from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, flash
import time
import logging
import pickle
import os
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = 'your-secret-key-here'  # Replace with a secure secret key

# Configure session for production
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Add error handling middleware
@app.before_request
def before_request():
    # Ensure cookies directory exists
    if not os.path.exists('cookies'):
        os.makedirs('cookies')

@app.after_request
def after_request(response):
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def init_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return webdriver.Chrome(options=chrome_options)

def wait_and_find_element(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        logger.error(f"Timeout waiting for element: {value}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Linkify is running'})

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/connections')
def connections():
    if 'username' not in session:
        flash('Please log in to manage your connections.', 'warning')
        return redirect(url_for('login'))
    return render_template('connections.html')

@app.route('/process-connections', methods=['POST'])
def process_connections():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Session expired. Please login again.'})
    
    try:
        driver = init_driver()
        cookie_path = os.path.join('cookies', f"linkedin_cookies_{session['username']}.pkl")
        
        if not os.path.exists(cookie_path):
            return jsonify({'success': False, 'message': 'No valid session found. Please login again.'})
        
        # Load cookies and process connections
        connections_accepted = accept_connections(driver, cookie_path)
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {connections_accepted} connection requests!'
        })
    except Exception as e:
        logger.error(f"Error processing connections: {str(e)}")
        return jsonify({'success': False, 'message': f'Error processing connections: {str(e)}'})
    finally:
        if 'driver' in locals():
            driver.quit()

def accept_connections(driver, cookie_path):
    """Handle accepting connection requests"""
    connections_accepted = 0
    try:
        # Load cookies
        driver.get('https://www.linkedin.com')
        with open(cookie_path, 'rb') as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        
        # Navigate to Connection Requests Page
        driver.get('https://www.linkedin.com/mynetwork/invitation-manager/')
        time.sleep(5)

        max_scrolls = 5
        scroll_count = 0

        while scroll_count < max_scrolls:
            connections_in_current_scroll = 0

            # Find accept buttons
            accept_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept']")
            if not accept_buttons:
                accept_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'artdeco-button--secondary')]")
            if not accept_buttons:
                accept_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Accept')]")

            if not accept_buttons:
                break

            # Process each button
            for button in accept_buttons:
                try:
                    if not button.is_displayed():
                        continue

                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                    time.sleep(1)

                    initial_button_count = len(driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept']"))
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)

                    new_button_count = len(driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Accept']"))
                    if new_button_count < initial_button_count:
                        connections_accepted += 1
                        connections_in_current_scroll += 1

                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Failed to process button: {str(e)}")
                    continue

            if connections_in_current_scroll == 0:
                break

            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(3)
            scroll_count += 1

        return connections_accepted

    except Exception as e:
        logger.error(f"Error in accept_connections: {str(e)}")
        raise

@app.route('/submit-password', methods=['POST'])
def submit_password():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'})
    
    driver = init_driver()
    try:
        driver.get('https://www.linkedin.com/login')
        
        username_field = wait_and_find_element(driver, By.ID, 'username')
        if not username_field:
            return jsonify({'success': False, 'message': 'Could not find username field'})
        username_field.send_keys(username)

        password_field = wait_and_find_element(driver, By.ID, 'password')
        if not password_field:
            return jsonify({'success': False, 'message': 'Could not find password field'})
        password_field.send_keys(password)

        sign_in_button = wait_and_find_element(driver, By.CSS_SELECTOR, 'button[type="submit"]')
        if not sign_in_button:
            return jsonify({'success': False, 'message': 'Could not find sign in button'})
        sign_in_button.click()

        time.sleep(3)

        # Check for login error (invalid credentials)
        error_element = None
        try:
            error_element = driver.find_element(By.CSS_SELECTOR, '.alert.error, .form__error, .alert-content, .form__label--error')
        except Exception:
            pass
        if error_element and error_element.is_displayed():
            return jsonify({'success': False, 'message': error_element.text or 'Invalid username or password.'})
        # Also check for URL not changing from login page
        if 'login' in driver.current_url:
            return jsonify({'success': False, 'message': 'Invalid username or password.'})

        session['username'] = username
        session['password'] = password
        session['cookies'] = driver.get_cookies()
        
        otp_field = wait_and_find_element(driver, By.CSS_SELECTOR, 'input[name="pin"]')
        if otp_field:
            return jsonify({'success': True, 'redirect': '/otp'})

        # If no OTP field, save cookies and proceed
        cookie_dir = 'cookies'
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
        
        cookie_path = os.path.join(cookie_dir, f"linkedin_cookies_{username}.pkl")
        with open(cookie_path, 'wb') as file:
            pickle.dump(driver.get_cookies(), file)
        
        return jsonify({'success': True, 'redirect': '/connections'})

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': f'Login error: {str(e)}'})
    finally:
        driver.quit()

@app.route('/otp')
def otp_page():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('otp.html')

@app.route('/submit-otp', methods=['POST'])
def submit_otp():
    if 'username' not in session or 'password' not in session:
        return jsonify({'success': False, 'message': 'Session expired. Please login again.'})

    otp = request.form.get('otp')
    skip_otp = request.form.get('skip_otp')

    if not otp and not skip_otp:
        return jsonify({'success': False, 'message': 'OTP is required'})

    driver = init_driver()
    try:
        driver.get('https://www.linkedin.com/login')
        
        for cookie in session.get('cookies', []):
            driver.add_cookie(cookie)
        
        driver.get('https://www.linkedin.com')

        if not skip_otp:
            otp_field = wait_and_find_element(driver, By.CSS_SELECTOR, 'input[name="pin"]')
            if otp_field:
                otp_field.send_keys(otp)
                verify_button = wait_and_find_element(driver, By.CSS_SELECTOR, 'button[type="submit"]')
                if verify_button:
                    verify_button.click()
                    time.sleep(3)

        cookies = driver.get_cookies()
        cookie_dir = 'cookies'
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
            
        cookie_path = os.path.join(cookie_dir, f"linkedin_cookies_{session['username']}.pkl")
        with open(cookie_path, 'wb') as file:
            pickle.dump(cookies, file)
        
        return jsonify({'success': True, 'redirect': '/connections'})

    except Exception as e:
        logger.error(f"OTP verification error: {str(e)}")
        return jsonify({'success': False, 'message': f'OTP verification error: {str(e)}'})
    finally:
        driver.quit()

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/check-session')
def check_session():
    """Endpoint to check if user session is still valid"""
    if 'username' not in session:
        return jsonify({'valid': False})
        
    # Check if cookie file exists
    cookie_path = os.path.join('cookies', f"linkedin_cookies_{session['username']}.pkl")
    if not os.path.exists(cookie_path):
        return jsonify({'valid': False})
        
    return jsonify({'valid': True})

@app.route('/connection-stats')
def connection_stats():
    """Endpoint to get LinkedIn connection statistics"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
        
    try:
        cookie_path = os.path.join('cookies', f"linkedin_cookies_{session['username']}.pkl")
        if not os.path.exists(cookie_path):
            return jsonify({'success': False, 'message': 'No valid session found'})
            
        driver = init_driver()
        
        try:
            # Load cookies
            driver.get('https://www.linkedin.com')
            with open(cookie_path, 'rb') as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            
            # Navigate to My Network page to check pending invitations
            driver.get('https://www.linkedin.com/mynetwork/invitation-manager/')
            time.sleep(3)
            
            # Improved: Scroll until no new Accept buttons appear
            max_scrolls = 20
            last_count = -1
            pending_buttons = set()
            for _ in range(max_scrolls):
                # Use a robust selector for Accept buttons
                accept_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Accept') or contains(text(), 'Accept') or contains(@class, 'artdeco-button--secondary')]")
                # Use the parent invitation card's data-id or href as a unique key if possible
                for btn in accept_buttons:
                    try:
                        parent = btn.find_element(By.XPATH, './ancestor::li[contains(@data-id, "invitation")]')
                        unique_id = parent.get_attribute('data-id')
                        if unique_id:
                            pending_buttons.add(unique_id)
                        else:
                            pending_buttons.add(btn)
                    except Exception:
                        pending_buttons.add(btn)
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2.5)
                # Wait for new elements to load
                if len(pending_buttons) == last_count:
                    break
                last_count = len(pending_buttons)
            pending_count = len(pending_buttons)
            
            # Get total connections count (approximate)
            driver.get('https://www.linkedin.com/mynetwork/')
            time.sleep(2)
            
            total_connections = 0
            try:
                connections_element = driver.find_element(By.XPATH, "//a[contains(@href, '/mynetwork/connections/')]")
                connections_text = connections_element.text
                import re
                match = re.search(r'(\d+)', connections_text)
                if match:
                    total_connections = int(match.group(1))
            except:
                logger.info("Could not find total connections count")
                total_connections = 500
            
            # Return the statistics
            return jsonify({
                'success': True,
                'pending': pending_count,
                'total': total_connections,
                'history': [
                    {"date": "1 week ago", "pending": 0, "accepted": 0},
                    {"date": "6 days ago", "pending": 0, "accepted": 0},
                    {"date": "5 days ago", "pending": 0, "accepted": 0},
                    {"date": "4 days ago", "pending": 0, "accepted": 0},
                    {"date": "3 days ago", "pending": 0, "accepted": 0},
                    {"date": "2 days ago", "pending": 0, "accepted": 0},
                    {"date": "Yesterday", "pending": 0, "accepted": 0},
                    {"date": "Today", "pending": pending_count, "accepted": 0}
                ]
            })
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error fetching connection stats: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Error fetching connection statistics', 
            'error': str(e)
        })

@app.route('/delete-local-data', methods=['POST'])
def delete_local_data():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401
    try:
        cookies_dir = 'cookies'
        deleted_files = 0
        errors = []
        if os.path.exists(cookies_dir):
            for filename in os.listdir(cookies_dir):
                if not filename.endswith('.pkl'):
                    continue
                file_path = os.path.join(cookies_dir, filename)
                try:
                    os.remove(file_path)
                    deleted_files += 1
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
                    continue
        if errors:
            logger.error(f"Delete errors: {errors}")
        session.clear()  # Log out the user after deleting cookies
        if deleted_files == 0 and not errors:
            return jsonify({'success': False, 'message': 'No local data files found to delete.'})
        if errors and deleted_files == 0:
            return jsonify({'success': False, 'message': f'Failed to delete files: {errors}'})
        return jsonify({'success': True, 'message': f'Deleted {deleted_files} local data files and logged out.'})
    except Exception as e:
        logger.error(f"Delete local data error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting local data: {str(e)}'}), 500

@app.errorhandler(404)
def page_not_found(e):
    # Don't redirect to index for API requests
    if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Endpoint not found'}), 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    # Don't return JSON for regular page requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Server error occurred. Please try again later.'}), 500
    return render_template('index.html'), 500

if __name__ == '__main__':
    try:
        if not os.path.exists('cookies'):
            os.makedirs('cookies')
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")