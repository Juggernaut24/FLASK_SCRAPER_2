import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_dynamic_loading():
    options = Options()
    options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    driver = webdriver.Chrome(options=options)

    driver.get("https://the-internet.herokuapp.com/dynamic_loading/2")

    driver.find_element(By.TAG_NAME, "Button").click()

    wait = WebDriverWait(driver, 10)
    finish_element = wait.until(
        EC.visibility_of_element_located((By.ID, "finish"))
    )

    print(finish_element.text)
    driver.quit()

if __name__ == "__main__":
    scrape_dynamic_loading()