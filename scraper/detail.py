from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FIELDS_REQUIRED = {
    "TENDER NO.": "tender_no",
    "Detailed Description": "name",
    "OFFICE/DIVISION(PWD) NAME": "department",
    "Estimated Value": "amount",
    "Bid Due Date": "last_date",
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
        "last_date": ""
    }

    labels = driver.find_elements(By.CLASS_NAME, "fieldLabel")

    for label in labels:
        key = label.text.strip().replace("\n", " ")

        if key in FIELDS_REQUIRED:
            try:
                value = label.find_element(
                    By.XPATH,
                    "./following-sibling::*[contains(@class,'field')][1]"
                )

                data[FIELDS_REQUIRED[key]] = value.text.strip().replace("\n", " ")

            except:
                pass

    return data