import time
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- Konfiguration ---
CATEGORIES = [
    "https://books.toscrape.com/catalogue/category/books/historical_42/index.html",
    "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    "https://books.toscrape.com/catalogue/category/books/classics_6/index.html"
]

RATING_MAP = { "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5 }

def get_soup(url):
    """Hjælpefunktion til at hente suppe sikkert"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            response.encoding = 'utf-8'
            return BeautifulSoup(response.text, "html.parser")
    except Exception:
        pass
    return None

def scrape_book_details(book_url):
    """Går ind på detaljesiden og henter ekstra info"""
    soup = get_soup(book_url)
    if not soup:
        return {"description": "Fejl", "upc": "N/A", "availability": 0}
    
    # Hent beskrivelse
    desc_elem = soup.select_one("#product_description ~ p")
    description = desc_elem.text.strip() if desc_elem else "Ingen beskrivelse"

    # Hent tabeldata (UPC og Lager)
    upc = "Ukendt"
    availability = 0
    
    for row in soup.select("table.table-striped tr"):
        header = row.find("th").text
        value = row.find("td").text
        
        if header == "UPC":
            upc = value
        elif header == "Availability":
            numbers = re.findall(r'\d+', value)
            availability = int(numbers[0]) if numbers else 0

    return {"description": description, "upc": upc, "availability": availability}

def scrape_books_advanced(query=None):
    """
    Hovedfunktion til Flask.
    Scraper kategorier -> lister -> detaljesider.
    """
    start_time = time.time()
    results = []
    errors = []
    seen_upcs = set()
    
    # SIKKERHEDSGRÆNSE: Stopper efter 15 bøger for at undgå timeout i browseren
    MAX_BOOKS = 15 

    try:
        for category_url in CATEGORIES:
            if len(results) >= MAX_BOOKS: 
                break
                
            current_url = category_url
            
            # Loop gennem sider i kategorien
            while current_url and len(results) < MAX_BOOKS:
                soup = get_soup(current_url)
                if not soup:
                    errors.append(f"Kunne ikke læse: {current_url}")
                    break

                articles = soup.select("article.product_pod")
                
                for article in articles:
                    if len(results) >= MAX_BOOKS: 
                        break

                    try:
                        # 1. Hent info fra listevisning
                        title = article.h3.a["title"]
                        price = article.select_one(".price_color").text
                        
                        rating_class = article.select_one(".star-rating")["class"]
                        rating = RATING_MAP.get(rating_class[1], 0) if len(rating_class) > 1 else 0
                        
                        detail_rel_link = article.h3.a["href"]
                        detail_url = urljoin(current_url, detail_rel_link)

                        # Simpel søgning (hvis brugeren har indtastet noget)
                        if query and query.lower() not in title.lower():
                            continue

                        # 2. Gå ind på detaljesiden (Dette tager tid!)
                        # time.sleep(0.2) # Lille pause for at være høflig
                        details = scrape_book_details(detail_url)

                        # 3. Dedup check
                        if details["upc"] in seen_upcs:
                            continue
                        seen_upcs.add(details["upc"])

                        # 4. Gem data
                        results.append({
                            "Titel": title,
                            "Pris": price,
                            "Rating": f"{rating}/5",
                            "Lager": details["availability"],
                            "UPC": details["upc"],
                            # "Beskrivelse": details["description"][:50] + "..." # Korter beskrivelsen af
                        })

                    except Exception as e:
                        errors.append(f"Fejl ved bog: {str(e)}")

                # Find næste side i kategorien
                next_btn = soup.select_one("li.next a")
                if next_btn:
                    current_url = urljoin(current_url, next_btn["href"])
                else:
                    current_url = None

    except Exception as e:
        errors.append(f"Kritisk fejl: {str(e)}")

    runtime_ms = int((time.time() - start_time) * 1000)

    return {
        "source": "Advanced Books Scraper (Detail Pages)",
        "query": query if query else "Kategorier (Max 15 bøger)",
        "runtime_ms": runtime_ms,
        "results": results,
        "errors": errors
    }