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


def open_listing_page(driver, page_no):
    for attempt in range(1, PAGE_RETRIES + 1):
        if page_no == 1:
            if advance_to_next_page(driver, 1):
                return True
        elif go_to_page(driver, page_no):
            return True

        print(f"Retrying page {page_no} after recovery (attempt {attempt}/{PAGE_RETRIES})...")
        if recover_to_page(driver, page_no):
            return True
        time.sleep(10)

    return False


def collect_new_tender_ids(driver, existing_tenders, full_scan=False):
    """
    Phase 1 — ID scan only (no detail pages).

    Daily flow:
      Page 1 → read IDs top to bottom
      If an ID is not in DB, queue it as new
      If zero matches on the whole page → go to page 2 and repeat
      Stop at the first ID that already exists in DB
    """
    new_by_page = {}
    page_no = 1
    scan_completed = False
    total_new_ids = 0

    print(
        "\n========== PHASE 1: ID SCAN =========="
        "\nPage 1 → match IDs → if no match on page, page 2 → "
        "stop at first existing tender ID."
    )

    while page_no <= MAX_PAGES:
        print(f"\n========== ID SCAN PAGE {page_no} ==========")

        if page_no == 1:
            if not advance_to_next_page(driver, page_no):
                print("Could not load page 1.")
                break
        elif not advance_to_next_page(driver, page_no):
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

        page_new = []
        hit_existing = False

        for tender in tenders:
            tender_no = str(tender["number"]).strip()
            if not tender_no:
                continue

            if full_scan:
                if tender_no not in existing_tenders:
                    page_new.append(tender_no)
                continue

            if tender_no in existing_tenders:
                print(f"Found existing tender {tender_no} — stopping ID scan.")
                hit_existing = True
                break

            page_new.append(tender_no)

        if page_new:
            new_by_page[page_no] = page_new
            total_new_ids += len(page_new)
            print(f"Page {page_no}: {len(page_new)} new ID(s) queued")

        if full_scan:
            page_no += 1
            continue

        if hit_existing:
            break

        print(f"Page {page_no}: zero matches — all IDs are new. Moving to page {page_no + 1}.")
        page_no += 1

    print(f"\nID scan done. {total_new_ids} new tender ID(s) to fetch.")
    return new_by_page, scan_completed, total_new_ids


def scrape_tender_detail(driver, wait, page_no, tender_no, existing_tenders):
    print(f"\nFetching details: {tender_no} (page {page_no})")

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
    print(f"Saved tender: {tender_no}")

    if not return_to_same_page(driver, page_no):
        if not recover_to_page(driver, page_no):
            raise RuntimeError(f"Could not return to page {page_no} after saving {tender_no}")


def fetch_new_tender_details(driver, wait, new_by_page, existing_tenders):
    """Phase 2 — open detail pages only for queued new IDs."""
    new_count = 0

    if not new_by_page:
        print("\nNo new tender IDs to fetch.")
        return 0

    print("\n========== PHASE 2: FETCH DETAILS ==========")

    for page_no in sorted(new_by_page.keys()):
        print(f"\n========== DETAIL PAGE {page_no} ==========")

        if not open_listing_page(driver, page_no):
            print(f"Could not open page {page_no} for detail fetch.")
            break

        for tender_no in new_by_page[page_no]:
            try:
                scrape_tender_detail(driver, wait, page_no, tender_no, existing_tenders)
                new_count += 1
            except Exception as error:
                print(f"Error fetching {tender_no}: {error}")
                if not recover_to_page(driver, page_no):
                    print("Could not recover during detail fetch.")
                    return new_count

    return new_count


def run_scraper(headless=False, full_scan=False):
    """
    Daily flow:
      1. Scan listing IDs from page 1 forward until first existing tender ID
      2. Fetch details for all new IDs only
      3. Export everything — UI splits open vs closed by bid due date
    """
    db.init_db()
    existing_tenders = db.get_existing_tender_numbers()

    print(f"Already saved tenders: {len(existing_tenders)}")

    checkpoint_file = Path(__file__).resolve().parent.parent / ".scraper_listing_checkpoint.json"
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    driver = create_driver(headless=headless)
    wait = WebDriverWait(driver, 45)
    run_error = None
    new_by_page = {}
    scan_completed = False
    new_count = 0
    total_new_ids = 0

    try:
        if not open_url(driver, URL):
            print("Could not open portal")
            return _summary(0, 0, 0, False, "portal timeout")

        time.sleep(3)

        if not authenticate(driver):
            print("Login/authentication failed")
            return _summary(0, 0, 0, False, "authentication failed")

        new_by_page, scan_completed, total_new_ids = collect_new_tender_ids(
            driver,
            existing_tenders,
            full_scan=full_scan,
        )

        new_count = fetch_new_tender_details(
            driver,
            wait,
            new_by_page,
            existing_tenders,
        )

    except Exception as error:
        print(f"Scraper error: {error}")
        run_error = str(error)
    finally:
        driver.quit()

    still_missing = max(total_new_ids - new_count, 0)
    return _summary(new_count, total_new_ids, still_missing, scan_completed, run_error)


def _summary(new_count, queued_ids, still_missing, scan_completed, run_error):
    saved_count = len(db.get_existing_tender_numbers())
    open_count = db.get_stats()["total"]

    print("\nNothing deleted from database. Open/closed split is handled on the dashboard by bid due date.")
    print("\n========== FINAL SUMMARY ==========")
    print(f"New IDs found: {queued_ids}")
    print(f"Details saved this run: {new_count}")
    print(f"Still to fetch: {still_missing}")
    print(f"Open saved (DB): {open_count}")
    print(f"Total in database: {saved_count}")
    print(f"ID scan completed: {scan_completed}")
    if run_error:
        print(f"Run finished with errors: {run_error}")
    print("Run .\\run_push.ps1 to update the website.")

    return {
        "new": new_count,
        "skipped": max(queued_ids - new_count, 0),
        "portal_total": queued_ids,
        "scan_completed": scan_completed,
        "missing_after_scan": still_missing,
        "open_saved": open_count,
        "error": run_error,
    }
