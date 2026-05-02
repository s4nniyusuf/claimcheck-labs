import time

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


urls = {
    "Women Fashion": "https://www.jumia.com.ng/womens-fashion/"
}
ua = UserAgent()

def fetch_page_html(url):
    headers = {"User-Agent": ua.random}
    response = requests.get(url, headers=headers, timeout=10)
    time.sleep(3)
    if response.status_code == 200:
        print(f"Successfully retrieved data from {url}")
        return response.text
    else:
        print(f"Failed to retrieve data from {url}")
        return None


def parse_data(html):
    soup = BeautifulSoup(html, "lxml")
    print("Data parsing successful")
    return soup


def get_products(soup):
    products = soup.find_all("article", class_="prd")
    print(f"Found {len(products)} products on the page.")
    for product in products:
        core = product.find("a", class_="core")
        product_detail_url = core["href"]
        print(f"Product Detail URL: {product_detail_url}")
        print("-" * 40)
        print("\n")


def main():
    for category, url in urls.items():
        html = fetch_page_html(url)
        if html:
            soup = parse_data(html)
            get_products(soup)


if __name__ == "__main__":
    main() 