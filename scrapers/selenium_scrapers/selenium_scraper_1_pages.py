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

def scrape_quotes_selenium(query=None):
    data = []
    errors = []

    try:
        driver = get_brave_driver()
        driver.get("https://quotes.toscrape.com/js/")
        wait = WebDriverWait(driver, 10)

        start_time = time.time()

        search_term = query.lower() if query else None

        while True:
            # -- Current page scraping --
            quotes_elements = driver.find_elements(By.CSS_SELECTOR, ".quote")

            for q in quotes_elements:
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
            # -- Pagination logic (next button) --
            try:
                load_more_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '.pager .next a'))
                )
                load_more_btn.click()
                time.sleep(0.5)

            except TimeoutException:
                print("Alle sider loaded (eller knap ikke fundet).")
                break

    except Exception as e:
        errors.append(str(e))

    finally:
        if 'driver' in locals():
            driver.quit()

    print(f"Total quotes found and saved: {len(data)}")

    runtime_ms = int((time.time()- start_time) * 1000)

    return {
        "source": "selenium scraper 1 pages",
        "query": query if query else "Alle",
        "runtime_ms": runtime_ms,
        "results": data,
        "errors": errors
    }

if __name__ == "__main__":
    print(scrape_quotes_selenium())