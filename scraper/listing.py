from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_tender_list(driver, silent=False):

    wait = WebDriverWait(driver, 20)

    if not silent:
        print("\nReading Tender List...")

    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href,'viewRfq')]")
        )
    )

    tender_elements = driver.find_elements(
        By.XPATH,
        "//a[contains(@href,'viewRfq')]"
    )

    tenders = []

    for tender in tender_elements:
        number = tender.text.strip()

        if number:
            tenders.append({
                "number": number
            })

    if not silent:
        print(f"Found {len(tenders)} tenders\n")

        for i, tender in enumerate(tenders, start=1):
            print(f"{i}. {tender['number']}")

    return tenders