import requests

session = requests.Session()
url = "https://www.ambitionbox.com/_next/data/ZH-MX7uHTRU8kaKFErhTy/overview/uber-overview.json"

headers= {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36', 'accept': '*/*', 'accept-encoding': 'gzip, deflate, br, zstd', 'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8', 'cache-control': 'no-cache'}

response = session.get(url, headers=headers)
print(response.status_code)