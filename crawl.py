from determine_engine import is_xe_based_soup
from db_library import insert_row
import requests
import bs4
import difflib
import re
from typing import Set, List, Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from collections import Counter
from url_library import (
    is_internal_url,
    assemble_url,
    validate_url,
    trim_url,
    normalize_url,
    is_internal_specific_url,
    remove_page_query,
)
import click
from request_with_fake_headers import request_with_fake_headers


def classify_tag(text: str) -> str:
    category_keywords_dictionary = {
        "webtoon": ["웹툰", "webtoon", "애니", "만화", "툰", "코믹"],
        "sportslive": ["스포츠라이브", "중계", "sportslive"],
        "torrent": ["토렌트", "torrent", "토렌토", "토렌", "토랜"],
        "streaming": ["다시보기", "영화", "드라마", "TV", "티비"],
        "adult": ["성인", "야동", "19영상", "서양", "동양"],
        "link": ["링크모음", "주소모음"],
    }

    for (category, keywords) in category_keywords_dictionary.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "else"


def get_category_dictionary(main_url: str):
    response = request_with_fake_headers(main_url)
    soup = bs4.BeautifulSoup(response.content, "html5lib")
    # TODO: 필요한 지 생각해봐야함
    div_soup = bs4.BeautifulSoup(
        "\n".join([str(div_tag) for div_tag in soup.find_all("div", limit=5)]),
        "html5lib",
    )
    categories = [
        "webtoon",
        "sportslive",
        "adult",
        "torrent",
        "streaming",
        # "link",
    ]

    a_tags = div_soup.find_all("a", {"href": True})
    url_text_tuples = [(a_tag["href"].strip(), a_tag.text) for a_tag in a_tags]

    return {
        # TODO: 누더기...
        category: set(
            filter(
                validate_url,
                [
                    href
                    if "http" in href
                    else normalize_url(main_url) + assemble_url(href)
                    for (href, text) in url_text_tuples
                    if (classify_tag(text) == category)
                    and is_internal_url(href, main_url)
                    # 그누보드를 쓰는 사이트에서 카테고리 url 을 뽑기 위해 걸러냄
                    and href.find("&wr_id") == -1
                    and href.find("document_srl") == -1
                    and not (
                        # XE 쓰는 사이트에서 index 숨겼을 때 게시판 까지만 참조하도록함
                        is_xe_based_soup(soup)
                        and len(urlparse(href).path.split("/")) > 2
                    )
                    and href != main_url
                    and "#" not in href
                ],
            )
        )
        for category in categories
    }


def get_next_page_url(a_soup: bs4.BeautifulSoup, current_url: str) -> Optional[str]:
    parse_result = urlparse(current_url)
    parsed_query = parse_result.query
    parsed_query_string_dictionary = dict(parse_qsl(parsed_query))

    # page가 쿼리에 있으면 그걸 사용하고 없으면 1로 가정
    current_page = (
        int(parsed_query_string_dictionary["page"]) if "page" in parsed_query else 1
    )
    next_page_in_string = str(current_page + 1)
    next_parsed_query_string_dictionary = {
        **parsed_query_string_dictionary,
        "page": next_page_in_string,
    }

    next_page_parsed = [
        # attribute 중 query만 page를 다음 페이지로 바꿔줌 https://docs.python.org/ko/3/library/urllib.parse.html 표 참조
        urlencode(next_parsed_query_string_dictionary) if index == 4 else attirbute
        for index, attirbute in enumerate(parse_result)
    ]
    next_page_url = urlunparse(next_page_parsed)

    # 다음 페이지 호출하는 url이 html에 존재할 때만 반환
    return (
        next_page_url
        if any(
            [
                a_tag["href"].strip()
                for a_tag in a_soup.find_all("a", {"href": True})
                if "page=" + next_page_in_string in a_tag["href"].strip()
            ]
        )
        else None
    )


def get_external_url_set(soup: bs4.BeautifulSoup, main_url: str) -> Set[str]:
    stripped = [a_tag["href"].strip() for a_tag in soup.find_all("a", {"href": True})]
    return set(
        [
            external_url
            for external_url in stripped
            if is_internal_url(external_url, main_url) == False
        ]
    )


def get_internal_url_set(soup: bs4.BeautifulSoup, main_url: str) -> Set[str]:
    stripped = [
        a_tag["href"].strip()
        for a_tag in soup.find_all("a", {"href": True})
        if len(a_tag["href"]) > 0
    ]

    return set(
        [
            "http" in internal_url
            and internal_url
            or main_url + assemble_url(internal_url)
            for internal_url in stripped
            if is_internal_url(internal_url, main_url) == True
        ]
    )


def get_a_soup_of_difference(
    a_soup: bs4.BeautifulSoup, b_soup: bs4.BeautifulSoup
) -> bs4.BeautifulSoup:
    # diff 성능이 좋지 않은 사이트들이 있음
    diff = difflib.unified_diff(
        a_soup.prettify().splitlines(), b_soup.prettify().splitlines()
    )
    # TODO: 정규 표현식 더 상세하게 수정 필요
    pattern = re.compile("<a.*>")

    a_tags_of_diff = pattern.findall("\n".join(filter(lambda x: x[0] == "-", diff)))
    return bs4.BeautifulSoup("\n".join(a_tags_of_diff), "html5lib")


def get_external_internal_urls(category_url: str, main_url: str):
    category_response = request_with_fake_headers(category_url)
    category_soup = bs4.BeautifulSoup(category_response.content, "html5lib")

    normalized_main_url = normalize_url(main_url)
    main_response = request_with_fake_headers(normalized_main_url)
    main_soup = bs4.BeautifulSoup(main_response.content, "html5lib")

    a_soup_of_category_diff_main = get_a_soup_of_difference(category_soup, main_soup)

    next_page_url = get_next_page_url(a_soup_of_category_diff_main, category_url)
    limit = 0
    category_soups: List[bs4.BeautifulSoup] = [category_soup]
    while next_page_url is not None and limit < 5:
        current_page_url = next_page_url
        current_page_response = request_with_fake_headers(current_page_url)
        current_page_soup = bs4.BeautifulSoup(current_page_response.content, "html5lib")
        # main 과 비교해야 페이지가 있는 a tag 가 살아있음
        current_diff_a_soup = get_a_soup_of_difference(current_page_soup, main_soup)
        category_soups.append(current_page_soup)
        next_page_url = get_next_page_url(current_diff_a_soup, current_page_url)
        limit += 1

    diff_soups = (
        len(category_soups) > 1
        and [
            # 다음 페이지가 있으면 여기서 자기들 끼리 비교해서 page 관련 태그를 없애고자 함
            get_a_soup_of_difference(category_soups[index], category_soups[index - 1])
            for index, _ in enumerate(category_soups)
        ]
        or [a_soup_of_category_diff_main]
    )

    # 한 페이지 별로 Set을 만들어서 광고등으로 여러번 나온 url을 하나만 나오도록 함
    external_urls: List[Set[str]] = [
        get_external_url_set(diff_soup, normalized_main_url) for diff_soup in diff_soups
    ]

    internal_urls: List[Set[str]] = [
        set(
            filter(
                # category_url로 필터하면 main_url에 붙여서 만든 internal_url 들이 걸러질 것
                lambda url: is_internal_specific_url(url, category_url),
                get_internal_url_set(diff_soup, normalized_main_url),
            )
        )
        for diff_soup in diff_soups
    ]

    def integrate_urls(url_sets: List[Set[str]]) -> List[str]:
        # 2차원 배열 1차원으로 flatten 하고 원소별 개수 Counter로 체크
        counter = Counter([url for url_set in url_sets for url in url_set])
        # 여러 페이지에서 중복으로 나오는 url은 광고일 확률이 높으므로 필터
        urls = [url for url, count in counter.items() if count == 1]

        return urls

    return {
        "external": integrate_urls(external_urls),
        "internal": integrate_urls(internal_urls),
    }


def crawl_from_internals(urls: List[str], main_url: str) -> List[str]:
    urls_without_page = [remove_page_query(url) for url in urls]
    # print(urls_without_page)
    soups = []

    for url in urls_without_page:
        try:
            soup = bs4.BeautifulSoup(request_with_fake_headers(url).content, "html5lib")
        except:
            pass
        else:
            soups.append(soup)
    diff_soups = [
        # 다음 페이지가 있으면 여기서 자기들 끼리 비교해서 page 관련 태그를 없애고자 함
        get_a_soup_of_difference(soups[index], soups[index - 1])
        for index, _ in enumerate(soups)
    ]

    internals = [
        diff_soup.find("a", {"href": re.compile(r"&no=")}) for diff_soup in diff_soups
    ]

    filtered_internals = [
        internal["href"] for internal in internals if internal is not None
    ]

    final_internals = []
    for filtered_url in filtered_internals:
        try:
            result = requests.get(filtered_url, headers={"referer": filtered_url}).url
        except:
            pass
        else:
            final_internals.append(result)

    if len(final_internals) > 0:
        return final_internals

    externals = [
        [
            a_tag["href"]
            for a_tag in diff_soup.find_all("a", {"href": True})
            if is_internal_url(a_tag["href"], main_url) == False
        ]
        for diff_soup in diff_soups
    ]

    final_externals = [external[0] for external in externals if len(external) > 0]
    return final_externals


@click.command()
@click.argument("url")
def crawl_link_collection_site(url):
    """Crawl site which collects illegal site urls"""
    if validate_url(url) == False:
        print("INVALID URL")
        return 0
    category_dictionary = get_category_dictionary(url)
    # print(category_dictionary)
    url_dict = dict()
    for category, category_urls in category_dictionary.items():
        for category_url in category_urls:
            result = get_external_internal_urls(category_url, url)
            url_dict[category] = list(
                set(
                    result["external"]
                    if len(result["external"]) > 0
                    else crawl_from_internals(result["internal"], url)
                )
            )

    for category, urls in url_dict.items():
        for url_from_dict in urls:
            insert_row(
                {
                    "main_url": trim_url(url_from_dict),
                    "expected_category": category,
                    "main_html_path": None,
                    "captured_url": None,
                    "captured_file_path": None,
                    "google_analytics_code": None,
                    "telegram_url": None,
                    "twitter_url": None,
                    "similarity_group": None,
                    "engine": None,
                    "next_url": None,
                }
            )

    insert_row(
        {
            "main_url": trim_url(url),
            "expected_category": "link",
            "main_html_path": None,
            "captured_url": None,
            "captured_file_path": None,
            "google_analytics_code": None,
            "telegram_url": None,
            "twitter_url": None,
            "similarity_group": None,
            "engine": None,
            "next_url": None,
        }
    )

    return url_dict


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    crawl_link_collection_site()
