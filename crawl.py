import requests
import bs4
import difflib
import re
from typing import Set, List


def request_with_fake_headers(url):
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


def get_target_urls_from_category_url(category_url: str, main_url: str) -> Set[str]:
    main_response = request_with_fake_headers(main_url)
    main_soup = bs4.BeautifulSoup(main_response.content, "html5lib")

    category_response = request_with_fake_headers(category_url)
    category_soup = bs4.BeautifulSoup(category_response.content, "html5lib")

    # TODO: 정규 표현식 더 상세하게 수정 필요
    pattern = re.compile("<a.*>")
    diff = difflib.unified_diff(
        category_soup.prettify().splitlines(), main_soup.prettify().splitlines()
    )
    a_tags_of_diff = pattern.findall("\n".join(filter(lambda x: x[0] == "-", diff)))
    a_soup = bs4.BeautifulSoup("\n".join(a_tags_of_diff), "html5lib")

    return set(
        [
            a_tag["href"].strip()
            for a_tag in a_soup.find_all("a", {"href": True})
            if main_url not in a_tag["href"].strip()
        ]
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
print(
    get_target_urls_from_category_url(
        "https://linkzip.site/board_SnzU08", "https://linkzip.site/"
    )
)
