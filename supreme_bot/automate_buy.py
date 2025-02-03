import os
import random
import time
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Constants
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "./chromedriver.exe")
TEMP_DIR = tempfile.mkdtemp()

# Chrome Options Setup
options = webdriver.ChromeOptions()
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
options.add_argument("--disable-browser-side-navigation")
options.add_argument("--disable-cookies")
options.add_argument("--disable-site-isolation-trials")
options.add_argument("--disable-web-security")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.71 Safari/537.36")
options.add_argument(f"user-data-dir={TEMP_DIR}")

# WebDriver Initialization
driver = webdriver.Chrome(options=options, service=Service(CHROMEDRIVER_PATH))


# Helper Functions
def detect_captcha():
    """Detects if a CAPTCHA is present on the page."""
    try:
        driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
        return True
    except NoSuchElementException:
        return False


def wait_for_captcha():
    """Waits for the user to solve the CAPTCHA."""
    print("CAPTCHA detected. Please solve it, then press Enter to continue...")
    input("Press Enter once you've solved the CAPTCHA.")
    while detect_captcha():
        print("Waiting for CAPTCHA to be solved...")
        time.sleep(3)


def captcha_check():
    """Checks and handles CAPTCHA if detected."""
    if detect_captcha():
        wait_for_captcha()


def add_item_to_cart(keywords, size):
    """
    Handles the process of finding an item, optionally selecting its size, 
    adding it to the cart, and waiting for confirmation before returning.
    """
    try:
        # Wait for the page to fully load
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        image = WebDriverWait(driver, 300).until(
            EC.element_to_be_clickable((By.XPATH, f"//img[@alt='{keywords}']"))
        )
        image.click()
        print(f"Item '{keywords}' selected.")

        # Check if size selection is required
        if size != "One Size":
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="MainContent"]/div[2]/div/div[2]/section/div[1]/div/select'))
                )
                size_selector = driver.find_element(By.XPATH, '//*[@id="MainContent"]/div[2]/div/div[2]/section/div[1]/div/select')
                size_selector.click()
                time.sleep(0.5)
                Select(size_selector).select_by_visible_text(size)
                print(f"Size '{size}' selected for '{keywords}'.")
            except Exception:
                print(f"Size selection not available for '{keywords}'. Skipping size selection.")
        else:
            print(f"No size selection needed for '{keywords}'.")

        # Add to cart
        atc_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="add-to-cart-button"]'))
        )
        atc_button.click()
        print(f"Clicked 'Add to Cart' button for '{keywords}'.")

        # Wait until the button changes to "remove-from-cart-button"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//button[@data-testid="remove-from-cart-button"]'))
        )
        print(f"Item '{keywords}' successfully added to cart.")
    except Exception as e:
        print(f"Could not add '{keywords}' to cart")


def click_checkout():
    """Clicks the checkout button."""
    try:
        checkout_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Supreme Checkout']"))
        )
        checkout_btn.click()
        print("Checkout initiated.")
    except Exception as e:
        print(f"Error clicking checkout button: {e}")


def fill_info():
    """Fills in the checkout information, including payment details."""
    try:
        # Personal Information
        fields = {
            "email": '//*[@id="email"]',
            "first_name": '//*[@id="TextField0"]',
            "last_name": '//*[@id="TextField1"]',
            "address": '//*[@id="shipping-address1"]',
            "city": '//*[@id="TextField3"]',
            "state": '//*[@id="Select1"]',
            "zip_code": '//*[@id="TextField4"]',
            "phone": '//*[@id="TextField5"]'
        }
        data = {
            "email": "exampleEmail@gmail.com",
            "first_name": "John",
            "last_name": "Doe",
            "address": "123 Test Ln",
            "city": "Testing Meadows",
            "state": "Illinois",
            "zip_code": "60007",
            "phone": "1234567890"
        }
        for field, xpath in fields.items():
            input_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            input_field.send_keys(data[field])
            # time.sleep(random.uniform(0.5, 1))  # Random pause to avoid detection

        # Payment Information
        iframe_info = {
            "card_number": "number",
            "expiry": "expiry",
            "verification_value": "verification_value",
            "name": "name"
        }
        input_data = {
            "card_number": "1234123412341234",
            "expiry": "1234",  # MMYY format
            "verification_value": "000",
            "name": "John Doe"
        }
        print("Sleeping...")
        time.sleep(1)
        for field, field_id in iframe_info.items():
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f'//iframe[starts-with(@id, "card-fields-{field_id}-")]'))
            )
            driver.switch_to.frame(iframe)

            input_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//*[@id="{field_id}"]'))
            )

            if field == "expiry":
                input_field.send_keys(input_data[field][:2])  # MM
                time.sleep(random.uniform(0.5, 1))
                input_field.send_keys(input_data[field][2:])  # YY
            else:
                input_field.send_keys(input_data[field])

            # time.sleep(random.uniform(0.5, 1))  # Random pause
            driver.switch_to.default_content()

        print("Checkout information entered.")
    except Exception as e:
        print(f"Error filling checkout details: {e}")


def send_order():
    """Clicks the pay button to finalize the order."""
    try:
        payment_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="checkout-pay-button"]'))
        )
        payment_btn.click()
        print("Order submitted successfully.")
    except Exception as e:
        print(f"Error submitting order: {e}")


def buy(items):
    """
    Handles the entire purchase process for multiple items, each with its own size.
    """
    driver.get("https://us.supreme.com/collections/all")
    captcha_check()

    for item in items:
        keywords, size = item  # Unpack keyword and size
        add_item_to_cart(keywords, size)
        captcha_check()

        # Return to the main collections page if there are more items
        if item != items[-1]:
            driver.get("https://us.supreme.com/collections/all")
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            captcha_check()

    # Proceed to checkout
    click_checkout()
    captcha_check()

    fill_info()
    send_order()

    time.sleep(1000)

