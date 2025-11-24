import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import time
import re
import datetime
from database import get_db_connection

# Cloudscraper instance
scraper = cloudscraper.create_scraper()

DATA_DIR = 'data'
CITIES_FILE = os.path.join(DATA_DIR, 'cities.json')
METADATA_FILE = os.path.join(DATA_DIR, 'metadata.json')

def load_cities():
    if os.path.exists(CITIES_FILE):
        with open(CITIES_FILE, 'r') as f:
            return json.load(f)
    return []

# ===== BMS Scraping Functions =====

def fetch_bms_movies(url, city_name, status):
    print(f"  [BMS] Fetching {status} for {city_name}...")
    movies = []
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        seen_titles = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/movies/' in href and not 'buytickets' in href:
                # Try to get title from img alt first (more reliable)
                title = None
                img = a.find('img')
                if img and img.get('alt'):
                    title = img['alt'].strip()
                
                # If no image, get text content
                if not title:
                    title = a.get_text().strip()
                
                if title and title not in seen_titles:
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title).strip()
                    # Remove genre prefixes if present (e.g., "Action/ThrillerMovie Name")
                    title = re.sub(r'^[A-Za-z]+(/[A-Za-z]+)*', '', title).strip()
                    
                    if len(title) > 1:
                        movies.append({
                            "title": title,
                            "url": "https://in.bookmyshow.com" + href if not href.startswith('http') else href,
                            "city": city_name,
                            "status": status,
                            "source": "BMS"
                        })
                        seen_titles.add(title)
    except Exception as e:
        print(f"    [BMS] Error: {e}")
    return movies

def fetch_bms_theatres(city_name, city_code, city_slug, movies):
    print(f"  [BMS] Fetching theatres for {city_name}...")
    theatres = []
    seen = set()
    
    target_movies = movies[:3]
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    for movie in target_movies:
        try:
            parts = movie['url'].split('/')
            event_code = parts[-1]
            slug = parts[-2]
            region_part = city_code
              
            book_url = f"https://in.bookmyshow.com/buytickets/{slug}-{city_slug}/movie-{region_part}-{event_code}-MT/{today}"
            
            resp = scraper.get(book_url)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for a in soup.find_all('a', href=True):
                    if '/cinemas/' in a['href']:
                        name = a.get_text().strip()
                        href = a['href']
                        if name and name not in seen:
                            theatres.append({
                                "name": name,
                                "url": "https://in.bookmyshow.com" + href if not href.startswith('http') else href,
                                "city": city_name
                            })
                            seen.add(name)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"    [BMS] Error processing {movie['title']}: {e}")
            
    print(f"    [BMS] Found {len(theatres)} theatres.")
    return theatres

def fetch_bms_filters(city_name):
    formats = ["IMAX", "4DX", "2D", "3D", "ICE", "ScreenX", "MX4D"]
    languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam", "Kannada"]
    
    url = f"https://in.bookmyshow.com/explore/movies-{city_name.lower()}"
    try:
        response = scraper.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        scraped_formats = set()
        text_content = soup.get_text()
        
        for fmt in formats:
            if fmt in text_content:
                scraped_formats.add(fmt)
                
        if len(scraped_formats) > 2:
            formats = list(scraped_formats)
            
    except Exception as e:
        print(f"    [BMS] Error fetching filters: {e}")
        
    return {
        "formats": sorted(formats),
        "languages": sorted(languages)
    }

# ===== Database Integration =====

def save_movies_to_db(city_name, all_movies):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for movie in all_movies:
        # Clean title
        title = movie['title']
        if title.startswith("Book "):
            title = title[5:]
        
        # Create slug from URL
        if 'bookmyshow' in movie['url']:
            slug = movie['url'].split('/')[-1]
        else:
            slug = movie['url'].split('/')[-1]
        
        # Insert movie
        cursor.execute('''
            INSERT OR IGNORE INTO movies (title, slug, city, language, format)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, slug, city_name, movie.get('language', 'Unknown'), movie.get('format', '2D')))
    
    conn.commit()
    conn.close()

def save_theatres_to_db(city_name, theatres):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for theatre in theatres:
        slug = re.sub(r'[^a-zA-Z0-9]', '', theatre['name'].lower())
        
        cursor.execute('''
            INSERT OR IGNORE INTO theatres (name, city, slug)
            VALUES (?, ?, ?)
        ''', (theatre['name'], city_name, slug))
    
    conn.commit()
    conn.close()

def export_metadata():
    print("Exporting unified metadata...")
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
            title = row['title']
            if title.startswith("Book "):
                title = title[5:]
            
             # Determine URL based on slug pattern
            slug = row['slug']
            if slug.startswith('ET') or slug.startswith('MV'):
                # BMS or District slug
                if '-' in slug and not slug.startswith('ET'):
                    url = f"https://www.district.in/movies/{slug}"
                else:
                    # BMS URL - reconstruct
                    url = f"https://in.bookmyshow.com/movies/{city_name.lower()}/{slug}"
            else:
                url = f"https://www.district.in/movies/{slug}"
            
            movies.append({
                "title": title,
                "url": url,
                "status": "NOW_SHOWING",  # Can enhance later
                "city": row['city']
            })
            
        # Get Theatres
        cursor.execute('SELECT * FROM theatres WHERE city = ?', (city_name,))
        theatres = []
        for row in cursor.fetchall():
            if row['name'] == "Unknown Theatre (Scraped)":
                continue
                
            theatres.append({
                "name": row['name'],
                "url": row.get('url', ''),
                "city": row['city']
            })
            
        # Get unique formats and languages
        cursor.execute('SELECT DISTINCT format FROM movies WHERE city = ? AND format IS NOT NULL', (city_name,))
        formats = [r[0] for r in cursor.fetchall() if r[0] and r[0] != "Unknown"]
        
        cursor.execute('SELECT DISTINCT language FROM movies WHERE city = ? AND language IS NOT NULL', (city_name,))
        languages = [r[0] for r in cursor.fetchall() if r[0] and r[0] != "Unknown"]
        
        metadata[city_name] = {
            "movies": movies,
            "theatres": theatres,
            "filters": {
                "formats": formats if formats else ["2D", "3D", "IMAX", "4DX"],
                "languages": languages if languages else ["English", "Hindi", "Tamil", "Telugu"]
            }
        }
        
    conn.close()
    
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved unified metadata to {METADATA_FILE}")

def main():
    cities = load_cities()
    
    for city in cities:
        city_name = city['name']
        city_code = city['code']
        city_slug = city['slug']
        print(f"\nProcessing {city_name}...")
        
        # 1. Scrape BMS
        now_showing = fetch_bms_movies(
            f"https://in.bookmyshow.com/explore/movies-{city_name.lower()}", 
            city_name, "NOW_SHOWING"
        )
        coming_soon = fetch_bms_movies(
            f"https://in.bookmyshow.com/explore/upcoming-movies-{city_name.lower()}", 
            city_name, "COMING_SOON"
        )
        
        all_movies = now_showing + coming_soon
        
        # 2. Scrape BMS Theatres
        theatres = fetch_bms_theatres(city_name, city_code, city_slug, now_showing)
        
        # 3. Save to DB
        if all_movies:
            save_movies_to_db(city_name, all_movies)
        if theatres:
            save_theatres_to_db(city_name, theatres)
        
        print(f"  Total Movies: {len(all_movies)} | Theatres: {len(theatres)}")
        time.sleep(2)
    
    # 4. Export final metadata
    export_metadata()

if __name__ == "__main__":
    main()
