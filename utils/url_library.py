import re
from urllib.parse import urlparse


def is_internal_url(url: str, main_url) -> bool:
    return main_url in url or "http" not in url


def is_xe_based_url(url: str) -> bool:
    return "?mid" in url


def is_gnu_based_url(url: str) -> bool:
    return "bo_table" in url


def assemble_url(href_without_http: str) -> str:
    regex = re.compile(".*/")
    # print(href_without_http)
    if re.match(regex, href_without_http) is not None:
        slash_index = href_without_http.find("/")
        return href_without_http[slash_index:]
    if href_without_http[0] == "#":
        return "/" + href_without_http
    return href_without_http


def normalize_url(url: str) -> str:
    return url[:-1] if url[-1] == "/" else url


def validate_url(url: str) -> bool:
    regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    # javascript 여기서 걸러도 되는가.. onclick과 함게 나올 확률이 높은듯? 어떻게 처리할 지
    return (re.match(regex, url) != None) and ("javascript" not in url)


def is_telegram_url(url: str):
    if "telegram.me" not in url and "//t.me/" not in url:
        return False
    return True


def is_twitter_url(url: str):
    if "twitter.com" not in url and "//t.co/" not in url:
        return False
    return True


def is_main_url(url: str):
    if urlparse(normalize_url(url)).path == "":
        return True
    return False


def trim_url(url: str) -> str:
    stripped = url.strip()
    # url_with_https = re.search(r"https://.*", stripped)
    # url_with_http = re.search(r"http://.*", stripped)
    # if url_with_https != None:
    #     return urlparse(url).netloc
    # if url_with_http != None:
    #     return urlparse(url).netloc
    # return stripped
    return urlparse(stripped).netloc


def is_internal_specific_url(url: str, category_url: str) -> bool:
    return (
        category_url in url
        and validate_url(url)
        # 그누보드 쓰는 페이지들에서 bo_table만 있고 wr_id는 없는(정렬, 다음 페이지등) url 필터
        and (("bo_table" in url and "wr_id" not in url) == False)
        and (("?mid=" in url and "document_srl" not in url) == False)
    )


def remove_page_query(url: str) -> str:
    # page를 제거해서 diff 때 같은 footer 갖도록 함
    return re.sub(r"&page=\d{1,2}", "", url)
