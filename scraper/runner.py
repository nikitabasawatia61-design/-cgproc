import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium import webdriver
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
PAGE_RETRIES = 5
MAX_PAGES = 250


def page_sleep(page_no):
    if page_no <= 10:
        return 4
    return 6


def wait_for_listing(driver, page_no=1):
    timeout = 60 if page_no <= 10 else 90
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href,'viewRfq')]")
        )
    )


def try_submit_page(driver, page_no):
    sleep_seconds = page_sleep(page_no)
    try:
        driver.execute_script(f"submitPage({page_no});")
        time.sleep(sleep_seconds)
        wait_for_listing(driver, page_no)
        print(f"Ready on Page {page_no}")
        return True
    except Exception as error:
        print(f"submitPage({page_no}) failed: {error}")
        return False


def go_to_page(driver, page_no):
    """Jump to a page after recovery — may use stepped navigation."""
    print(f"Going to Page {page_no}")

    if page_no == 1:
        wait_for_listing(driver, page_no)
        print("Ready on Page 1")
        return True

    if try_submit_page(driver, page_no):
        return True

    print(f"Trying sequential navigation to page {page_no}...")
    try:
        wait_for_listing(driver, 1)
    except Exception:
        return False

    for step in range(2, page_no + 1):
        if not try_submit_page(driver, step):
            return False
    return True


def advance_to_next_page(driver, page_no):
    """Move forward one listing page. New tenders appear on page 1, 2, 3..."""
    if page_no == 1:
        wait_for_listing(driver, 1)
        print("Ready on Page 1")
        return True
    return try_submit_page(driver, page_no)


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

        if not go_to_page(driver, page_no):
            return False

        print(f"Recovered to Page {page_no}")
        return True
    except Exception as error:
        print(f"Recovery failed for page {page_no}: {error}")
        return False


def return_to_same_page(driver, page_no):
    """Return to the listing after opening a tender detail — stay on the same page."""
    print(f"Returning to listing on page {page_no}")

    try:
        driver.back()
        time.sleep(2)
        wait_for_listing(driver, page_no)
        print(f"Back on Page {page_no}")
        return True
    except Exception:
        print("Browser back did not restore listing.")

    if authenticate(driver):
        try:
            wait_for_listing(driver, 1)
            if page_no == 1:
                return True
            return try_submit_page(driver, page_no)
        except Exception:
            pass

    print("Using full recovery.")
    return recover_to_page(driver, page_no)


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


def scrape_listing_pages(driver, wait, existing_tenders, full_scan=False):
    """
    Walk listing pages forward from page 1 only.

    Daily mode (default): stop when a page has no new tenders — new ones
    are always on the first pages of the portal.

    Full scan: walk every page until the listing is empty.
    """
    portal_numbers = set()
    scan_completed = False
    new_count = 0
    skipped_count = 0
    page_no = 1

    mode_label = "FULL SCAN (all pages)" if full_scan else "DAILY (pages 1, 2, 3... until no new tenders)"
    print(f"Scan mode: {mode_label}")

    while page_no <= MAX_PAGES:
        print(f"\n========== PAGE {page_no} ==========")

        if page_no == 1:
            if not advance_to_next_page(driver, page_no):
                print("Could not load page 1.")
                break
        else:
            if not advance_to_next_page(driver, page_no):
                print(f"Could not go forward to page {page_no}.")
                if not recover_to_page(driver, page_no):
                    break

        try:
            tenders = get_tender_list(driver)
        except Exception as error:
            print(f"Could not read tender list on page {page_no}: {error}")
            break

        if not tenders:
            scan_completed = True
            print("Reached end of portal listing.")
            break

        for tender in tenders:
            portal_numbers.add(str(tender["number"]).strip())

        page_new, page_skipped = scrape_new_tenders_on_page(
            driver,
            wait,
            page_no,
            existing_tenders,
        )
        new_count += page_new
        skipped_count += page_skipped

        print(
            f"Page {page_no}: {page_new} new, {page_skipped} already saved, "
            f"{len(portal_numbers)} portal IDs collected so far"
        )

        if not full_scan and page_new == 0:
            print(
                "No new tenders on this page. "
                "Stopping here — new portal tenders appear on page 1, 2, 3..."
            )
            break

        page_no += 1

    return portal_numbers, scan_completed, new_count, skipped_count


def run_scraper(start_page=1, headless=False, full_scan=False):
    """
    Scrape tenders from the CG e-procurement portal.

    Default daily run: pages 1, 2, 3... forward until a page has no new tenders.
    Full scan (--full-scan): every listing page until empty.
    Nothing is ever deleted from the database.
    """
    db.init_db()
    existing_tenders = db.get_existing_tender_numbers()

    print(f"Already saved tenders: {len(existing_tenders)}")

    checkpoint_file = Path(__file__).resolve().parent.parent / ".scraper_listing_checkpoint.json"
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    driver = create_driver(headless=headless)
    wait = WebDriverWait(driver, 45)

    portal_numbers = set()
    scan_completed = False
    new_count = 0
    skipped_count = 0
    run_error = None

    try:
        if not open_url(driver, URL):
            print("Could not open portal")
            return _summary(0, 0, set(), False, "portal timeout")

        time.sleep(3)

        if not authenticate(driver):
            print("Login/authentication failed")
            return _summary(0, 0, set(), False, "authentication failed")

        portal_numbers, scan_completed, new_count, skipped_count = scrape_listing_pages(
            driver,
            wait,
            existing_tenders,
            full_scan=full_scan,
        )

    except Exception as error:
        print(f"Scraper error: {error}")
        run_error = str(error)
    finally:
        driver.quit()

    return _summary(
        new_count,
        skipped_count,
        portal_numbers,
        scan_completed,
        run_error,
    )


def _summary(new_count, skipped_count, portal_numbers, scan_completed, run_error):
    saved_count = len(db.get_existing_tender_numbers())
    still_missing = len(portal_numbers - db.get_existing_tender_numbers()) if portal_numbers else 0
    open_count = db.get_stats()["total"]

    print("\nKeeping all saved tenders. Open/closed tabs use bid due date only.")
    print("\n========== FINAL SUMMARY ==========")
    print(f"Open saved: {open_count}")
    print(f"On portal (this run): {len(portal_numbers)}")
    print(f"Still to fetch: {still_missing}")
    print(f"Listing scan completed: {scan_completed}")
    print(f"New tenders scraped this run: {new_count}")
    print(f"Skipped existing tenders: {skipped_count}")
    print(f"Total in database: {saved_count}")
    if run_error:
        print(f"Run finished with errors: {run_error}")
    elif still_missing and not scan_completed:
        print("Tip: run .\\run_scrape.ps1 -FullScan once to fetch older missing tenders.")
    print("Run .\\run_push.ps1 when ready to update the website.")

    return {
        "new": new_count,
        "skipped": skipped_count,
        "portal_total": len(portal_numbers),
        "scan_completed": scan_completed,
        "missing_after_scan": still_missing,
        "open_saved": open_count,
        "error": run_error,
    }
