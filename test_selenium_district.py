from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_selenium():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Add user agent to avoid detection
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://www.district.in/movies/"
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait for content
        time.sleep(5)
        
        # Print title
        print(f"Title: {driver.title}")
        
        # Try to find movie links
        # They usually have /movies/ in href
        links = driver.find_elements(By.TAG_NAME, "a")
        movie_links = []
        for a in links:
            href = a.get_attribute('href')
            if href and '/movies/' in href:
                movie_links.append(href)
                
        print(f"Found {len(movie_links)} movie links.")
        print("Sample:", movie_links[:5])
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_selenium()
