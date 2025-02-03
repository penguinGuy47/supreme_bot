import json
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import os
import tempfile

# Constants
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "./chromedriver.exe")
TEMP_DIR = tempfile.mkdtemp()
PROXY_FILE = "proxies.json"  # Path to the proxies.json file

# Get Instance ID from Command-Line Arguments
instance_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# Load Proxies from File
try:
    with open(PROXY_FILE, "r") as file:
        proxies = json.load(file)
except FileNotFoundError:
    raise Exception(f"Proxy file '{PROXY_FILE}' not found.")
except json.JSONDecodeError:
    raise Exception(f"Proxy file '{PROXY_FILE}' is not valid JSON.")

# Select Proxy Based on Instance ID
if instance_id >= len(proxies):
    raise Exception(f"Instance ID {instance_id} exceeds available proxies in '{PROXY_FILE}'.")
proxy = proxies[instance_id]

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
options.add_argument(f"--proxy-server=http://{proxy}")

# WebDriver Initialization
driver = webdriver.Chrome(options=options, service=Service(CHROMEDRIVER_PATH))

print(f"Using proxy: {proxy}")
