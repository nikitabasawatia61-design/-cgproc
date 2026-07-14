import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://eproc.cgstate.gov.in/CHEPS/business/getOpenRfqListAction.do"


def authenticate(driver, attempt=1):

    MAX_ATTEMPTS = 10

    print(f"\n========== Authentication Attempt {attempt} ==========")

    if attempt > MAX_ATTEMPTS:
        print("Maximum authentication attempts reached.")
        return False

    wait = WebDriverWait(driver, 20)

    # ==========================================
    # Read Authentication Code
    # ==========================================
    print("Reading Authentication Code...")

    code = wait.until(
        EC.visibility_of_element_located(
            (By.TAG_NAME, "i")
        )
    ).text.strip()

    print("Authentication Code:", code)

    # ==========================================
    # Enter Authentication Code
    # ==========================================
    textbox = wait.until(
        EC.visibility_of_element_located(
            (By.NAME, "inputCaptchaValue")
        )
    )

    textbox.clear()
    textbox.send_keys(code)

    # ==========================================
    # Click Submit
    # ==========================================
    submit_btn = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input.epsSubmit")
        )
    )

    submit_btn.click()

    print("Submit Clicked")

    # Wait for page to respond
    time.sleep(3)

    # ==========================================
    # Did authentication fail?
    # ==========================================
    failure = driver.find_elements(
        By.XPATH,
        "//td[normalize-space()='Failure']"
    )

    if failure:

        print("Authentication Failed")

        # ======================================
        # Click Back
        # ======================================
        back_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href,'backTo')]")
            )
        )

        back_btn.click()

        print("Back Clicked")

        # Wait for page to reload
        time.sleep(5)

        # ======================================
        # Click Advanced Search
        # ======================================
        adv_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//input[@value='Advanced Search' and @onclick='submitRfqSearchForm();']"
                )
            )
        )

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            adv_btn
        )

        time.sleep(1)

        adv_btn.click()

        print("Advanced Search Clicked")

        # Wait for new authentication page
        time.sleep(3)

        # Retry with new authentication code
        return authenticate(driver, attempt + 1)

    # ==========================================
    # Success
    # ==========================================
    print("Authentication Successful")

    return True