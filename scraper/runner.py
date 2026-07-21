import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from scraper.auth import authenticate
from scraper.checkpoint import (
    clear_listing_checkpoint,
    load_listing_checkpoint,
    save_listing_checkpoint,
)
from scraper.listing import get_tender_list
from scraper.detail import scrape_tender_details
import database as db

URL = "https://eproc.cgstate.gov.in/CHEPS/business/getOpenRfqListAction.do"
PAGE_RETRIES = 3
MAX_PAGES = 250


def wait_for_listing(driver, page_no=1):
    timeout = 45 if page_no <= 15 else 75
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href,'viewRfq')]")
        )
    )


def go_to_page(driver, page_no):
    print(f"Going to Page {page_no}")

    if page_no == 1:
        wait_for_listing(driver, page_no)
        print("Ready on Page 1")
        return True

    sleep_seconds = 5 if page_no <= 15 else 8
    for attempt in range(1, PAGE_RETRIES + 1):
        try:
            driver.execute_script(f"submitPage({page_no});")
            time.sleep(sleep_seconds)
            wait_for_listing(driver, page_no)
            print(f"Ready on Page {page_no}")
            return True
        except Exception as error:
            print(
                f"Page {page_no} navigation failed "
                f"(attempt {attempt}/{PAGE_RETRIES}): {error}"
            )
            time.sleep(5)
    return False


def recover_to_page(driver, page_no):
    print(f"Recovering to Page {page_no}")

    try:
        if not open_url(driver, URL):
            print("Recovery could not open portal")
            return False
        time.sleep(2)

        if not authenticate(driver):
            print("Recovery authentication failed")
            return False

        wait_for_listing(driver, page_no)

        if page_no > 1:
            print(f"Going back to Page {page_no} after recovery")
            sleep_seconds = 5 if page_no <= 15 else 8
            for attempt in range(1, PAGE_RETRIES + 1):
                try:
                    driver.execute_script(f"submitPage({page_no});")
                    time.sleep(sleep_seconds)
                    wait_for_listing(driver, page_no)
                    break
                except Exception as error:
                    print(
                        f"Recovery page {page_no} failed "
                        f"(attempt {attempt}/{PAGE_RETRIES}): {error}"
                    )
                    if attempt == PAGE_RETRIES:
                        return False
                    time.sleep(8)

        print(f"Recovered to Page {page_no}")
        return True
    except Exception as error:
        print(f"Recovery failed for page {page_no}: {error}")
        return False


def return_to_same_page(driver, page_no):
    print("Clicking BACK button")

    try:
        driver.execute_script("backTo(1);")
        time.sleep(2)
    except Exception:
        print("backTo not available. Using full recovery.")
        return recover_to_page(driver, page_no)

    if not authenticate(driver):
        print("Authentication failed after BACK. Using recovery.")
        return recover_to_page(driver, page_no)

    print("Landed on Page 1 after authentication")

    if page_no > 1:
        print(f"Going back to Page {page_no}")
        return go_to_page(driver, page_no)

    wait_for_listing(driver, page_no)
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
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    options.add_argument("--force-device-scale-factor=0.9")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.page_load_strategy = "eager"

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )


def open_listing_page(driver, page_no):
    for attempt in range(1, PAGE_RETRIES + 1):
        if go_to_page(driver, page_no):
            return True

        print(f"Retrying page {page_no} after recovery (attempt {attempt}/{PAGE_RETRIES})...")
        if recover_to_page(driver, page_no):
            return True
        time.sleep(10)

    return False


def collect_portal_listings(driver, start_page=1, resume=True):
    """Phase 1: walk listing pages and collect tender numbers only."""
    checkpoint_numbers, checkpoint_page, checkpoint_done = load_listing_checkpoint()
    portal_numbers = set(checkpoint_numbers)
    scan_completed = checkpoint_done

    page_no = start_page
    if resume and start_page == 1 and not checkpoint_done and checkpoint_numbers:
        page_no = checkpoint_page + 1
        print(
            f"Resuming listing scan from page {page_no} "
            f"({len(portal_numbers)} tenders loaded from checkpoint)"
        )

    while page_no <= MAX_PAGES:
        print(f"\n========== LISTING PAGE {page_no} ==========")

        if not open_listing_page(driver, page_no):
            print(f"Listing scan stopped at page {page_no} after retries.")
            save_listing_checkpoint(portal_numbers, max(page_no - 1, 1), False)
            break

        try:
            tenders = get_tender_list(driver)
        except Exception as error:
            print(f"Could not read tender list on page {page_no}: {error}")
            save_listing_checkpoint(portal_numbers, max(page_no - 1, 1), False)
            break

        total = len(tenders)
        print(
            f"Found {total} tenders on listing page {page_no} "
            f"(running total: {len(portal_numbers) + total})"
        )

        if total == 0:
            scan_completed = True
            print("Reached end of portal listing.")
            clear_listing_checkpoint()
            break

        for tender in tenders:
            portal_numbers.add(str(tender["number"]).strip())

        save_listing_checkpoint(portal_numbers, page_no, False)
        page_no += 1

    if scan_completed:
        clear_listing_checkpoint()
    elif portal_numbers:
        save_listing_checkpoint(portal_numbers, max(page_no - 1, start_page), False)

    return portal_numbers, scan_completed


def scrape_new_tenders_on_page(driver, wait, page_no, existing_tenders):
    """Open detail pages only for tenders missing from the database."""
    new_count = 0
    skipped_count = 0

    tenders = get_tender_list(driver)
    total = len(tenders)
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

            if not return_to_same_page(driver, page_no):
                if not recover_to_page(driver, page_no):
                    print("Could not recover while scraping details.")
                    break

            index += 1

        except Exception as error:
            print(f"Error while scraping tender at index {index + 1}: {error}")
            if not recover_to_page(driver, page_no):
                print("Could not recover while scraping details.")
                break
            continue

    return new_count, skipped_count


def run_scraper(start_page=1, headless=False, full_scan=True, resume=True):
    """
    Scrape tenders from the CG e-procurement portal.

    Phase 1 collects every tender number from listing pages (fast).
    Phase 2 opens detail pages only for tenders missing from the database.
    Nothing is deleted from the database.
    """
    db.init_db()
    existing_tenders = db.get_existing_tender_numbers()

    print(f"Already saved tenders: {len(existing_tenders)}")

    driver = create_driver(headless=headless)
    wait = WebDriverWait(driver, 45)

    new_count = 0
    skipped_count = 0
    portal_numbers = set()
    scan_completed = False
    run_error = None

    try:
        if not open_url(driver, URL):
            print("Could not open portal")
            return {
                "new": 0,
                "skipped": 0,
                "portal_total": 0,
                "scan_completed": False,
                "missing_after_scan": 0,
                "error": "portal timeout",
            }

        time.sleep(3)

        if not authenticate(driver):
            print("Login/authentication failed")
            return {
                "new": 0,
                "skipped": 0,
                "portal_total": 0,
                "scan_completed": False,
                "missing_after_scan": 0,
                "error": "authentication failed",
            }

        wait_for_listing(driver)

        print("\n========== PHASE 1: LISTING SCAN ==========")
        try:
            portal_numbers, scan_completed = collect_portal_listings(
                driver,
                start_page=start_page,
                resume=resume,
            )
        except Exception as error:
            print(f"Listing scan error: {error}")
            run_error = str(error)
            checkpoint_numbers, _, checkpoint_done = load_listing_checkpoint()
            portal_numbers = checkpoint_numbers or portal_numbers
            scan_completed = checkpoint_done

        missing_on_portal = portal_numbers - existing_tenders
        print(f"Portal listing total: {len(portal_numbers)}")
        print(f"Missing from database: {len(missing_on_portal)}")

        if full_scan and missing_on_portal and portal_numbers:
            print("\n========== PHASE 2: DETAIL SCRAPE ==========")
            page_no = 1

            while page_no <= MAX_PAGES:
                print(f"\n========== DETAIL PAGE {page_no} ==========")

                if not open_listing_page(driver, page_no):
                    print(f"Detail scrape stopped at page {page_no}.")
                    break

                try:
                    tenders = get_tender_list(driver)
                except Exception as error:
                    print(f"Could not read tender list on detail page {page_no}: {error}")
                    break

                if not tenders:
                    break

                page_new, page_skipped = scrape_new_tenders_on_page(
                    driver,
                    wait,
                    page_no,
                    existing_tenders,
                )
                new_count += page_new
                skipped_count += page_skipped

                if not (portal_numbers - existing_tenders):
                    print("All portal tenders are now saved.")
                    break

                page_no += 1
        elif not full_scan:
            print("Single-page mode: skipping detail scan for other pages.")
        elif not portal_numbers:
            print("No portal listings collected.")
        elif not missing_on_portal:
            print("Database already has every tender from the listing scan.")

    except Exception as error:
        print(f"Scraper error: {error}")
        run_error = str(error)
        checkpoint_numbers, _, checkpoint_done = load_listing_checkpoint()
        if checkpoint_numbers:
            portal_numbers = checkpoint_numbers
            scan_completed = checkpoint_done
    finally:
        driver.quit()

    saved_count = len(db.get_existing_tender_numbers())
    still_missing = len(portal_numbers - db.get_existing_tender_numbers()) if portal_numbers else 0

    print("Keeping all saved tenders. Open/closed tabs use bid due date only.")

    summary = {
        "new": new_count,
        "skipped": skipped_count,
        "portal_total": len(portal_numbers),
        "scan_completed": scan_completed,
        "missing_after_scan": still_missing,
        "error": run_error,
    }
    print("\n========== FINAL SUMMARY ==========")
    print(f"Portal listing total: {summary['portal_total']}")
    print(f"Listing scan completed: {scan_completed}")
    print(f"Saved in database: {saved_count}")
    print(f"New tenders scraped: {new_count}")
    print(f"Skipped existing tenders: {skipped_count}")
    print(f"Still missing from portal listing: {still_missing}")
    if run_error:
        print(f"Run finished with errors: {run_error}")
    return summary
