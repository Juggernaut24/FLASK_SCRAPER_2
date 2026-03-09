import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scrape_books(query=None):
    base_url = "https://books.toscrape.com/"
    # Hvis query er en URL (brugeren har indtastet et direkte link), brug den, ellers start fra forsiden
    current_url = base_url
    
    results = []
    errors = []
    
    start_time = time.time()
    page_count = 0
    max_pages = 3  # VIGTIGT: Begræns antal sider for demo (ellers venter du i 5 minutter)

    try:
        while current_url and page_count < max_pages:
            response = requests.get(current_url, timeout=10)
            
            if response.status_code != 200:
                errors.append(f"Kunne ikke hente {current_url}. Status: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            book_elements = soup.find_all('article', class_='product_pod')

            for book in book_elements:
                try:
                    name = book.h3.a['title']
                    price = book.find("p", class_="price_color").get_text()
                    stock_text = book.find("p", class_="instock availability").get_text(strip=True)
                    
                    # Simpel filtrering: Hvis brugeren søgte på noget, gem kun bøger der matcher
                    if query and query.lower() not in name.lower():
                        continue

                    results.append({
                        "book_name": name,
                        "price": price,
                        "in_stock": stock_text
                    })
                except AttributeError as e:
                    # Hvis en bog mangler et felt, spring over men log det ikke som en kritisk fejl
                    continue

            # Pagination logik
            next_btn = soup.find('li', class_='next')
            if next_btn:
                next_page_path = next_btn.find('a')['href']
                current_url = urljoin(current_url, next_page_path)
                page_count += 1
                time.sleep(0.20) # Ventetid
            else:
                current_url = None

    except Exception as e:
        errors.append(f"Kritisk fejl: {str(e)}")

    # Beregn runtime
    runtime_ms = int((time.time() - start_time) * 1000)

    # Returner data til Flask (Controlleren)
    return {
        "source": "Books Scraper (BS4)",
        "query": query if query else "Alle (Max 3 sider)",
        "runtime_ms": runtime_ms,
        "results": results,
        "errors": errors
    }