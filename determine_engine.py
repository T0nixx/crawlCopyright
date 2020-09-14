import re
from url_library import is_xe_based_url
from bs4 import BeautifulSoup


def is_xe_based_soup(soup: BeautifulSoup):
    return bool(soup.find(text=re.compile("var current_mid ")))


def is_gnu_based_soup(soup: BeautifulSoup):
    return bool(soup.find(text=re.compile("var g5_url")))


def determine_engine(soup: BeautifulSoup):
    if is_gnu_based_soup(soup) == True:
        return "gnu"
    if is_xe_based_url(soup) == True:
        return "XE"
    return None