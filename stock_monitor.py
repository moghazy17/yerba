import os
import smtplib
import requests
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

PRODUCTS_URL = "https://drinkyerbanow.com/products.json"
TARGET_HANDLES = {
    # "pipore-yerba-mate-250g",
    "wooden-cup-100-real-wood-torpedo"
}

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")


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


def send_email(in_stock):
    items = "\n".join(f"  - {name}" for name in in_stock)
    body = f"The following products are back in stock on drinkyerbanow.com:\n\n{items}\n\nGo grab them!"
    msg = MIMEText(body)
    msg["Subject"] = "Yerba Stock Alert: Items Available!"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = NOTIFY_EMAIL

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)
    print("Email notification sent.")


if __name__ == "__main__":
    in_stock = check_stock()
    if in_stock:
        if all([EMAIL_ADDRESS, EMAIL_APP_PASSWORD, NOTIFY_EMAIL]):
            send_email(in_stock)
        else:
            print("Email credentials not configured in .env — skipping notification.")
    else:
        print("Nothing in stock. No notification sent.")
