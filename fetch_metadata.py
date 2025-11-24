import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import time
import re

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

def fetch_movies_from_url(url, city_name, status):
    print(f"  Fetching {status} for {city_name}...")
    movies = []
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"    Failed to fetch {url}: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        seen_titles = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/movies/' in href and not 'buytickets' in href:
                title = a.get_text().strip()
                if not title:
                    img = a.find('img')
                    if img and img.get('alt'):
                        title = img['alt']
                
                if title and title not in seen_titles:
                    title = re.sub(r'\s+', ' ', title).strip()
                    if len(title) > 1:
                        movies.append({
                            "title": title,
                            "url": "https://in.bookmyshow.com" + href if not href.startswith('http') else href,
                            "city": city_name,
                            "status": status
                        })
                        seen_titles.add(title)
    except Exception as e:
        print(f"    Error: {e}")
    return movies

def fetch_theatres_for_city(city_name):
    print(f"  Fetching theatres for {city_name}...")
    url = f"https://in.bookmyshow.com/explore/cinemas-{city_name.lower()}"
    theatres = []
    try:
        response = scraper.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        seen = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/cinemas/' in href or '/cinema-card/' in href:
                name = a.get_text().strip()
                if name and name not in seen:
                    theatres.append({
                        "name": name,
                        "url": "https://in.bookmyshow.com" + href if not href.startswith('http') else href,
                        "city": city_name
                    })
                    seen.add(name)
    except Exception as e:
        print(f"    Error fetching theatres: {e}")
    return theatres

def fetch_filters_for_city(city_name):
    print(f"  Fetching filters for {city_name}...")
    formats = ["IMAX", "4DX", "2D", "3D", "ICE", "ScreenX", "MX4D", "PVR", "INOX", "Gold", "Luxe"]
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
        print(f"    Error fetching filters: {e}")
        
    return {
        "formats": sorted(formats),
        "languages": sorted(languages)
    }

def main():
    cities = load_cities()
    full_metadata = {}

    for city in cities:
        city_name = city['name']
        print(f"Processing {city_name}...")
        
        # 1. Movies
        now_showing = fetch_movies_from_url(
            f"https://in.bookmyshow.com/explore/movies-{city_name.lower()}", 
            city_name, "NOW_SHOWING"
        )
        coming_soon = fetch_movies_from_url(
            f"https://in.bookmyshow.com/explore/upcoming-movies-{city_name.lower()}", 
            city_name, "COMING_SOON"
        )
        
        # 2. Theatres
        theatres = fetch_theatres_for_city(city_name)
        
        # 3. Filters
        filters = fetch_filters_for_city(city_name)
        
        full_metadata[city_name] = {
            "movies": now_showing + coming_soon,
            "theatres": theatres,
            "filters": filters
        }
        
        time.sleep(2) # Be polite

    with open(METADATA_FILE, 'w') as f:
        json.dump(full_metadata, f, indent=2)
        
    print(f"Saved consolidated metadata to {METADATA_FILE}")

if __name__ == "__main__":
    main()
