import sys
import time
import logging
import traceback
from playwright.sync_api import sync_playwright, TimeoutError
import os
from dotenv import load_dotenv
import argparse
import random
import re

load_dotenv()

# ------------------------------------------------------------------------------
# CONFIGURATION - Customize these for your environment
# ------------------------------------------------------------------------------
# Parse command-line arguments
parser = argparse.ArgumentParser(description="Book a Mindbody class.")
parser.add_argument("--name", required=True, help="Name of the desired class.")
parser.add_argument("--day", required=True, help="Day of the desired class (e.g., 'April 16, 2025').")
parser.add_argument("--time", required=True, help="Time of the desired class (e.g., '6:15 pm EDT').")
parser.add_argument("--id", required=True, help="Mindbody Gym ID")
parser.add_argument(
    "--headless",
    action="store_true",
    help="Run the browser in headless mode (default: headed if not provided)."
)
parser.add_argument(
    "--proxy",
    action="store_true",
    help="Run the browser with proxy (default: Proxyless)"
)

args = parser.parse_args()

GYM_ID = args.id
DESIRED_CLASS_NAME = args.name
DESIRED_CLASS_DAY = args.day
DESIRED_CLASS_TIME = args.time
HEADLESS = args.headless

if HEADLESS:
    DEV_TOOLS = False
else:  # Default to headed mode
    DEV_TOOLS = True

GYM_LOGIN_URL = f"https://clients.mindbodyonline.com/classic/ws?studioid={GYM_ID}"
GYM_SCHEDULE_URL = "https://clients.mindbodyonline.com/classic/mainclass?fl=true&tabID=7"
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
DESIRED_CALENDAR_DATE = time.strftime("%m/%d/%Y", time.strptime(DESIRED_CLASS_DAY, "%B %d, %Y"))

# Optional proxy - if you want to rotate or hide your IP
USE_PROXY = args.proxy

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def book_mindbody_class():
    """
    Logs into Mindbody Online, navigates to schedule, and attempts to book a specified class.
    """

    logging.info("Starting Playwright script...")

    # Wrapper for Playwright usage
    try:
        with sync_playwright() as p:
            browser_type = p.chromium  # or p.firefox, p.webkit
            
            if USE_PROXY:
                browser = browser_type.launch(
                    headless=HEADLESS,
                    devtools=DEV_TOOLS,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)…",
                    viewport={"width":1280,"height":720},
                    locale="en-US",
                    timezone_id="America/New_York",
                )
                page = context.new_page()
                
                # stealth init
                page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                """)
            else:
                browser = browser_type.launch(
                    headless=HEADLESS, 
                    devtools=DEV_TOOLS
                )

                page = browser.new_page()

            # 1. Navigate to the login page
            logging.info("Navigating to login page...")
            page.goto(GYM_LOGIN_URL, timeout=10000)  # 30-second timeout
            time.sleep(random.uniform(1,2))

            # 2. Fill in username and password
            logging.info("Filling in login form...")
            # Adjust selectors to match your gym's site
            page.locator("input#su1UserName").fill(USERNAME)
            page.locator("input#su1Password").fill(PASSWORD)
            # 3. Submit the login form
            page.locator("input[name=\"btnSignUp2\"]").click()  # Adjust if different
            page.wait_for_load_state("networkidle")  # Wait for page load

            # Check if an error is displayed
            try:
                page.locator("div#LoginError").wait_for(timeout=2000)
                error_message = page.locator("#LoginError").text_content()
                logging.info(f"Login failed: {error_message}")
                browser.close()
                sys.exit(1)
            except TimeoutError:
                logging.info("No login error found. Continuing...")

            # 4. Wait for navigation or some post-login element
            try:
                page.get_by_role("heading", name="Profile").wait_for(timeout=15000)  # Adjust to a known post-login element
                logging.info("Login successful!")
            except TimeoutError:
                logging.error("Login did not succeed within the expected time.")
                browser.close()
                sys.exit(1)

            # 5. Navigate to the class schedule page
            # Calculate the time to wait until 1 week and 15 minutes before the class time
            os.environ.setdefault("TZ", "America/New_York")
            time.tzset()
            raw = f"{DESIRED_CLASS_DAY} {DESIRED_CLASS_TIME}"

            # 2) uppercase the am/pm designator (but leave "EDT" alone)
            raw = re.sub(r'\b(am|pm)\b', lambda m: m.group().upper(), raw)

            # now raw == "April 25, 2025 6:15 PM EDT"
            class_time_struct = time.strptime(raw, "%B %d, %Y %I:%M %p %Z")
            class_time_epoch = time.mktime(class_time_struct)
            wait_until_epoch = class_time_epoch - (7 * 24 * 60 * 60) - (15 * 60)  # Subtract 1 week and 15 minutes

            current_time_epoch = time.time()
            if current_time_epoch < wait_until_epoch:
                wait_time = wait_until_epoch - current_time_epoch
                logging.info(f"Waiting for {wait_time / 60:.2f} minutes until 1 week and 15 minutes before the class time...")
                
                while current_time_epoch < wait_until_epoch:
                    remaining_time = wait_until_epoch - current_time_epoch
                    if remaining_time > 3600:  # More than an hour remaining
                        logging.info(f"Time remaining: {remaining_time / 3600:.2f} hours. Sleeping for 1 hour...")
                        time.sleep(3600)  # Sleep for 1 hour
                    else:
                        logging.info(f"Time remaining: {remaining_time / 60:.2f} minutes. Sleeping until the target time...")
                        time.sleep(remaining_time)  # Sleep for the remaining time
                        break
                    current_time_epoch = time.time()

            # Retry logic for navigating and finding the desired class
            max_retries = 5
            retry_delay = 4  # seconds

            for attempt in range(max_retries):
                try:
                    logging.info("Navigating to schedule page...")
                    page.goto(GYM_SCHEDULE_URL, timeout=10000)
                    # 6. Filter or search for the desired class
                    logging.info("Looking for the desired class...")

                    # Wait for schedule to load
                    page.get_by_role("heading", name="Class Schedule").wait_for(timeout=1000)

                    # If there's a date/day picker, you might need to select the correct day
                    page.locator("#txtDate").press("ControlOrMeta+a")
                    page.locator("#txtDate").fill(DESIRED_CALENDAR_DATE)
                    page.locator("#txtDate").press("Enter")

                    page.get_by_role("heading", name="Class Schedule").wait_for(timeout=1000)

                    # Find the class row with the correct name/time
                    rows_xpath = (
                        f"//div[contains(@class, 'row') and "
                        f"not(preceding-sibling::div[contains(@class, 'header')][1]"
                        f"[not(contains(., '{DESIRED_CLASS_DAY}'))])]"
                    )

                    # Locate the class rows for the day
                    class_rows = page.locator(f"xpath={rows_xpath}")

                    # Narrow down to the specific class row
                    specific_class_row = class_rows.filter(
                        has=page.locator("a.modalClassDesc", has_text=DESIRED_CLASS_NAME)
                    ).filter(
                        has=page.locator("div.col.col-first", has_text=DESIRED_CLASS_TIME)
                    )

                    logging.info(f"Row locator: {specific_class_row}")
                    specific_class_row.wait_for(timeout=1000)

                    # Once found, click the "Book" or "Sign Up" button in that row
                    specific_class_row.locator("input.SignupButton").click()
                    break  # Exit the retry loop if successful

                except (TimeoutError, Exception) as e:
                    logging.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        logging.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logging.error("Max retries reached. Unable to find or book the class.")
                        browser.close()
                        sys.exit(1)
            # 7. Confirm booking
            # If there's a final confirmation step
            try:
                page.get_by_role("heading", name="Make a Reservation").wait_for(timeout=5000)
                page.get_by_role("button", name="Make a single reservation").click()
            except TimeoutError:
                logging.warning("No extra confirmation required or not found. Proceeding...")

            # 8. Validate that booking succeeded
            # Wait for or check for a confirmation message
            try:
                page.locator("notifyBooking").wait_for(timeout=10000)
                logging.info("Class booking confirmed!")
            except TimeoutError:
                logging.error("Failed to confirm booking. Check if the button or flow changed.")
                # You might want to do extra debugging or screenshot capture here

            # Cleanup
            browser.close()
            logging.info("Booking flow completed.")
    except Exception as e:
        logging.error("An unexpected error occurred:")
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # Run the booking function
    book_mindbody_class()
