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
        "webtoon": ["웹툰", "webtoon", "애니", "만화"],
        "sportslive": ["스포츠라이브", "중계", "sportslive"],
        "adult": ["성인", "야동", "19영상", "서양", "동양"],
        "torrent": ["토렌트", "torrent", "토렌토"],
        "streaming": ["다시보기", "영화", "드라마", "TV"],
        "link": ["링크", "주소", "link"],
    }

    for (category, keywords) in category_keywords_dictionary.items():
        if any(keyword in tag.text for keyword in keywords):
            return category
    return "else"


def get_category_dictionary_from_a_tags(a_tags: List[bs4.Tag]):
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
                a_tag["href"].strip()
                for a_tag in a_tags
                if classify_tag(a_tag) == category
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
    return get_category_dictionary_from_a_tags(div_soup.find_all("a", {"href": True}))


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


print(get_category_dictionary_from_index_page("https://linkmoum.net/"))
print(
    get_target_urls_from_category_url(
        "https://linkmoum.net/index.php?mid=webtoon", "https://linkmoum.net/"
    )
)
