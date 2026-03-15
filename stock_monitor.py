import os
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

PRODUCTS_URL = "https://drinkyerbanow.com/products.json"
TARGET_HANDLES = {
    # "pipore-yerba-mate-250g",
    "wooden-cup-100-real-wood-torpedo"
}

# Amazfit Helio Strap on Amazon AE — monitoring both variants
# B0F8HJCB47: Helio Strap (Android)
# B0F9J3TFMB: Helio Strap (Android & iPhone)
AMAZON_AE_PRODUCTS = {
    "B0F8HJCB47": "Amazfit Helio Strap (Amazon AE - Android)",
    "B0F9J3TFMB": "Amazfit Helio Strap (Amazon AE - Android & iPhone)",
}

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")

AMAZON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AE,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_products():
    products = []
    page = 1
    while True:
        resp = requests.get(PRODUCTS_URL, params={"page": page, "limit": 250}, timeout=30)
        resp.raise_for_status()
        batch = resp.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        page += 1
    return products


def check_stock():
    products = fetch_products()
    in_stock = []
    checked = set()

    for product in products:
        handle = product.get("handle")
        if handle not in TARGET_HANDLES:
            continue
        checked.add(handle)
        available = any(v.get("available", False) for v in product.get("variants", []))
        title = product.get("title", handle)
        if available:
            in_stock.append(title)
            print(f"IN STOCK: {title}")
        else:
            print(f"Sold out: {title}")

    for handle in TARGET_HANDLES - checked:
        print(f"NOT FOUND: {handle}")

    return in_stock


def check_amazon_ae_stock():
    """Check availability of Helio Strap on Amazon AE. Returns list of available product names."""
    available_items = []

    for asin, name in AMAZON_AE_PRODUCTS.items():
        url = f"https://www.amazon.ae/dp/{asin}"
        try:
            resp = requests.get(url, headers=AMAZON_HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            availability_div = soup.find(id="availability")
            add_to_cart = soup.find(id="add-to-cart-button")

            if add_to_cart:
                print(f"IN STOCK: {name}")
                available_items.append(f"{name}: {url}")
            elif availability_div and "currently unavailable" in availability_div.get_text().lower():
                print(f"Currently unavailable: {name}")
            else:
                print(f"Status unclear (possible bot block): {name}")
        except requests.RequestException as e:
            print(f"Error checking {name}: {e}")

    return available_items


def send_email(in_stock):
    items = "\n".join(f"  - {name}" for name in in_stock)
    body = f"The following products are now available:\n\n{items}\n\nGo grab them!"
    msg = MIMEText(body)
    msg["Subject"] = "Stock Alert: Items Available!"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = NOTIFY_EMAIL

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)
    print("Email notification sent.")


if __name__ == "__main__":
    in_stock = check_stock()
    amazon_in_stock = check_amazon_ae_stock()

    all_available = in_stock + amazon_in_stock

    if all_available:
        if all([EMAIL_ADDRESS, EMAIL_APP_PASSWORD, NOTIFY_EMAIL]):
            send_email(all_available)
        else:
            print("Email credentials not configured in .env — skipping notification.")
    else:
        print("Nothing in stock. No notification sent.")
