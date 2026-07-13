from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from scraper.location import extract_area_city


FIELDS_REQUIRED = {
    "TENDER NO.": "tender_no",
    "Detailed Description": "name",
    "OFFICE/DIVISION(PWD) NAME": "department",
    "Estimated Value": "amount",
    "Bid Due Date": "last_date",
}

AREA_CITY_LABELS = {
    "City": "area_city",
    "CITY": "area_city",
    "City Name": "area_city",
    "District": "area_city",
    "District Name": "area_city",
    "Place of Work": "area_city",
    "Location": "area_city",
    "Location of Work": "area_city",
    "Area": "area_city",
}


def scrape_tender_details(driver):
    wait = WebDriverWait(driver, 15)

    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'TENDER/NIT HEADER DETAIL')]")
        )
    )

    data = {
        "tender_no": "",
        "name": "",
        "department": "",
        "amount": "",
        "last_date": "",
        "area_city": "",
    }

    labels = driver.find_elements(By.CLASS_NAME, "fieldLabel")
    scraped_city = ""

    for label in labels:
        key = label.text.strip().replace("\n", " ")

        field_key = FIELDS_REQUIRED.get(key) or AREA_CITY_LABELS.get(key)
        if not field_key:
            continue

        try:
            value = label.find_element(
                By.XPATH,
                "./following-sibling::*[contains(@class,'field')][1]"
            )

            text_value = value.text.strip().replace("\n", " ")
            data[field_key] = text_value
            if field_key == "area_city":
                scraped_city = text_value

        except Exception:
            pass

    data["area_city"] = extract_area_city(
        name=data["name"],
        department=data["department"],
        scraped_city=scraped_city,
    )

    return data