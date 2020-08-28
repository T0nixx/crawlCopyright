import sqlite3
import subprocess
from pathlib import Path
import os
from urllib.parse import urlparse
import bs4
import re
from crawl import request_with_fake_headers
from typing import List, Dict, Optional
from shutil import rmtree


def initailize_leaves_database():
    with sqlite3.connect("illegals.db") as db_connection:
        cursor = db_connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS illegal_leaves(
                main_url TEXT PRIMARY KEY,
                main_html_path TEXT,
                captured_url TEXT,
                captured_file_path TEXT,
                google_analytics_code TEXT,
                telegram_url TEXT,
                twitter_url TEXT,
                similarity_group TEXT,
                engine TEXT,
                next_url TEXT
            )
        """
        )
        db_connection.commit()
        return db_connection


def is_telegram_url(url: str):
    if "telegram.me" not in url and "t.me/" not in url:
        return False
    return True


def is_twitter_url(url: str):
    if "twitter.com" not in url and "t.co/" not in url:
        return False
    return True


def is_main_url(url: str):
    if urlparse(url).path == "":
        return True
    return False


def trim_url(url: str) -> str:
    stripped = url.strip()
    if "https://" in stripped:
        return stripped[8:]
    if "http://" in stripped:
        return stripped[7:]
    return stripped


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
    url_with_scheme = "//" not in url and "http://" + url or url
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

    # [script_tag["src"] for script_tag in ]
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
    if wget_result.returncode != 0:
        print(wget_result)
    index_html_path = html_dir / "index.html"
    revise_html(index_html_path)

    # TODO: os.chdir 비직관적임 대체 가능하면 바꿔야함
    os.chdir(html_dir)
    rename_css_files(".")
    os.chdir("../..")

    def get_first_or_none(target: List[str]) -> Optional[str]:
        print(target)
        return len(target) != 0 and target[0] or None

    return {
        "main_url": trimmed_url,
        "main_html_path": str(html_dir.absolute()),
        "captured_url": None,
        "captured_file_path": None,
        "google_analytics_code": get_first_or_none(google_analytics_codes),
        "telegram_url": get_first_or_none(telegram_urls),
        "twitter_url": get_first_or_none(twitter_urls),
        "similarity_group": None,
        "engine": None,
        "next_url": None,
    }


def insert_row(row: Dict[str, str], connection: sqlite3.Connection):
    cursor = connection.cursor()
    # OR REPLACE
    sql = f"""
        INSERT OR REPLACE INTO illegal_leaves VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
    """
    cursor.execute(
        sql,
        (
            row["main_url"],
            row["main_html_path"],
            row["captured_url"],
            row["captured_file_path"],
            row["google_analytics_code"],
            row["telegram_url"],
            row["twitter_url"],
            row["similarity_group"],
            row["engine"],
            row["next_url"],
        ),
    )

    connection.commit()
    return connection


if __name__ == "__main__":
    connection = initailize_leaves_database()
    row = map_to_row("nabitoon2.link/웹툰")
    insert_row(row, connection).close()

