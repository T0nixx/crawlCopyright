from db_library import update_row
from determine_engine import determine_engine
import subprocess
from pathlib import Path
import os
import bs4
import re
from typing import List, Optional
from shutil import rmtree
from url_library import (
    trim_url,
    is_telegram_url,
    is_twitter_url,
    is_main_url,
)
from request_with_fake_headers import request_with_fake_headers
import click


def revise_html(path: Path):
    with open(path.absolute(), "r", encoding="utf-8") as main_page:
        css_pattern = re.compile(r'.css@.*"')
        revised_lines = [
            css_pattern.sub(r'.css"', line) for line in main_page.readlines()
        ]
    with open(path.absolute(), "w+", encoding="utf-8") as revised_page:
        revised_page.writelines(revised_lines)


def rename_css_files(directory):
    css_file_pattern = re.compile(r".css@.*")
    for file_name in os.listdir(directory):
        if file_name.find(".css") and os.path.isfile(file_name):
            new_file_name = css_file_pattern.sub(r".css", file_name)
            os.rename(file_name, new_file_name)
        if os.path.isdir(file_name):
            os.chdir(file_name)
            rename_css_files(".")
            os.chdir("..")


def map_to_row(url: str):
    url_with_scheme = "https://" + url if "//" not in url else url
    response = request_with_fake_headers(url_with_scheme)
    soup = bs4.BeautifulSoup(response.content, "html5lib")

    urls_in_soup = [
        a_tag["href"].strip() for a_tag in soup.find_all("a", {"href": True})
    ]

    telegram_urls = [
        url
        for url in urls_in_soup
        if is_telegram_url(url) == True and is_main_url(url) == False
    ]

    twitter_urls = [
        url
        for url in urls_in_soup
        if is_twitter_url(url) == True and is_main_url(url) == False
    ]

    google_analytics_pattern = re.compile(r"UA-[0-9]{9}-[0-9]+")

    google_analytics_codes = google_analytics_pattern.findall(
        " ".join(
            [str(script_tag) for script_tag in soup.find_all("script", {"src": True})]
        )
    )

    trimmed_url = trim_url(url)
    html_dir = Path(f"html/{trimmed_url}")

    if os.path.exists(html_dir) == True:
        # 이미 있는 경우 해당 폴더 삭제
        rmtree(html_dir)

    wget_result = subprocess.run(
        [
            "./wget.exe",
            "-pqk",
            "-U",
            "Mozilla",
            "-P",
            "./html/",
            "-e",
            "robots=off",
            trimmed_url,
        ]
    )
    # wget 실패하는 경우에 대한 처리 필요
    # if wget_result.returncode != 0:
    #     print(wget_result)
    index_html_path = html_dir / "index.html"
    revise_html(index_html_path)

    # TODO: os.chdir 비직관적임 대체 가능하면 바꿔야함
    os.chdir(html_dir)
    rename_css_files(".")
    os.chdir("../..")

    def get_first_or_none(target: List[str]) -> Optional[str]:
        return None if len(target) == 0 else target[0]

    return {
        "main_url": trimmed_url,
        "main_html_path": str(html_dir.absolute()),
        "captured_url": None,
        "captured_file_path": None,
        "google_analytics_code": get_first_or_none(google_analytics_codes),
        "telegram_url": get_first_or_none(telegram_urls),
        "twitter_url": get_first_or_none(twitter_urls),
        "similarity_group": None,
        "engine": determine_engine(soup),
        "next_url": None,
        "expected_category": None,
    }


@click.command()
@click.argument("url")
def update_url(url: str):
    """Update detail information of input url"""
    row = map_to_row(url)
    update_row(row)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    update_url()
