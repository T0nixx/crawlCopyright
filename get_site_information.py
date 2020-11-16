import requests
from utils.db_library import (
    select_all_urls,
    select_unstored_urls,
    select_available_urls,
    update_row,
)
from utils.soup_library import determine_engine
import subprocess
from pathlib import Path
import os
import bs4
import re
from typing import List, Optional
from shutil import rmtree
from utils.url_library import (
    is_telegram_url,
    is_twitter_url,
    is_main_url, trim_url,
)
from request_with_fake_headers import request_with_fake_headers
import click
import logging
from utils.now import now


logging.basicConfig(
    filename="get_site_information.log",
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
)


def revise_html(path: Path):
    # encoding이 다른 데 어떤 식으로 해야하는지 잘 모르겠음

    encodings = ["utf-8", "euc-kr", "utf-8-sig", "utf-16"]
    for encoding in encodings:
        try:
            with open(path.absolute(), "r", encoding=encoding) as main_page:
                css_pattern = re.compile(r'.css@.*"')
                revised_lines = [
                    css_pattern.sub(r'.css"', line) for line in main_page.readlines()
                ]
            with open(path.absolute(), "w+", encoding=encoding) as revised_page:
                revised_page.writelines(revised_lines)
        except:
            logging.error(str(path) + "REVISE HTML ERROR")
            continue
        else:
            break


def rename_css_files(directory):
    css_file_pattern = re.compile(r".css@.*")
    for file_name in os.listdir(directory):
        if css_file_pattern.search(file_name) is not None and os.path.isfile(file_name):
            new_file_name = css_file_pattern.sub(r".css", file_name)
            if os.path.exists(new_file_name):
                os.remove(new_file_name)
            os.rename(file_name, new_file_name)
        if os.path.isdir(file_name):
            os.chdir(file_name)
            rename_css_files(".")
            os.chdir("..")


def map_to_row(url: str):
    try:
        response = requests.get(url, stream=True)
    except:
        click.echo(f"Error has occurred on proccessing {url}")
        logging.error(f"ERROR ON {url}")
        return {
            "main_url": url,
            "site_available": False,
            "visited": True,
            "last_visited_at": now(),
        }

    # in that sock is gone after call response.content ip address is assigned
    ip_address = (
        response.raw.connection.sock.getpeername()[0]
        if getattr(response.raw.connection, "sock") is not None
        else None
    )
    
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
            [
                str(script_tag)
                for script_tag in soup.find_all("script", {"src": True})
            ]
        )
    )
    if os.path.exists("./html") == False:
        os.mkdir("html")
    # trimmed_url = trim_url(url)
    html_dir = Path(f"html/{trim_url(url)}")

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
            "--no-check-certificate",
            url,
        ]
    )
    # wget 실패하는 경우에 대한 처리 필요
    # if wget_result.returncode != 0:
    #     print(wget_result)
    index_html_path = html_dir / "index.html"
    revise_html(index_html_path)

    # TODO: os.chdir 비직관적임 대체 가능하면 바꿔야함 있으면 삭제하고 없으면 만드는데..?
    if os.path.exists(html_dir) == False:
        os.mkdir(html_dir)
    os.chdir(html_dir)
    rename_css_files(".")
    os.chdir("../..")

    def get_first_or_none(target: List[str]) -> Optional[str]:
        return None if len(target) == 0 else target[0]

    return {
        "main_url": url,
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
        "visited": True,
        "site_available": True,
        "ip_address": ip_address,
        "last_visited_at": now(),
    }


@click.group()
def cli1():
    pass


@cli1.command()
@click.argument("url")
def specific_url(url: str):
    """Get site information for specific url."""
    row = map_to_row(url)
    update_row(row)


@click.group()
def cli2():
    pass


@cli2.command()
def unstored():
    """Get site information for unstored rows of database."""
    urls = select_unstored_urls()
    for url in urls:
        row = map_to_row(url)
        if row is not None:
            update_row(row)


@click.group()
def cli3():
    pass


@cli3.command()
def all():
    """Get site information for all rows of database. This operation can take significantly long time."""
    urls = select_all_urls()
    for url in urls:
        row = map_to_row(url)
        update_row(row)


@click.group()
def cli4():
    pass


@cli4.command()
def available():
    """Get site information from available sites. This operation can take significantly long time."""
    urls = select_available_urls()
    for url in urls:
        row = map_to_row(url)
        update_row(row)


cli = click.CommandCollection(sources=[cli1, cli2, cli3, cli4])

if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    cli()
