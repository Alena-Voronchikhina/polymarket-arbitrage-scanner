import requests
import json
import time
import csv
from datetime import datetime
import os


def load_logged_entries(file_path="opportunities.csv"):
    entries = set()

    if not os.path.exists(file_path):
        return entries

    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                question = row.get("question", "")
                prices_raw = row.get("prices", "[]")
                price_sum_raw = row.get("price_sum", "0")
                spread_raw = row.get("spread", "0")

                try:
                    prices = [float(p) for p in json.loads(prices_raw)]
                    price_sum = float(price_sum_raw)
                    spread = float(spread_raw)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

                log_key = (
                    question,
                    tuple(round(price, 6) for price in prices),
                    round(price_sum, 6),
                    round(spread, 6),
                )
                entries.add(log_key)
    except OSError:
        return entries

    return entries


logged_entries = load_logged_entries()
print(f"Loaded {len(logged_entries)} prior opportunities from opportunities.csv")


def log_opportunity(question, prices, price_sum, spread):
    file_path = "opportunities.csv"
    file_exists = os.path.exists(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["timestamp", "question", "prices", "price_sum", "spread"])

        writer.writerow([
            datetime.utcnow().isoformat() + "Z",
            question,
            json.dumps(prices),
            f"{price_sum:.6f}",
            f"{spread:.6f}",
        ])

#Fetch Active Events
def fetchActiveEvents():
    url = "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data


def displayData(data):
    print("Market Data:")
    newly_logged_count = 0
    
    # gamma-api returns list directly, clob-api returns {"data": [...]}
    if isinstance(data, list):
        events = data
    else:
        events = data.get("data", data.get("markets", []))
    
    print(f"Found {len(events)} events\n")
    
    for event in events:
        sub_markets = event.get('markets', [])
        
        for m in sub_markets:
            question = m.get('question', '')
            prices_raw = m.get('outcomePrices', [])
            
            # Parse and convert prices
            try:
                prices = [float(p) for p in json.loads(prices_raw) if p]
            except (json.JSONDecodeError, TypeError, ValueError):
                prices = []
            
            # Skip markets with incomplete price data
            if len(prices) < 2:
                continue
            
            total = sum(prices)
            
            # Only print if mispriced
            if abs(total - 1.0) > 0.02:
                spread = max(prices) - min(prices)
                log_key = (
                    question,
                    tuple(round(price, 6) for price in prices),
                    round(total, 6),
                    round(spread, 6),
                )

                if log_key not in logged_entries:
                    log_opportunity(question, prices, total, spread)
                    logged_entries.add(log_key)
                    newly_logged_count += 1

                print(f"⚠️ {question}")
                print(f"   Prices: {prices} sum={total:.3f}")

    return newly_logged_count

def main():
    while True:
        try:
            data = fetchActiveEvents()
            newly_logged_count = displayData(data)
            print(f"New opportunities logged this cycle: {newly_logged_count}")
        except requests.RequestException as error:
            print(f"Request error: {error}")

        print("waiting 30s...")
        time.sleep(30)


if __name__ == "__main__":
    main()


