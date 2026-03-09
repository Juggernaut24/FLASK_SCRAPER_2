import time
import requests
from bs4 import BeautifulSoup

def scrape_quotes(query=None):
    """
    Scraper quotes.toscrape.com ved hjælp af BS4.
    Håndterer pagination og returnerer det krævede format.
    """
    base_url = "https://quotes.toscrape.com"
    url = base_url
    
    # Start tidsmåling
    start_time = time.time()
    
    results = []
    errors = []
    
    try:
        # Simpel pagination (stopper hvis der ikke er flere sider eller efter max 3 sider for demo)
        page_count = 0
        max_pages = 3 

        while url and page_count < max_pages:
            response = requests.get(url, timeout=10) # Timeout håndtering
            
            if response.status_code != 200:
                errors.append(f"Fejl ved hentning af {url}: Status {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            quotes = soup.find_all('div', class_='quote')

            for q in quotes:
                text = q.find('span', class_='text').get_text(strip=True)
                author = q.find('small', class_='author').get_text(strip=True)
                # Hent tags og saml dem til en streng
                tags = [tag.get_text(strip=True) for tag in q.find_all('a', class_='tag')]
                
                # Hvis query er angivet, filtrer vi (simpel søgning)
                if query and query.lower() not in text.lower():
                    continue

                results.append({
                    "quote": text,
                    "author": author,
                    "tags": ", ".join(tags)
                })

            # Find næste side
            next_btn = soup.find('li', class_='next')
            if next_btn:
                next_link = next_btn.find('a')['href']
                url = base_url + next_link
                page_count += 1
                time.sleep(0.5) # Vigtigt: Vær høflig overfor serveren
            else:
                url = None

    except Exception as e:
        errors.append(str(e))

    # Beregn runtime i ms
    runtime_ms = int((time.time() - start_time) * 1000)

    # Returner det obligatoriske format
    return {
        "source": "Quotes Scraper (BS4)",
        "query": query if query else "Alle",
        "runtime_ms": runtime_ms,
        "results": results,
        "errors": errors
    }