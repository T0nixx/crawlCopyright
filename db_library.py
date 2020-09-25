import sqlite3
from typing import List, Dict, Optional
from url_library import trim_url


def initialize_database():
    with sqlite3.connect("illegals.db") as db_connection:
        cursor = db_connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS illegal_sites(
                main_url TEXT PRIMARY KEY,
                main_html_path TEXT,
                captured_url TEXT,
                captured_file_path TEXT,
                google_analytics_code TEXT,
                telegram_url TEXT,
                twitter_url TEXT,
                similarity_group TEXT,
                engine TEXT,
                next_url TEXT,
                expected_category TEXT,
                have_site_information BOOLEAN
            )
        """
        )
        db_connection.commit()
        return db_connection


def insert_row(row: Dict[str, Optional[str]]):
    connection = initialize_database()
    with connection:
        cursor = connection.cursor()
        sql = f"""
            INSERT OR REPLACE INTO illegal_sites VALUES (
                ?,
                ?,
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
                row["expected_category"],
                row["have_site_information"],
            ),
        )
        connection.commit()
    return connection


def update_row(row: Dict[str, Optional[str]]):
    if row is None:
        return

    connection = initialize_database()
    with connection:
        cursor = connection.cursor()
        # None으로 업데이트하지 않을 것이라고 가정
        will_be_updated = [
            (key, value)
            for key, value in row.items()
            if value is not None and key != "main_url"
        ]

        for key, value in will_be_updated:
            # {trim_url(row['main_url'])}
            sql = f"""
                UPDATE illegal_sites 
                SET {key} = ? 
                WHERE main_url = ?
                """

            cursor.execute(sql, (value, row["main_url"]))
        connection.commit()
    return connection


def select_urls_by_category(category):
    connection = initialize_database()
    with connection:
        cursor = connection.cursor()

        sql = f"""
            SELECT main_url
            FROM illegal_sites
            WHERE expected_category = ?
        """

        result = cursor.execute(sql, (category,))

        connection.commit()
        return [url for (url,) in result.fetchall()]


def select_unstored_urls():
    connection = initialize_database()
    with connection:
        cursor = connection.cursor()

        sql = f"""
            SELECT main_url
            FROM illegal_sites
            WHERE have_site_information = ?
        """

        result = cursor.execute(sql, (0,))

        connection.commit()
        return [url for (url,) in result.fetchall()]


def select_all_urls():
    connection = initialize_database()
    with connection:
        cursor = connection.cursor()

        sql = f"""
            SELECT main_url
            FROM illegal_sites
        """

        result = cursor.execute(sql)

        connection.commit()
        return [url for (url,) in result.fetchall()]
