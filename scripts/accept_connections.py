from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time
import logging
import pickle
import sys

def accept_connections():
    """Handle accepting connection requests"""
    # Configure Chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Chrome WebDriver initialized successfully")

        # Load cookies from file
        try:
            driver.get('https://www.linkedin.com')
            with open('linkedin_cookies.pkl', 'rb') as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            logging.info("Cookies loaded successfully")
        except Exception as e:
            logging.error(f"Error loading cookies: {str(e)}")
            return False

        # Navigate to Connection Requests Page
        driver.get('https://www.linkedin.com/mynetwork/invitation-manager/')
        logging.info("Navigating to invitation manager")
        time.sleep(5)

        connections_accepted = 0
        max_scrolls = 5
        scroll_count = 0

        while scroll_count < max_scrolls:
            connections_in_current_scroll = 0

            # Check for accept buttons
            accept_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept']")
            if not accept_buttons:
                accept_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'artdeco-button--secondary')]")
            if not accept_buttons:
                accept_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Accept')]")

            if not accept_buttons:
                logging.info("No connection requests found!")
                break

            # Process accept buttons
            for button in accept_buttons:
                try:
                    # Check if button still exists and is visible
                    if not button.is_displayed():
                        continue

                    # Scroll button into view
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                    time.sleep(1)

                    # Verify button is still clickable before clicking
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.ID, button.get_attribute("id")))
                        )
                    except:
                        continue

                    # Try to click and verify the button was actually clicked
                    initial_button_count = len(driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept']"))
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)

                    # Verify button count has decreased (meaning connection was accepted)
                    new_button_count = len(driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept']"))
                    if new_button_count < initial_button_count:
                        connections_accepted += 1
                        connections_in_current_scroll += 1
                        logging.info(f"Successfully accepted connection {connections_accepted}")

                    time.sleep(2)
                except Exception as e:
                    logging.error(f"Failed to process button: {str(e)}")
                    continue

            if connections_in_current_scroll == 0:
                logging.info("No new connections were accepted in this scroll.")
                break

            # Scroll to load more
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(3)
            scroll_count += 1

        logging.info(f"Script completed. Total connections actually accepted: {connections_accepted}")
        if connections_accepted == 0:
            logging.info("No connections were successfully accepted. All caught up!")

        return True

    finally:
        driver.quit()
        logging.info("Browser closed successfully")