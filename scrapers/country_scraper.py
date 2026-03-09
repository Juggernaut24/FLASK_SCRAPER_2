import time
import requests
from bs4 import BeautifulSoup

def get_safe_text(parent, selector, class_name):
    element = parent.find(selector, class_=class_name)
    if element:
        return element.get_text(strip=True)
    return "N/A"

def country_scraper(query=None):
    base_url = "https://www.scrapethissite.com/pages/simple/"
    current_url = base_url

    results = []
    errors = []

    start_time = time.time()
    
    try:
        response = requests.get(current_url, timeout=10)

        if response.status_code !=200:
            errors.append(f"Kunne ikke hente {current_url}. Status: {response.status_code}")
        else:
            print("Success! Page loaded.")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        country_elements = soup.find_all('div', class_='country')

        for count in country_elements:
            try:
                name = get_safe_text(count, "h3", "country-name")
                capital = get_safe_text(count, "span", "country-capital")
                population = get_safe_text(count, "span", "country-population")
                area = get_safe_text(count, "span", "country-area")

                if query:
                    q = query.lower()
                    match = (q in name.lower() or 
                            q in capital.lower() or 
                            q in population.lower() or 
                            q in area.lower())
                    if not match:
                        continue

                results.append({
                    "name": name,
                    "capital": capital,
                    "population": population,
                    "area": area
                })
            except AttributeError as e:
                continue

    except Exception as e:
        errors.append(f"Kritisk fejl: {str(e)}")

    runtime_ms = int((time.time()- start_time) * 1000)

    return {
        "source": "Country Scraper (BS4)",
        "query": query if query else "Alle",
        "runtime_ms": runtime_ms,
        "results": results,
        "errors": errors
    }