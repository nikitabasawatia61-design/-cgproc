"""One-off script to list all field labels on a tender detail page."""
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from scraper.auth import authenticate
from scraper.listing import get_tender_list

URL = "https://eproc.cgstate.gov.in/CHEPS/business/getOpenRfqListAction.do"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options,
)
wait = WebDriverWait(driver, 30)

try:
    driver.get(URL)
    if not authenticate(driver):
        raise SystemExit("auth failed")

    wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'viewRfq')]")))
    tenders = get_tender_list(driver, silent=True)
    link = driver.find_element(By.XPATH, f"//a[normalize-space()='{tenders[0]['number']}']")
    driver.execute_script("arguments[0].click();", link)
    time.sleep(3)

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "fieldLabel")))
    labels = driver.find_elements(By.CLASS_NAME, "fieldLabel")
    for label in labels:
        key = label.text.strip().replace("\n", " ")
        try:
            value = label.find_element(
                By.XPATH, "./following-sibling::*[contains(@class,'field')][1]"
            ).text.strip().replace("\n", " ")[:80]
        except Exception:
            value = ""
        print(f"{key!r} => {value!r}")
finally:
    driver.quit()
