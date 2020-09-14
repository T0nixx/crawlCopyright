import requests


def request_with_fake_headers(url: str, referer="https://www.google.com"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
        "referer": referer,
    }

    # 함수를 return 하는 방식으로 바꿀 수 있을 것 같은데?
    return requests.get(url, headers=headers)