import cloudscraper
import json
import os
import time
import re
import sqlite3
from bs4 import BeautifulSoup
from database import get_db_connection

# Configuration
DATA_DIR = 'data'
CITIES_FILE = os.path.join(DATA_DIR, 'cities.json')
METADATA_FILE = os.path.join(DATA_DIR, 'district_metadata.json')

import cloudscraper
import json
import os
import time
import re
import sqlite3
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from database import get_db_connection

# Configuration
DATA_DIR = 'data'
CITIES_FILE = os.path.join(DATA_DIR, 'cities.json')
METADATA_FILE = os.path.join(DATA_DIR, 'district_metadata.json')

scraper = cloudscraper.create_scraper()

def load_cities():
    if os.path.exists(CITIES_FILE):
        with open(CITIES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_to_db(city_name, movies_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"  Saving {len(movies_data)} movies to DB...")
    
    for movie in movies_data:
        # 1. Insert/Get Movie
        cursor.execute('''
            INSERT OR IGNORE INTO movies (title, slug, city, language, format)
            VALUES (?, ?, ?, ?, ?)
        ''', (movie['title'], movie['slug'], city_name, movie.get('language'), movie.get('format')))
        
        # Get ID
        cursor.execute('SELECT id FROM movies WHERE slug = ? AND city = ?', (movie['slug'], city_name))
        res = cursor.fetchone()
        if not res: continue
        movie_id = res[0]
        
        # 2. Process Showtimes
        for show in movie.get('showtimes', []):
            theatre_name = show['theatre']
            theatre_slug = re.sub(r'[^a-zA-Z0-9]', '', theatre_name.lower())
            
            # Insert/Get Theatre
            cursor.execute('''
                INSERT OR IGNORE INTO theatres (name, city, slug)
                VALUES (?, ?, ?)
            ''', (theatre_name, city_name, theatre_slug))
            
            cursor.execute('SELECT id FROM theatres WHERE name = ? AND city = ?', (theatre_name, city_name))
            t_res = cursor.fetchone()
            if not t_res: continue
            theatre_id = t_res[0]
            
            # Insert Showtime
            cursor.execute('''
                INSERT OR IGNORE INTO showtimes (movie_id, theatre_id, show_date, show_time, link)
                VALUES (?, ?, ?, ?, ?)
            ''', (movie_id, theatre_id, show['date'], show['time'], show.get('link')))
            
    conn.commit()
    conn.close()
    print(f"  Saved data for {city_name} to DB.")

def get_movie_urls_selenium(city_name):
    print(f"  Discovering movies for {city_name} via Selenium...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    movie_urls = set()
    
    try:
        driver.get("https://www.district.in/")
        time.sleep(3)
        
        # 1. Select City
        print("  Selecting city...")
        try:
            # Click Location Header
            # Try finding by aria-label (it might be the current city name)
            # Or just the button in the header.
            # We'll try a few strategies.
            
            # Strategy A: Button with aria-label containing a city name
            # We don't know the current city, so we look for the location icon or class.
            # But the subagent said it was a button with aria-label.
            
            # Let's try to find the input directly first (if modal is open? no).
            
            # Click the header button.
            # It's usually the second button in the header.
            # Let's try XPATH for the location pin icon or text.
            header_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'location') or .//svg]")
            # This is risky.
            
            # Better: Look for text that is a city name.
            # But we don't know which one.
            
            # Let's try to find the button that opens the modal.
            # It usually has an aria-label.
            buttons = driver.find_elements(By.TAG_NAME, "button")
            location_btn = None
            for btn in buttons:
                label = btn.get_attribute('aria-label')
                if label and label in ['Gurugram', 'Delhi', 'Mumbai', 'Chennai', 'Bengaluru', 'Hyderabad']:
                    location_btn = btn
                    break
            
            if not location_btn:
                # Fallback: Try to find by text
                location_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Location') or contains(text(), 'Gurugram')]")
                
            if location_btn:
                location_btn.click()
                time.sleep(1)
                
                # Type in input
                inputs = driver.find_elements(By.TAG_NAME, "input")
                if inputs:
                    print(f"  Typing {city_name}...")
                    inputs[0].send_keys(city_name)
                    time.sleep(1)
                    
                    # Click Result
                    # Look for div with aria-label=city_name
                    results = driver.find_elements(By.XPATH, f"//div[@aria-label='{city_name}']")
                    if results:
                        print("  Clicking result...")
                        results[0].click()
                        time.sleep(3)
                    else:
                        print("  City result not found in dropdown.")
            else:
                print("  Could not find location button.")
                
        except Exception as e:
            print(f"  City selection error: {e}")
            
        # 2. Go to Movies
        print("  Navigating to Movies tab...")
        try:
            # Click "Movies" link
            movies_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Movies')]")
            movies_link.click()
            time.sleep(3)
        except:
            # Fallback: Force URL
            driver.get("https://www.district.in/movies/")
            time.sleep(3)
        
        # 3. Extract Links
        print("  Extracting links...")
        # Scroll down to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            href = a.get_attribute('href')
            if href and '/movies/' in href and '-movie-tickets-in-' in href:
                # Filter for city if possible
                if city_name.lower() in href.lower():
                    movie_urls.add(href)
                    
    except Exception as e:
        print(f"  Selenium Error: {e}")
    finally:
        driver.quit()
        
    return list(movie_urls)

def fetch_movie_details(url, city_name):
    try:
        resp = scraper.get(url)
        if resp.status_code != 200: return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        next_data = soup.find('script', id='__NEXT_DATA__')
        
        if next_data:
            data = json.loads(next_data.string)
            props = data.get('props', {}).get('pageProps', {})
            
            # Extract Movie Info
            initial_state = props.get('initialState', {})
            
            title = soup.title.string.split('|')[0].strip() if soup.title else "Unknown"
            title = title.split(' Movie Tickets')[0].strip()
            
            slug = url.split('/')[-1]
            
            showtimes = []
            
            # Regex for showtimes
            times = re.findall(r'\d{1,2}:\d{2}\s(?:AM|PM)', resp.text)
            unique_times = sorted(list(set(times)))
            
            if unique_times:
                showtimes.append({
                    "theatre": "Unknown Theatre (Scraped)", 
                    "time": unique_times[0],
                    "date": "Today", 
                    "link": url
                })
            
            return {
                "title": title,
                "slug": slug,
                "showtimes": showtimes,
                "language": "Unknown",
                "format": "2D"
            }
            
    except Exception as e:
        print(f"  Error fetching details for {url}: {e}")
    return None

def export_metadata():
    print("Exporting metadata for frontend...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cities = load_cities()
    metadata = {}
    
    for city in cities:
        city_name = city['name']
        
        # Get Movies
        cursor.execute('SELECT * FROM movies WHERE city = ?', (city_name,))
        movies = []
        for row in cursor.fetchall():
            movies.append({
                "Title": row['title'],
                "EventCode": row['slug'], 
                "City": row['city'],
                "Language": row['language'],
                "Format": row['format']
            })
            
        # Get Theatres
        cursor.execute('SELECT * FROM theatres WHERE city = ?', (city_name,))
        theatres = []
        for row in cursor.fetchall():
            theatres.append({
                "TheatreName": row['name'],
                "TheatreCode": row['slug'],
                "City": row['city']
            })
            
        metadata[city_name] = {
            "movies": movies,
            "theatres": theatres,
            "filters": {"Languages": [], "Formats": []} 
        }
        
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved {METADATA_FILE}")

def main():
    cities = load_cities()
    
    # Initialize DB
    for city in cities:
        city_name = city['name']
        print(f"Processing {city_name}...")
        
        # 1. Get URLs
        urls = get_movie_urls_selenium(city_name)
        print(f"  Found {len(urls)} movies.")
        
        movies_data = []
        for url in urls[:10]: # Limit to 10
            print(f"  Fetching {url}...")
            details = fetch_movie_details(url, city_name)
            if details:
                movies_data.append(details)
                time.sleep(0.5)
                
        # 2. Save to DB
        if movies_data:
            save_to_db(city_name, movies_data)
            
    # 3. Export
    export_metadata()

if __name__ == "__main__":
    main()
