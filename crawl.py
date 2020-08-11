import requests
import bs4
import difflib
import re
from typing import Set, List, AnyStr, Union, Optional, Callable, TypeVar
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from collections import Counter


def request_with_fake_headers(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
        "referer": "https://www.google.com",
    }
    return requests.get(url, headers=headers)


def classify_tag(text: str) -> str:
    category_keywords_dictionary = {
        "webtoon": ["웹툰", "webtoon", "애니", "만화", "툰", "코믹"],
        "sportslive": ["스포츠라이브", "중계", "sportslive"],
        "torrent": ["토렌트", "torrent", "토렌토", "토렌", "토랜"],
        "streaming": ["다시보기", "영화", "드라마", "TV", "티비"],
        "adult": ["성인", "야동", "19영상", "서양", "동양"],
        "link": ["링크", "주소", "link"],
    }

    for (category, keywords) in category_keywords_dictionary.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "else"


def determine_internal_url(url: str, main_url) -> bool:
    return main_url in url or "http" not in url


def assemble_url(href_without_http: str) -> str:
    regex = re.compile(".*/")

    if re.match(regex, href_without_http):
        slash_index = href_without_http.find("/")
        return href_without_http[slash_index:]
    if href_without_http[0] == "#":
        return "/" + href_without_http
    return href_without_http


def validate_url(url: str) -> bool:
    regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(regex, url) is not None


def get_category_dictionary_from_soup_and_main_url(
    soup: bs4.BeautifulSoup, main_url: str
):
    categories = [
        "webtoon",
        "sportslive",
        "adult",
        "torrent",
        "streaming",
        "link",
    ]

    a_tags = soup.find_all("a", {"href": True})
    url_text_tuples = [(a_tag["href"].strip(), a_tag.text) for a_tag in a_tags]

    return {
        # TODO: 누더기...
        category: set(
            filter(
                validate_url,
                [
                    "http" in href and href or main_url + assemble_url(href)
                    for (href, text) in url_text_tuples
                    if (classify_tag(text) == category)
                    and determine_internal_url(href, main_url)
                    and href.find("&wr_id") == -1
                ],
            )
        )
        for category in categories
    }


def get_category_dictionary_from_main_page(main_url: str):
    response = request_with_fake_headers(main_url)
    soup = bs4.BeautifulSoup(response.content, "html5lib")
    div_soup = bs4.BeautifulSoup(
        "\n".join([str(div_tag) for div_tag in soup.find_all("div", limit=5)]),
        "html5lib",
    )
    return get_category_dictionary_from_soup_and_main_url(div_soup, main_url)


def get_next_page_url(a_soup: bs4.BeautifulSoup, current_url: str) -> Optional[str]:
    parse_result = urlparse(current_url)
    parsed_query = parse_result.query
    parsed_query_string_dictionary = dict(parse_qsl(parsed_query))

    # page가 쿼리에 있으면 그걸 사용하고 없으면 1로 가정
    current_page = (
        "page" in parsed_query and int(parsed_query_string_dictionary["page"]) or 1
    )
    next_page_in_string = str(current_page + 1)
    next_parsed_query_string_dictionary = {
        **parsed_query_string_dictionary,
        "page": next_page_in_string,
    }

    next_page_parsed = [
        # attribute 중 query만 page를 다음 페이지로 바꿔줌 https://docs.python.org/ko/3/library/urllib.parse.html 표 참조
        index == 4 and urlencode(next_parsed_query_string_dictionary) or attirbute
        for index, attirbute in enumerate(parse_result)
    ]
    next_page_url = urlunparse(next_page_parsed)

    # 다음 페이지 호출하는 url이 html에 존재할 때만 반환
    return (
        any(
            [
                a_tag["href"].strip()
                for a_tag in a_soup.find_all("a", {"href": True})
                if "page=" + next_page_in_string in a_tag["href"].strip()
            ]
        )
        and next_page_url
        or None
    )


def get_external_urls_from_soup_and_main_url(
    soup: bs4.BeautifulSoup, main_url: str
) -> Set[str]:
    stripped = [a_tag["href"].strip() for a_tag in soup.find_all("a", {"href": True})]
    return set(
        [
            external_url
            for external_url in stripped
            if determine_internal_url(external_url, main_url) == False
        ]
    )


def get_internal_urls_from_soup_and_main_url(
    soup: bs4.BeautifulSoup, main_url: str
) -> Set[str]:
    stripped = [a_tag["href"].strip() for a_tag in soup.find_all("a", {"href": True})]

    return set(
        [
            "http" in internal_url
            and internal_url
            or main_url + assemble_url(internal_url)
            for internal_url in stripped
            if determine_internal_url(internal_url, main_url) == True
        ]
    )


def get_a_soup_from_url(url: str):
    response = request_with_fake_headers(url)
    return bs4.BeautifulSoup(response.content, "html5lib")


# 더 나은 이름이 있을 것 같은데 생각이 안남 ㅎㅎ;
def get_a_soup_of_difference(
    a_soup: bs4.BeautifulSoup, b_soup: bs4.BeautifulSoup
) -> bs4.BeautifulSoup:
    # TODO: 정규 표현식 더 상세하게 수정 필요
    pattern = re.compile("<a.*>")
    # diff 성능이 좋지 않은 사이트들이 있음
    diff = difflib.unified_diff(
        a_soup.prettify().splitlines(), b_soup.prettify().splitlines()
    )

    a_tags_of_diff = pattern.findall("\n".join(filter(lambda x: x[0] == "-", diff)))
    return bs4.BeautifulSoup("\n".join(a_tags_of_diff), "html5lib")


def get_result(category_url: str, main_url: str):
    category_a_soup = get_a_soup_from_url(category_url)
    main_a_soup = get_a_soup_from_url(main_url)
    a_soup_of_category_diff_main = get_a_soup_of_difference(
        category_a_soup, main_a_soup
    )

    next_page_url = get_next_page_url(a_soup_of_category_diff_main, category_url)

    category_soups: List[bs4.BeautifulSoup] = [category_a_soup]
    while next_page_url != None:
        current_page_url = next_page_url
        current_page_a_soup = get_a_soup_from_url(current_page_url)
        # main 과 비교해야 페이지가 있는 a tag 가 살아있음
        current_diff_a_soup = get_a_soup_of_difference(current_page_a_soup, main_a_soup)
        category_soups.append(current_page_a_soup)
        next_page_url = get_next_page_url(current_diff_a_soup, current_page_url)

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
        get_external_urls_from_soup_and_main_url(diff_soup, main_url)
        for diff_soup in diff_soups
    ]

    internal_urls: List[Set[str]] = [
        set(
            filter(
                # category_url로 필터하면 main_url에 붙여서 만든 internal_url 들이 걸러질 것
                lambda url: category_url in url and validate_url(url),
                get_internal_urls_from_soup_and_main_url(diff_soup, main_url),
            )
        )
        for diff_soup in diff_soups
    ]

    def integrate_urls(url_sets: List[Set[str]]) -> List[str]:
        counter = Counter([url for url_set in url_sets for url in url_set])
        # 여러 페이지에서 중복으로 나오는 url은 광고일 확률이 높으므로 필터
        urls = [url for url, count in counter.items() if count == 1]

        return urls

    return {
        "external": integrate_urls(external_urls),
        "internal": integrate_urls(internal_urls),
    }

