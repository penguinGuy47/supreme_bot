import os
import time
import tempfile
from queue import Queue
import random
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# --- Constants / Globals ---
TEMP_DIR = tempfile.mkdtemp()
results_queue = Queue()

# --- Browser / Context setup ---
def create_context(p):
    """
    Creates a Chromium persistent context so cookies/login can persist between runs.
    Adjust headless as needed. Configure user agent, viewport, etc. here.
    """
    context = p.chromium.launch_persistent_context(
        user_data_dir=TEMP_DIR,
        headless=False,
        args=[
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1920,1080",
        ],
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0.6668.71 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/Chicago",
        extra_http_headers={"DNT": "1", "Accept-Language": "en-US,en;q=0.9"},
    )
    return context

# --- CAPTCHA helpers (human-in-the-loop only) ---
def detect_captcha(page):
    """Example heuristic: look for a recaptcha iframe. Adapt for your own site."""
    try:
        iframe = page.frame_locator("iframe[src*='recaptcha']").first
        return iframe.is_visible(timeout=1000)
    except PWTimeout:
        return False
    except Exception:
        return False

def wait_for_captcha(page):
    print("CAPTCHA detected. Please solve it in the browser window, then press Enter...")
    input("Press Enter once you've solved the CAPTCHA.")
    # poll briefly to confirm it’s gone
    for _ in range(10):
        if not detect_captcha(page):
            break
        print("Still seeing CAPTCHA... waiting...")
        time.sleep(3)

def captcha_check(page):
    if detect_captcha(page):
        wait_for_captcha(page)

# --- State detection helpers ---
def is_queue_state(page):
    try:
        content_lower = page.inner_text("body").lower()
        queue_indicators = ["queue", "waiting room", "high traffic", "please wait"]
        return any(indicator in content_lower for indicator in queue_indicators)
    except Exception:
        return False

def is_item_visible(page, keywords):
    try:
        image = page.locator(f"img[alt*='{keywords}']").first
        return image.is_visible(timeout=3000)
    except PWTimeout:
        return False
    except Exception:
        return False

# --- Monitoring for drop ---
def wait_for_drop(page, keywords):
    """
    Monitors the page for the three states:
    - QUEUE: Wait gently without spamming reloads.
    - PRE-DROP: Refresh with jitter.
    - LIVE: Item visible, proceed.
    """
    while True:
        try:
            # Initial load or reload
            page.reload(wait_until="networkidle", timeout=30000)
            captcha_check(page)

            if is_queue_state(page):
                print("QUEUE state detected. Waiting gently...")
                queue_start = time.time()
                while is_queue_state(page):
                    if time.time() - queue_start > 300:  # 5 min stuck timeout
                        print("Stuck in queue too long, forcing reload...")
                        break
                    time.sleep(random.uniform(5, 10))  # Check every 5-10s without reload
                continue  # After exiting queue loop, reload to confirm state

            if is_item_visible(page, keywords):
                print("LIVE state detected. Item visible!")
                return True

            else:
                print("PRE-DROP state. Refreshing with jitter...")
                time.sleep(random.uniform(5, 15))

        except PWTimeout:
            print("Timeout during monitoring, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"Error during monitoring: {e}")
            time.sleep(10)

# --- Core actions (use on sites you own or have permission to test) ---
def add_item_to_cart(page, keywords: str, size: str) -> bool:
    """
    Example logic: find a product card by alt text or title containing keywords,
    open it, select a size (if any), and click Add to Cart.
    Replace selectors with your site’s selectors.
    """
    try:
        # Ensure initial load
        page.wait_for_load_state("networkidle", timeout=30000)

        # Search for an image by partial alt text match
        # (Prefer data-testid or stable attributes on your site)
        deadline = time.time() + 300  # Extended to 5 min for resilience
        found = False

        while time.time() < deadline:
            if is_queue_state(page):
                print("QUEUE detected during ATC. Waiting...")
                queue_start = time.time()
                while is_queue_state(page):
                    if time.time() - queue_start > 300:
                        print("Stuck in queue during ATC, reloading...")
                        break
                    time.sleep(random.uniform(5, 10))
                page.reload(wait_until="networkidle", timeout=30000)
                continue

            try:
                image = page.locator(f"img[alt*='{keywords}']").first
                if image.is_visible():
                    image.click()
                    print(f"Item '{keywords}' selected.")
                    found = True
                    break
            except PWTimeout:
                pass
            except Exception:
                pass

            print(f"Item '{keywords}' not found. Refreshing with jitter...")
            time.sleep(random.uniform(5, 15))
            page.reload(wait_until="networkidle")

        if not found:
            print(f"Error: Could not find '{keywords}' after timeout. Skipping item.")
            return False

        # Optional size selection (example using a <select>)
        if size and size.lower() not in ("one size", "onesize"):
            try:
                # Wait for a select to appear; replace with your site’s selector
                size_select = page.get_by_test_id('size-dropdown')
                size_select.wait_for(state="visible", timeout=5000)
                size_select.click()
                size_select.select_option(label=size)
                print(f"Size '{size}' selected for '{keywords}'.")
            except PWTimeout:
                print(f"Size select not available for '{keywords}'. Skipping size selection.")
            except Exception:
                # Optionally enumerate options:
                try:
                    opts = size_select.locator("option").all_inner_texts()
                    print(f"Could not match size '{size}'. Available: {opts}")
                except Exception:
                    pass
                return False
        else:
            print(f"No size selection needed for '{keywords}'.")

        # Click Add to Cart (replace with a stable selector from your site)
        atc_btn = page.locator(
            "[data-testid='add-to-cart-button'], button:has-text('Add to cart'), button:has-text('Add to Cart')"
        ).first
        atc_btn.wait_for(state="visible", timeout=10000)

        def is_atc_response(resp):
            # Fast server-ack: proceed when the ATC request gets a 2xx response
            return (
                resp.request.method in ("POST", "PUT")
                and any(p in resp.url for p in ("/cart", "/api/cart", "add_to_cart"))
                and 200 <= resp.status < 300
            )

        # Click and block until the server *acknowledges* the add-to-cart
        with page.expect_response(is_atc_response, timeout=15000):
            atc_btn.click()
        print(f"Clicked 'Add to Cart' for '{keywords}' (server acknowledged).")
        # Wait for evidence of success (e.g., cart badge updates or change of button)
        page.wait_for_selector("[data-testid='remove-from-cart-button'], .cart-count, .mini-cart", timeout=10000)
        print(f"Item '{keywords}' successfully added to cart.")
        return True

    except Exception as e:
        print(f"Could not add '{keywords}' to cart: {e}")
        return False

def click_checkout(page):
    """Navigate to checkout. Replace selector/URL with your permitted site’s flow."""
    try:
        # Example: a header/cart link
        checkout = page.locator("a[aria-label*='Checkout'], a:has-text('Checkout')")
        checkout.first.click()
        print("Checkout initiated.")
    except Exception as e:
        print(f"Error clicking checkout button: {e}")

from playwright.sync_api import Page

def fill_info(page: Page):
    """
    Fill checkout info using element IDs and per-field card iframes.
    Use ONLY in your own sandbox/test environment.
    """
    try:
        # --- Personal info (top-level doc) ---
        fields = {
            "email": "#email",
            "first_name": "#TextField0",
            "last_name": "#TextField1",
            "address": "#shipping-address1",
            "city": "#TextField3",
            "state": "#Select1",        # <select>
            "zip_code": "#TextField4",
            "phone": "#TextField5",
        }
        data = {
            "email": "exampleEmail@gmail.com",
            "first_name": "John",
            "last_name": "Doe",
            "address": "123 Test Ln",
            "city": "Testing Meadows",
            "state": "Illinois",        # label in the select
            "zip_code": "60007",
            "phone": "1234567890",
        }

        for key, sel in fields.items():
            loc = page.locator(sel).first
            # Wait for it to be attached & visible
            loc.wait_for(state="visible", timeout=15000)
            loc.scroll_into_view_if_needed()
            if key == "state":
                # select dropdown by label (or use value="IL" if that's what the DOM has)
                loc.select_option(label=data[key])
            else:
                # Some masked inputs ignore .fill(); typing is more reliable
                loc.click()
                loc.press_sequentially(str(data[key]), delay=20)
        print("Personal information filled.")

        # --- Payment info (each field inside its own iframe) ---
        # Matches <iframe id="card-fields-number-XXXX">, etc.
        card_iframes = {
            "card_number": ("number", "4111111111111111"),
            "expiry": ("expiry", "1234"),               # MMYY
            "verification_value": ("verification_value", "000"),
            "name": ("name", "John Doe"),
        }

        for logical, (field_id, value) in card_iframes.items():
            frame = page.frame_locator(f"iframe[id^='card-fields-{field_id}-']").first
            # Wait for the iframe to be present and the inner input ready
            input_box = frame.locator(f"#{field_id}").first
            input_box.wait_for(state="visible", timeout=15000)
            input_box.scroll_into_view_if_needed()
            input_box.click()

            if field_id == "expiry":
                # Type MM then YY like your Selenium code
                mm, yy = value[:2], value[2:]
                input_box.press_sequentially(mm, delay=40)
                input_box.press_sequentially(yy, delay=40)
            else:
                # Masked inputs prefer sequential typing over fill()
                input_box.press_sequentially(value, delay=20)

        print("Payment information filled (test data).")

    except Exception as e:
        print(f"Error filling checkout details: {e}")



def send_order(page):
    """Submit the order in a test environment you control."""
    try:
        pay_btn = page.locator("#checkout-pay-button, button:has-text('Pay')")
        pay_btn.first.click()
        print("Order submitted (test).")
    except Exception as e:
        print(f"Error submitting order: {e}")

# --- Orchestration ---
# Switch to headless mode for production
def buy(items):
    """
    items: list[tuple[str, str]] like [("Keyword A", "Large"), ("Keyword B", "One Size")]
    """
    with sync_playwright() as p:
        context = create_context(p)
        page = context.new_page()

        try:
            page.goto("https://us.supreme.com/collections/new", wait_until="domcontentloaded")
            captcha_check(page)

            # Monitor for the drop using the first item's keywords
            if items:
                wait_for_drop(page, items[0][0])

            for idx, (keywords, size) in enumerate(items):
                success = add_item_to_cart(page, keywords, size)
                results_queue.put((keywords, success))
                captcha_check(page)

                if idx < len(items) - 1:
                    page.goto("https://us.supreme.com/collections/new", wait_until="domcontentloaded")
                    captcha_check(page)

            failed_items = []
            while not results_queue.empty():
                item, success = results_queue.get()
                if not success:
                    failed_items.append(item)

            if failed_items:
                print(f"Failed to add items to cart: {failed_items}")
                return

            click_checkout(page)
            captcha_check(page)
            fill_info(page)
            send_order(page)
            time.sleep(9999)
            page.wait_for_timeout(2000)

        finally:
            context.close()
