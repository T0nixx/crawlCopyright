import requests
import bs4
import difflib
import re
from typing import Set, List, AnyStr, Union, Optional, Callable, TypeVar
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def request_with_fake_headers(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
        "referer": "https://www.google.com",
    }
    return requests.get(url, headers=headers)


def classify_tag(tag: bs4.Tag) -> str:
    category_keywords_dictionary = {
        "webtoon": ["웹툰", "webtoon", "애니", "만화", "툰", "코믹"],
        "sportslive": ["스포츠라이브", "중계", "sportslive"],
        "torrent": ["토렌트", "torrent", "토렌토", "토렌", "토랜"],
        "streaming": ["다시보기", "영화", "드라마", "TV", "티비"],
        "adult": ["성인", "야동", "19영상", "서양", "동양"],
        "link": ["링크", "주소", "link"],
    }

    for (category, keywords) in category_keywords_dictionary.items():
        if any(keyword in tag.text for keyword in keywords):
            return category
    return "else"


# TODO: 조정 필요함 사이트마다 다른 부분이라 어쩔 수 없나 싶기도 한데
def gnu_board_url_trim(url: str) -> str:
    return url.find("&wr_id") == -1 and url or url[: url.find("&wr_id")]


def get_category_dictionary_from_a_tags(a_tags: List[bs4.Tag], index_url: str):
    categories = [
        "webtoon",
        "sportslive",
        "adult",
        "torrent",
        "streaming",
        "link",
    ]
    return {
        category: set(
            [
                gnu_board_url_trim(a_tag["href"].strip())
                for a_tag in a_tags
                if (classify_tag(a_tag) == category)
                and (index_url in a_tag["href"].strip())
            ]
        )
        for category in categories
    }


def get_category_dictionary_from_index_page(index_url: str):
    response = request_with_fake_headers(index_url)
    soup = bs4.BeautifulSoup(response.content, "html5lib")
    div_soup = bs4.BeautifulSoup(
        "\n".join([str(div_tag) for div_tag in soup.find_all("div", limit=5)]),
        "html5lib",
    )
    return get_category_dictionary_from_a_tags(
        div_soup.find_all("a", {"href": True}), index_url
    )


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


def get_external_urls_from_category_url(
    a_soup: bs4.BeautifulSoup, main_url: str
) -> Set[str]:
    return set(
        [
            a_tag["href"].strip()
            for a_tag in a_soup.find_all("a", {"href": True})
            if main_url not in a_tag["href"].strip() and "http" in a_tag["href"].strip()
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
    diff = difflib.unified_diff(
        a_soup.prettify().splitlines(), b_soup.prettify().splitlines()
    )
    a_tags_of_diff = pattern.findall("\n".join(filter(lambda x: x[0] == "-", diff)))
    return bs4.BeautifulSoup("\n".join(a_tags_of_diff), "html5lib")


def get_result(category_url, main_url: str):
    category_a_soup = get_a_soup_from_url(category_url)
    main_a_soup = get_a_soup_from_url(main_url)
    a_soup_of_category_diff_main = get_a_soup_of_difference(
        category_a_soup, main_a_soup
    )

    next_page_url = get_next_page_url(a_soup_of_category_diff_main, category_url)
    next_page_url != None
    result = set()
    result.update(
        get_external_urls_from_category_url(a_soup_of_category_diff_main, main_url)
    )
    category_soups: List[bs4.BeautifulSoup] = [category_a_soup]
    while next_page_url != None:
        current_page_url = next_page_url
        current_page_a_soup = get_a_soup_from_url(current_page_url)
        # main 과 비교해야 페이지가 있는 a tag 가 살아있음
        current_diff_a_soup = get_a_soup_of_difference(current_page_a_soup, main_a_soup)
        result.update(
            get_external_urls_from_category_url(current_diff_a_soup, main_url)
        )
        category_soups.append(current_page_a_soup)
        next_page_url = get_next_page_url(current_diff_a_soup, current_page_url)
    # return result
    return (
        len(category_soups) > 1
        and result.difference(
            get_external_urls_from_category_url(
                category_soups[1], main_url
            ).intersection(
                get_external_urls_from_category_url(category_soups[0], main_url)
            )
        )
        or result
    )


main_urls = [
    "https://linkmoum.net/",
    "https://prolink1.com/",
    "https://jusomoya.com/",
    "https://podo10.com/",
    "https://linkbom.net/",
    "https://truemoa1.com/",
    "https://linkzip.site/",
    "https://www.linkmap.me/",
    "https://www.linkmoon2.me/#",
    "https://linkpan21.com/",
    "https://www.bobaelink.net/",
    "https://www.mango15.me/",
    "https://www.dailylink1.xyz/",
]
# print(get_category_dictionary_from_index_page("https://linkmoum.net/"))

# for url in main_urls:
# print(get_category_dictionary_from_index_page(url))

# get_a_soup_of_difference(
#     "https://jusomoya.com/bbs/board.php?bo_table=wt", "https://jusomoya.com/"
# )

# get_a_soup_of_difference("https://podo10.com/adult", "https://podo10.com/")
# print(
#     get_result(
#         "https://linkbom.net/bbs/board.php?bo_table=webtoon", "https://linkbom.net/"
#     )
# )

# print(
#     # get_result(
#     #     "https://jusomoya.com/bbs/board.php?bo_table=wt&page=1", "https://jusomoya.com/"
#     # )
#     get_result(
#         "https://linkbom.net/bbs/board.php?bo_table=webtoon", "https://linkbom.net/"
#     )
# )

main_url = "https://linkbom.net/"
print(
    get_external_urls_from_category_url(
        get_a_soup_from_url("https://linkbom.net/bbs/board.php?bo_table=webtoon"),
        main_url,
    ).intersection(
        get_external_urls_from_category_url(
            get_a_soup_from_url(
                "https://linkbom.net/bbs/board.php?bo_table=webtoon&page=2"
            ),
            main_url,
        )
    )
)

# cate = get_a_soup_from_url("https://linkbom.net/bbs/board.php?bo_table=webtoon")
# main = get_a_soup_from_url("https://linkbom.net/")
# diff = get_a_soup_of_difference(cate, main)
# print([tag for tag in diff.find_all("a", {"href": True}) if "page=" in tag["href"]])

