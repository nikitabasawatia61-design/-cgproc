import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from scraper.auth import authenticate
from scraper.listing import get_tender_list
from scraper.detail import scrape_tender_details
import database as db

URL = "https://eproc.cgstate.gov.in/CHEPS/business/getOpenRfqListAction.do"


def wait_for_listing(wait):
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href,'viewRfq')]")
        )
    )


def go_to_page(driver, wait, page_no):
    print(f"Going to Page {page_no}")

    if page_no == 1:
        wait_for_listing(wait)
        print("Ready on Page 1")
        return True

    driver.execute_script(f"submitPage({page_no});")
    time.sleep(5)
    wait_for_listing(wait)
    print(f"Ready on Page {page_no}")
    return True


def recover_to_page(driver, wait, page_no):
    print(f"Recovering to Page {page_no}")

    if not open_url(driver, URL):
        print("Recovery could not open portal")
        return False
    time.sleep(2)

    if not authenticate(driver):
        print("Recovery authentication failed")
        return False

    wait_for_listing(wait)

    if page_no > 1:
        print(f"Going back to Page {page_no} after recovery")
        driver.execute_script(f"submitPage({page_no});")
        time.sleep(5)
        wait_for_listing(wait)

    print(f"Recovered to Page {page_no}")
    return True


def return_to_same_page(driver, wait, page_no):
    print("Clicking BACK button")

    try:
        driver.execute_script("backTo(1);")
        time.sleep(2)
    except Exception:
        print("backTo not available. Using full recovery.")
        return recover_to_page(driver, wait, page_no)

    if not authenticate(driver):
        print("Authentication failed after BACK. Using recovery.")
        return recover_to_page(driver, wait, page_no)

    print("Landed on Page 1 after authentication")

    if page_no > 1:
        print(f"Going back to Page {page_no}")
        driver.execute_script(f"submitPage({page_no});")
        time.sleep(5)

    wait_for_listing(wait)
    print(f"Ready again on Page {page_no}")
    return True


def open_url(driver, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            print(f"Opening portal (attempt {attempt}/{retries})...")
            driver.get(url)
            return True
        except (TimeoutException, WebDriverException, Exception) as error:
            print(f"Page load failed on attempt {attempt}: {type(error).__name__}: {error}")
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
            time.sleep(10)
    return False


def create_driver(headless=False):
    RemoteConnection.set_timeout(300)

    options = Options()
    options.page_load_strategy = "none"
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    options.add_argument("--force-device-scale-factor=0.9")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.set_page_load_timeout(300)
    driver.set_script_timeout(120)
    return driver


def run_scraper(start_page=1, headless=False, full_scan=True):
    """
    Scrape tenders from the CG e-procurement portal.

    full_scan: scan every listing page so missing tenders are fetched and
    counts stay aligned with the live portal.
    """
    db.init_db()
    existing_tenders = db.get_existing_tender_numbers()

    print(f"Already saved tenders: {len(existing_tenders)}")

    driver = create_driver(headless=headless)
    wait = WebDriverWait(driver, 45)

    new_count = 0
    skipped_count = 0
    portal_numbers = set()

    try:
        if not open_url(driver, URL):
            print("Could not open portal")
            return {
                "new": 0,
                "skipped": 0,
                "portal_total": 0,
                "removed_stale": 0,
                "error": "portal timeout",
            }

        if not authenticate(driver):
            print("Login/authentication failed")
            return {
                "new": 0,
                "skipped": 0,
                "portal_total": 0,
                "removed_stale": 0,
                "error": "authentication failed",
            }

        wait_for_listing(wait)

        page_no = start_page

        while True:
            print(f"\n========== PAGE {page_no} ==========")

            try:
                go_to_page(driver, wait, page_no)
            except Exception as e:
                print(f"Could not open Page {page_no}: {e}")
                if not recover_to_page(driver, wait, page_no):
                    print("Could not recover. Stopping.")
                    break

            tenders = get_tender_list(driver)
            total = len(tenders)
            print(f"Found {total} tenders on Page {page_no}")

            if total == 0:
                print("No tenders found. Scraping completed.")
                break

            for tender in tenders:
                portal_numbers.add(str(tender["number"]).strip())

            index = 0

            while index < total:
                try:
                    tenders = get_tender_list(driver, silent=True)

                    if index >= len(tenders):
                        print("Tender list changed. Moving to next page.")
                        break

                    tender = tenders[index]
                    tender_no = str(tender["number"]).strip()

                    if tender_no in existing_tenders:
                        print(f"Skipping existing tender: {tender_no}")
                        skipped_count += 1
                        index += 1
                        continue

                    print(f"\nOpening Tender {index + 1}/{total} on Page {page_no}: {tender_no}")

                    link = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//a[normalize-space()='{tender_no}']")
                        )
                    )

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        link,
                    )
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(3)

                    details = scrape_tender_details(driver)

                    required_data = {
                        "tender_no": details.get("tender_no", tender_no),
                        "name": details.get("name", ""),
                        "department": details.get("department", ""),
                        "amount": details.get("amount", ""),
                        "last_date": details.get("last_date", ""),
                        "area_city": details.get("area_city", ""),
                    }

                    print(required_data)
                    db.save_tender(required_data)

                    existing_tenders.add(tender_no)
                    new_count += 1
                    print(f"Saved tender: {tender_no}")

                    if not return_to_same_page(driver, wait, page_no):
                        if not recover_to_page(driver, wait, page_no):
                            print("Could not recover. Stopping.")
                            break

                    index += 1

                except Exception as e:
                    print(f"Error while scraping tender at index {index + 1}: {e}")
                    if not recover_to_page(driver, wait, page_no):
                        print("Could not recover. Stopping.")
                        break
                    continue

            print(f"\nCompleted Page {page_no}")

            if not full_scan:
                break

            page_no += 1

    finally:
        driver.quit()

    removed_stale = db.remove_tenders_not_on_portal(portal_numbers)

    summary = {
        "new": new_count,
        "skipped": skipped_count,
        "portal_total": len(portal_numbers),
        "removed_stale": removed_stale,
        "error": None,
    }
    print("\n========== FINAL SUMMARY ==========")
    print(f"Portal listing total: {summary['portal_total']}")
    print(f"New tenders scraped: {new_count}")
    print(f"Skipped existing tenders: {skipped_count}")
    print(f"Removed stale tenders: {removed_stale}")
    return summary
