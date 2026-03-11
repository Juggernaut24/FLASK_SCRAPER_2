import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request
from elasticsearch import Elasticsearch

from scrapers.example_quotes import scrape_quotes
from scrapers.mandag_books import scrape_books
from scrapers.tirsdag_books import scrape_books_advanced
from scrapers.country_scraper import country_scraper
from scrapers.selenium_scrapers.selenium_scraper_1_pages import scrape_quotes_selenium
from scrapers.selenium_scrapers.selenium_scraper_3_scroll import scrape_infinite_scroll
from scrapers.new_scrapers.rekvizitai_scraper_3 import scrape_rekvizitai_for_flask
from scrapers.new_scrapers.tjekbildk_scraper_8 import scrape_tjekbil_for_flask

import urllib3

app = Flask(__name__)

app.json.ensure_ascii = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRAPERS = {
    'quotes': scrape_quotes,
    'books': scrape_books,
    'books advanced': scrape_books_advanced,
    'country': country_scraper,
    'selenium quotes': scrape_quotes_selenium,
    'selenium scroll': scrape_infinite_scroll,
    'rekvizitai': scrape_rekvizitai_for_flask,
    'tjekbil': scrape_tjekbil_for_flask
    }

ES_INDICES = {
    'rekvizitai': 'search-com_rekvizitai',
    'tjekbil': 'search-com_bil'
}

# Sørg for at output mappen findes
OUTPUT_FOLDER = 'outputs'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "mZUZLZ3sIIbh9H6d3ruv"),
    verify_certs=False,
    request_timeout=30,
    headers={"Accept": "application/json", "Content-Type": "application/json"}
)

try:
    if es.ping():
        print("Hurra connected to ES")
    else:
        print("Kunne ikke pinge Elasticsearch.")

except Exception as e:
    print(f"Forbindelsesfejl: {e}")


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

        # --- 2. Overfør data til ElasticSearch ---
        target_index = ES_INDICES.get(scraper_choice)
        scraped_items = data.get("results") or data.get("result")

        if es and target_index and scraped_items:
            # GMT +1 København
            dansk_tidszone = timezone(timedelta(hours=1))
            current_time = datetime.now(dansk_tidszone).isoformat()

            for item in scraped_items:
                item["@timestamp"] = current_time
                try:
                    es.index(index=target_index, document=item)
                except Exception as e:
                    if "errors" not in data:
                        data['errors'] = []
                    data['errors'].append(f"Elasticsearch Index Error: {str(e)}")

    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)