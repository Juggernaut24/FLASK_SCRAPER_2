import os
import json
from datetime import datetime
from flask import Flask, render_template, request
from scrapers.example_quotes import scrape_quotes
from scrapers.mandag_books import scrape_books
from scrapers.tirsdag_books import scrape_books_advanced
from scrapers.country_scraper import country_scraper
from scrapers.selenium_scrapers.selenium_scraper_1_pages import scrape_quotes_selenium
from scrapers.selenium_scrapers.selenium_scraper_3_scroll import scrape_infinite_scroll

app = Flask(__name__)

SCRAPERS = {
    'quotes': scrape_quotes,
    'books': scrape_books,
    'books advanced': scrape_books_advanced,
    'country': country_scraper,
    'selenium quotes': scrape_quotes_selenium,
    'selenium scroll': scrape_infinite_scroll
    }

# Sørg for at output mappen findes
OUTPUT_FOLDER = 'outputs'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    data = None

    if request.method == 'POST':
        scraper_choice = request.form.get('scraper_choice')
        user_query = request.form.get('query')

        scraper_function = SCRAPERS.get(scraper_choice)

        if scraper_function:
            data = scraper_function(user_query)
        else:
            data = {
                "source": "Ukendt",
                "result": [],
                "runtime_ms": 0,
                "errors": ["Scraper ikke implementeret endnu"]
            }

        # 3. Gem resultatet som JSON fil (YYYYMMDD_HHMMSS_scrapername.json)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{scraper_choice}.json"
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)