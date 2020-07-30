import requests

# import re
response = requests.get(url="https://linkmoum.net")

body_fs = open("./body.html", mode="w", encoding="utf-8").write(response.text)
