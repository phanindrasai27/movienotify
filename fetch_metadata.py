import requests
from bs4 import BeautifulSoup
import json
import os
import time

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
}

DATA_DIR = 'data'
CITIES_FILE = os.path.join(DATA_DIR, 'cities.json')
MOVIES_FILE = os.path.join(DATA_DIR, 'movies.json')

def load_cities():
    if os.path.exists(CITIES_FILE):
        with open(CITIES_FILE, 'r') as f:
            return json.load(f)
    return []

def fetch_movies_for_city(city_name, city_code):
    print(f"Fetching movies for {city_name}...")
    # BMS URL structure: https://in.bookmyshow.com/explore/movies-chennai
    # Note: This is a simplified approach. BMS structure is complex.
    # We might need to use their API or a more robust scraping strategy.
    # For now, let's try scraping the 'Now Showing' page.
    
    url = f"https://in.bookmyshow.com/explore/movies-{city_name.lower()}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        movies = []
        # This selector is fragile and depends on BMS class names
        # Looking for movie cards. Common class often contains 'CommonStyles__LinkWrapper' or similar
        # A better heuristic: Look for links that contain '/movies/' in href
        
        seen_titles = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/movies/' in href and not 'buytickets' in href:
                # Extract title
                # Usually inside a div or img alt
                title = a.get_text().strip()
                if not title:
                    img = a.find('img')
                    if img and img.get('alt'):
                        title = img['alt']
                
                if title and title not in seen_titles:
                    # Clean up title
                    movies.append({
                        "title": title,
                        "url": "https://in.bookmyshow.com" + href,
                        "city": city_name
                    })
                    seen_titles.add(title)
        
        print(f"  Found {len(movies)} movies.")
        return movies

    except Exception as e:
        print(f"  Error fetching {city_name}: {e}")
        return []

def main():
    cities = load_cities()
    all_movies = {}

    for city in cities:
        city_movies = fetch_movies_for_city(city['name'], city['code'])
        all_movies[city['name']] = city_movies
        time.sleep(2) # Be polite

    with open(MOVIES_FILE, 'w') as f:
        json.dump(all_movies, f, indent=2)
    print(f"Saved movie metadata to {MOVIES_FILE}")

if __name__ == "__main__":
    main()
