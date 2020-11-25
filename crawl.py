import bs4
import click
import logging
import requests
from utils.now import now
from request_with_fake_headers import request_with_fake_headers

# from crawl_none_category import crawl_none_category_dictionary
from utils.soup_library import (
    crawl_from_internals,
    get_a_soup_of_difference,
    get_external_url_set,
    get_internal_url_set,
    is_xe_based_soup,
)
from utils.db_library import insert_row, select_urls_by_category, select_all_urls
from typing import Set, List, Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from collections import Counter
from utils.url_library import (
    is_internal_url,
    assemble_url,
    validate_url,
    normalize_url,
    is_internal_specific_url,
)

logging.basicConfig(
    filename="crawl.log", level=logging.DEBUG, format="%(asctime)s %(message)s"
)


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


def is_redirected(url: str, response: requests.Response):
    # TODO: 좀 더 테스트 필요
    return url != response.url


def get_category_dictionary(main_url: str, main_soup: bs4.BeautifulSoup):
    # TODO: 필요한 지 생각해봐야함
    div_soup = bs4.BeautifulSoup(
        "\n".join([str(div_tag) for div_tag in main_soup.find_all("div", limit=5)]),
        "html5lib",
    )
    categories = [
        "webtoon",
        "sportslive",
        "adult",
        "torrent",
        "streaming",
        "link",
    ]

    a_tags = div_soup.find_all("a", {"href": True})
    url_text_tuples = [(a_tag["href"].strip(), a_tag.text) for a_tag in a_tags]

    category_dictionary = {
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
                        is_xe_based_soup(main_soup) == True
                        and len(urlparse(href).path.split("/")) > 2
                    )
                    and href != main_url
                    and "#" not in href
                ],
            )
        )
        for category in categories
    }

    return category_dictionary


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


def get_external_internal_urls(
    category_url: str, main_url: str, main_soup: bs4.BeautifulSoup
):
    category_response = request_with_fake_headers(category_url)
    category_soup = bs4.BeautifulSoup(category_response.content, "html5lib")

    a_soup_of_category_diff_main = get_a_soup_of_difference(category_soup, main_soup)

    next_page_url = get_next_page_url(a_soup_of_category_diff_main, category_url)
    page_count = 0
    category_soups: List[bs4.BeautifulSoup] = [category_soup]
    while next_page_url is not None and page_count < 5:
        current_page_url = next_page_url
        current_page_response = request_with_fake_headers(current_page_url)
        current_page_soup = bs4.BeautifulSoup(current_page_response.content, "html5lib")
        # main 과 비교해야 페이지가 있는 a tag 가 살아있음
        current_diff_a_soup = get_a_soup_of_difference(current_page_soup, main_soup)
        category_soups.append(current_page_soup)
        next_page_url = get_next_page_url(current_diff_a_soup, current_page_url)
        page_count += 1

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
        get_external_url_set(diff_soup, main_url) for diff_soup in diff_soups
    ]

    internal_urls: List[Set[str]] = [
        set(
            filter(
                # category_url로 필터하면 main_url에 붙여서 만든 internal_url 들이 걸러질 것
                lambda url: is_internal_specific_url(url, category_url),
                get_internal_url_set(diff_soup, main_url),
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


def crawl_link_collection_site(main_urls: List[str], visited: List[str], options):
    limit = options["limit"]
    if limit == 0:
        return 0
    force_crawl = options["force_crawl"]
    next_urls = []

    for main_url in main_urls:
        if validate_url(main_url) == False:
            click.echo(f"{main_url} is invalid. Please check.")
            logging.error(f"{main_url} is invalid.")
            continue

        main_url = normalize_url(main_url)
        if main_url in visited and force_crawl == False:
            click.echo(
                f"{main_url} has been already visited. Please check for illegals.db or set --force-crawl option to True."
            )
            logging.warning(
                f"{main_url} has been already visited. Please check for illegals.db or set --force-crawl option to True."
            )
            continue

        response = request_with_fake_headers(main_url)
        if is_redirected(main_url, response) == True:
            main_url = normalize_url(response.url)
        soup = bs4.BeautifulSoup(response.content, "html5lib")

        category_dictionary = get_category_dictionary(main_url, soup)
        click.echo("Collecting category dictionary is done.")
        # print(category_dictionary)
        specific_url_dict = dict()
        # is_none_category_url = True
        # for category_urls in category_dictionary.values():
        #     if len(category_urls) > 0:
        #         is_none_category_url = False

        # if is_none_category_url == True:
        #     specific_url_dict = crawl_none_category_dictionary(main_url)
        # else:
        for category, category_urls in category_dictionary.items():
            for category_url in category_urls:
                result = get_external_internal_urls(category_url, main_url, soup)
                click.echo(f"Collecting urls for {category} of {main_url} is done.")
                specific_url_dict[category] = list(
                    set(
                        result["external"]
                        if len(result["external"]) > 0
                        else crawl_from_internals(result["internal"], main_url)
                    )
                )

        urls_in_db = select_all_urls()
        # print(urls_in_db)

        def get_default_row(url, expected_category):
            return {
                "main_url": url,
                "expected_category": expected_category,
                "main_html_path": None,
                "captured_url": None,
                "captured_file_path": None,
                "google_analytics_code": None,
                "telegram_url": None,
                "twitter_url": None,
                "similarity_group": None,
                "engine": None,
                "next_url": None,
                "visited": False,
                "site_available": False,
                "ip_address": None,
                "created_at": now(),
                "last_visited_at": None,
            }

        for category, category_urls in specific_url_dict.items():
            for url_from_dict in category_urls:
                normalized_url_from_dict = normalize_url(url_from_dict)
                print(normalized_url_from_dict)
                if normalized_url_from_dict not in urls_in_db:
                    insert_row(get_default_row(normalized_url_from_dict, category))
                    if category == "link":
                        next_urls.append(url_from_dict)

        if main_url not in urls_in_db:
            insert_row(get_default_row(main_url, "link"))
        visited.append(main_url)
        click.echo(f"Crawling for {main_url} is done.")

    crawl_link_collection_site(
        next_urls, visited, {"limit": limit - 1, "force_crawl": force_crawl}
    )

    return 1


@click.command()
@click.argument("url")
@click.option("-l", "--limit", default=1, type=int, help="depth for recursive crawling")
@click.option(
    "-f",
    "--force-crawl",
    default=False,
    type=bool,
    help="bool for force crawl visited site",
)
def main(url, limit: int, force_crawl: bool):
    """Crawl site which collects illegal site urls"""
    logging.info("PROCESS STARTED")
    visited_link_urls = select_urls_by_category("link")
    crawl_link_collection_site(
        [url], visited_link_urls, {"limit": limit, "force_crawl": force_crawl}
    )


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
