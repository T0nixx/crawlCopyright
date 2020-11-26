import sqlite3
from typing import Dict, Optional


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
                visited BOOLEAN,
                site_available BOOLEAN,
                ip_address TEXT,
                created_at TEXT,
                last_visited_at TEXT
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
                row["visited"],
                row["site_available"],
                row["ip_address"],
                row["created_at"],
                row["last_visited_at"],
            ),
        )
        connection.commit()
    return connection


def update_row(row: Dict[str, Optional[str]]):
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
            WHERE visited = ?
        """

        result = cursor.execute(sql, (False,))

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


def select_available_urls():
    connection = initialize_database()
    with connection:
        cursor = connection.cursor()

        sql = f"""
            SELECT main_url
            FROM illegal_sites
            WHERE site_available = ?
        """

        result = cursor.execute(sql, (True,))

        connection.commit()
        return [url for (url,) in result.fetchall()]


def get_site_data():
    connection = initialize_database()
    with connection:
        cursor = connection.cursor()

        sql = f"""
            SELECT main_url, site_available, created_at, last_visited_at
            FROM illegal_sites
            ORDER BY last_visited_at DESC
        """
        # WHERE main_html_path IS NOT NULL
        result = cursor.execute(sql)

        connection.commit()
        return list(result.fetchall())
