import time
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


HEADLESS = False
url = "https://www.jumia.com.ng/category-fashion-by-jumia/"
MAX_PAGES = 3


def setup_browser(playwright):
    """Launch Chromium and return (browser, context, page)."""
    browser = playwright.chromium.launch(
        headless=HEADLESS,
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = context.new_page()
    return browser, context, page


def safe_get(parent, tag, class_name):
    """Return element text or None — never crashes on missing elements."""
    el = parent.find(tag, class_=class_name)
    return el.text.strip() if el else None


def parse_products(soup):
    """Return a list of product dicts from a listing page soup."""
    products = []
    for card in soup.find_all("div", class_="info"):
        href = card.parent.get("href", "")
        product_url = f"https://www.jumia.com.ng{href}"
        product_id  = product_url.split("-")[-1].split(".")[0]
        products.extend([{
            "product_id":            product_id,
            "url":           product_url,
            "name":          safe_get(card, "h3", "name"),
            "current_price": safe_get(card, "div", "prc"),
            "old_price":     safe_get(card, "div", "old"),
            "rating":        safe_get(card, "div", "stars _s"),
        }])
    return products


def print_product_summary(product, index, total):
    """Print the listing-level info for one product."""
    print(f"Product {index}/{total}  ID: {product['product_id']}")
    print(f"  URL:           {product['url']}")
    print(f"  Name:          {product['name']}")
    print(f"  Current Price: {product['current_price']}")
    print(f"  Old Price:     {product['old_price']}")
    print(f"  Rating:        {product['rating']}")
  


def parse_reviews(soup, product_id):
    """Extract and print all reviews from a product page soup."""
    review_container = soup.find("div", class_="cola -phm -df -d-co")
    if not review_container:
        print("  No reviews found.")
        return []
    
    reviews_data = []
    reviews = review_container.find_all("article", class_="-pvs -hr _bet")
    for review in reviews:
        rating = safe_get(review, "div", "stars _m _al -mvs")
        review_title = safe_get(review, "h3", "-m -fs16 -pvs")
        review_text  = safe_get(review, "p", "-pvs")
        review_date = (
             review
            .find("div", class_="-df -j-bet -i-ctr -gy5")
            .find("div", class_="-pvs")
            .find_all("span")[0]
            .text.strip()
        )
        reviewer_name = (
            review
            .find("div", class_="-df -j-bet -i-ctr -gy5")
            .find("div", class_="-pvs")
            .find_all("span")[1]
            .text.strip()
        )
        reviews_data.append({
            "product_id": product_id,
            "reviewer_name": reviewer_name,
            "review_date": review_date,
            "rating": rating,
            "review_title": review_title,
            "review_text": review_text
        })

    time.sleep(2)
    return reviews_data


def scrape_product_description_and_review(page, product_url, product_id):
    """Visit a product page, print description + reviews, then go back."""
    try:
        page.goto(product_url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        soup = BeautifulSoup(page.content(), "lxml")

        img_el = soup.find("img", class_="-fw -fh")
        image_url = img_el.get("src") or img_el.get("data-src") if img_el else None

        desc_el = soup.find("div", class_="markup -mhm -pvl -oxa -sc")
        description = desc_el.text.strip() if desc_el else "N/A"

        see_all = soup.find("a", class_="btn _def _ti -mhs -fsh0")
        if see_all and see_all.text.strip().startswith("See All"):
            reviews_url = f"https://www.jumia.com.ng{see_all['href']}"
            print(f"  Navigating to all reviews: {reviews_url}")

            page.goto(reviews_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_selector("div.cola", timeout=10000)
            reviews_soup = BeautifulSoup(page.content(), "lxml")
            reviews = parse_reviews(soup=reviews_soup, product_id=product_id)

            page.go_back()  
            time.sleep(2)
        else:
            # Fall back to reviews already on the product page
            reviews = parse_reviews(soup=soup, product_id=product_id)

        return image_url, description, reviews

    except PlaywrightTimeoutError:
        print(f"  Timed out loading product page: {product_url}")
        return "N/A", "N/A", []
    finally:
        page.go_back()
        time.sleep(2)


def go_to_next_page(page):
    """
    Click the Next Page button if visible.
    Returns True on success, False when there are no more pages.
    """
    try:
        page.wait_for_selector("a.pg[aria-label='Next Page']", timeout=10000)
        next_btn = page.locator("a.pg[aria-label='Next Page']")

        if not next_btn.is_visible():
            print("No more pages.")
            return False

        next_btn.scroll_into_view_if_needed()
        next_btn.click()
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        return True

    except PlaywrightTimeoutError:
        print("Pagination timed out — treating as last page.")
        return False
    except Exception as e:
        print(f"Pagination error: {e}")
        return False


def save_products_details_to_csv(products):
    df = pd.DataFrame(products)
    main_dir = Path(__file__).parent.parent 
    file_path = main_dir  / 'data' / 'raw' / 'products.csv'
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    print("Product details saved to data/raw/products.csv")


def save_products_reviews_to_csv(reviews):
    df = pd.DataFrame(reviews)
    main_dir = Path(__file__).parent.parent 
    file_path = main_dir / 'data' / 'raw' / 'reviews.csv'
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    print("Product reviews saved to data/raw/reviews.csv")


def scrape_jumia(page, url):
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(2)
        page.get_by_role("button", name="Accept All Cookies").click()
        time.sleep(2)
        page.wait_for_selector("div.info", timeout=15000)
        print("Page loaded successfully. Starting scrape")
    except PlaywrightTimeoutError:
        print("Page load timed out")
    
    page_number = 1
    all_products = []
    all_reviews = []

    while page_number <= MAX_PAGES:
        print(f"\n--- Scraping page {page_number} ---")
        soup = BeautifulSoup(page.content(), "lxml")

        # Products found on this page only
        page_products = parse_products(soup=soup)
        print(f"Found {len(page_products)} products on page {page_number}")

        for i, product in enumerate(page_products, start=1):
            print_product_summary(product=product, index=i, total=len(page_products))

            image_url, description, reviews = scrape_product_description_and_review(
                page=page, 
                product_url=product["url"], 
                product_id=product["product_id"]
            )
            
            product["image_url"] = image_url
            product["description"] = description

            print(f"Description: {description[:80]}")
            print(f"Image URL: {image_url}")
            print()
            print(f"Reviews found: {len(reviews)}")
            print("Reviews:")
            for review in reviews:
                print(review)

            print("\n" + "=" * 80 + "\n")
            all_reviews.extend(reviews)

        all_products.extend(page_products)

        if not go_to_next_page(page):
            break

        page_number += 1
    
    save_products_details_to_csv(all_products)
    save_products_reviews_to_csv(all_reviews)


def main():
    with sync_playwright() as playwright:
        browser, context, page = setup_browser(playwright=playwright)

        try:
            scrape_jumia(page=page, url=url)
        finally:
            browser.close()

if __name__ == "__main__":
    main()