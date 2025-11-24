import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import time
import re
import datetime

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

def fetch_theatres_via_heuristic(city_name, city_code, city_slug, movies):
    print(f"  Fetching theatres for {city_name} (Heuristic)...")
    theatres = []
    seen = set()
    
    # Try top 3 movies to cover most cinemas
    target_movies = movies[:3]
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    for movie in target_movies:
        try:
            # Construct Booking URL
            # Movie URL: .../movies/chennai/mastiii-4/ET00464040
            # Booking URL: .../buytickets/mastiii-4-chennai/movie-chen-ET00464040-MT/20251124
            
            parts = movie['url'].split('/')
            event_code = parts[-1]
            slug = parts[-2]
            
            # Region code logic: usually city code works, but sometimes it's first 4 chars
            # We'll try city_code first
            region_part = city_code
             
            book_url = f"https://in.bookmyshow.com/buytickets/{slug}-{city_slug}/movie-{region_part}-{event_code}-MT/{today}"
            
            print(f"    Checking {book_url}...")
            resp = scraper.get(book_url)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Scrape cinemas
                count = 0
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
                            count += 1
                
                # Fallback: check generic venue classes if no links found
                if count == 0:
                     for div in soup.find_all('a', class_='__venue-name'):
                         name = div.get_text().strip()
                         if name and name not in seen:
                             theatres.append({
                                "name": name,
                                "url": "", # No URL but name is enough
                                "city": city_name
                            })
                             seen.add(name)
                             count += 1
                             
                print(f"      Found {count} new theatres.")
            
            time.sleep(1) # Be polite
            
        except Exception as e:
            print(f"    Error processing movie {movie['title']}: {e}")
            
    print(f"    Total unique theatres found: {len(theatres)}")
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
        city_code = city['code']
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
        
        # 2. Theatres (Heuristic)
        # Only use Now Showing movies for heuristic
        theatres = fetch_theatres_via_heuristic(city_name, city_code, city['slug'], now_showing)
        
        # 3. Filters
        filters = fetch_filters_for_city(city_name)
        
        full_metadata[city_name] = {
            "movies": now_showing + coming_soon,
            "theatres": theatres,
            "filters": filters
        }
        
        time.sleep(2)

    with open(METADATA_FILE, 'w') as f:
        json.dump(full_metadata, f, indent=2)
        
    print(f"Saved consolidated metadata to {METADATA_FILE}")

if __name__ == "__main__":
    main()
