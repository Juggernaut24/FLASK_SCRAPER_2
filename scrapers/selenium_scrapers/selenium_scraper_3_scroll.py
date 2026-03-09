import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

def get_brave_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    driver = webdriver.Chrome(options=options)
    return driver

def scrape_infinite_scroll(query=None):
    data = []
    errors = []
    
    try:
        driver = get_brave_driver()
        driver.get("https://quotes.toscrape.com/scroll")
        wait = WebDriverWait(driver, 5)
        
        start_time = time.time()
        css_selector = ".quote"
        search_term = query.lower() if query else None

        while True:
            current_items = driver.find_elements(By.CSS_SELECTOR, css_selector)
            current_count = len(current_items)
            print(f"current loaded iteams: {current_count}")
            

            # --- SCROLLING DOWN THE PAGE ---
            print("--- SCROLLING DOWN THE PAGE ---")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            try:
                wait.until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, css_selector)) > current_count
                )
            except TimeoutException:
                print("Reached the end of the page. No new items loaded.")
                break

        print("Starting data extraction...")
        all_quotes = driver.find_elements(By.CSS_SELECTOR, css_selector)

        for q in all_quotes:
            text = q.find_element(By.CSS_SELECTOR, ".text").text
            author = q.find_element(By.CSS_SELECTOR, ".author").text
            tags = [t.text for t in q.find_elements(By.CSS_SELECTOR, ".tag")]
            
            if search_term:
                matches_text = search_term in text.lower()
                matches_author = search_term in author.lower()
                matches_tags = any(search_term in tag.lower() for tag in tags)

                if not (matches_text or matches_author or matches_tags):
                    continue

            data.append({
                "text": text,
                "author": author,
                "tags": ", ".join(tags)
            })
    except Exception as e:
        errors.append(str(e))

    finally:
        if 'driver' in locals():
            driver.quit()

    print(f"Successfully scraped {len(data)} items.")

    runtime_ms = int((time.time()- start_time) * 1000)
    
    return {
        "source": "selenium scraper 3 scroll",
        "query": query if query else "Alle",
        "runtime_ms": runtime_ms,
        "results": data,
        "errors": errors
    }

if __name__ == "__main__":
    print(scrape_infinite_scroll())