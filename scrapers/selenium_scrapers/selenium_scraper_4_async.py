from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_async_hackernews():
    options = Options()
    options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    driver = webdriver.Chrome(options=options)

    driver.get("https://hn.algolia.com/")

    wait = WebDriverWait(driver, 10)

    search_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search']"))
    )

    first_original_article = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".Story"))
    )

    search_input.send_keys("Selenium Python")

    wait.until(
        EC.staleness_of(first_original_article)
    )

    new_articles = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".Story"))
    )

    print(f"Fandt {len(new_articles)} nye asynkrone resultater. her er de første 5")
    for article in new_articles[:5]:

        title = article.find_element(By.CSS_SELECTOR, ".Story_title").text
        print(f"- {title}")

    driver.quit()

if __name__ == "__main__":
    scrape_async_hackernews()