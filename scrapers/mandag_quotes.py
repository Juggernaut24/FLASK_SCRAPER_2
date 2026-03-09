import requests
from bs4 import BeautifulSoup
import json
import os

os.makedirs('outputs', exist_ok = True)

base_url = "https://quotes.toscrape.com/"
current_url = base_url
all_quotes = []

while current_url:
    response = requests.get(current_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    quote_elements = soup.find_all('div', class_='quote')

    for quote in quote_elements:

        text = quote.find('span', class_='text').get_text()
        author = quote.find('small', class_='author').get_text()

        tags = [tag.get_text() for tag in quote.find_all('a', class_='tag')]

        all_quotes.append({
            "quote": text,
            "author": author,
            "tags": tags
        })

    next_btn = soup.find('li', class_='next')
    if next_btn:

        next_page_path = next_btn.find('a')['href']
        current_url = base_url + next_page_path
    else:
        current_url = None

with open('outputs/quotes_bs4.json', 'w', encoding='utf-8') as f:
    json.dump(all_quotes, f, ensure_ascii=False, indent=4)

print(f"Scraping complete! Total quotes found: {len(all_quotes)}")