import bs4
import difflib
import re
import requests
from typing import Set, List
from utils.url_library import (
    assemble_url,
    is_internal_url,
    remove_page_query,
)
from request_with_fake_headers import request_with_fake_headers


def is_xe_based_soup(soup: bs4.BeautifulSoup):
    return bool(soup.find(text=re.compile("var current_mid ")))


def is_gnu_based_soup(soup: bs4.BeautifulSoup):
    return bool(soup.find(text=re.compile("var g5_url")))


def determine_engine(soup: bs4.BeautifulSoup):
    if is_gnu_based_soup(soup) == True:
        return "gnu"
    if is_xe_based_soup(soup) == True:
        return "XE"
    return None


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


def crawl_from_internals(urls: List[str], main_url: str) -> List[str]:
    urls_without_page = [remove_page_query(url) for url in urls]
    soups = []

    for url in urls_without_page:
        try:
            soup = bs4.BeautifulSoup(
                requests.get(url, headers={"referer": main_url}).content, "html5lib"
            )
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