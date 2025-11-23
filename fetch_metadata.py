import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
}

DATA_DIR = 'data'
CITIES_FILE = os.path.join(DATA_DIR, 'cities.json')
MOVIES_FILE = os.path.join(DATA_DIR, 'movies.json')
THEATRES_FILE = os.path.join(DATA_DIR, 'theatres.json')

def load_cities():
    if os.path.exists(CITIES_FILE):
        with open(CITIES_FILE, 'r') as f:
            return json.load(f)
    return []

def fetch_movies_from_url(url, city_name, status):
    print(f"  Fetching {status} for {city_name}...")
    movies = []
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"    Failed to fetch {url}: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        seen_titles = set()
        
        # BMS structure varies. Look for movie cards.
        # Common pattern: Links containing '/movies/'
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/movies/' in href and not 'buytickets' in href:
                title = a.get_text().strip()
                if not title:
                    img = a.find('img')
                    if img and img.get('alt'):
                        title = img['alt']
                
                if title and title not in seen_titles:
                    # Clean title
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
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        seen = set()
        
        # Look for cinema links
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

def main():
    cities = load_cities()
    all_movies = {}
    all_theatres = {}

    for city in cities:
        city_name = city['name']
        city_code = city['code']
        
        # 1. Fetch Now Showing
        now_showing = fetch_movies_from_url(
            f"https://in.bookmyshow.com/explore/movies-{city_name.lower()}", 
            city_name, 
            "NOW_SHOWING"
        )
        
        # 2. Fetch Coming Soon
        coming_soon = fetch_movies_from_url(
            f"https://in.bookmyshow.com/explore/upcoming-movies-{city_name.lower()}", 
            city_name, 
            "COMING_SOON"
        )
        
        all_movies[city_name] = now_showing + coming_soon
        
        # 3. Fetch Theatres
        all_theatres[city_name] = fetch_theatres_for_city(city_name)
        
        time.sleep(1)

    with open(MOVIES_FILE, 'w') as f:
        json.dump(all_movies, f, indent=2)
        
    with open(THEATRES_FILE, 'w') as f:
        json.dump(all_theatres, f, indent=2)
        
    print(f"Saved metadata to {DATA_DIR}")

if __name__ == "__main__":
    main()
