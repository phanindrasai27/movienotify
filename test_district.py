import cloudscraper
from bs4 import BeautifulSoup
import json

scraper = cloudscraper.create_scraper()
url = "https://www.district.in/movies/aaromaley-movie-tickets-in-chennai-MV208761"

print(f"Fetching {url}...")
try:
    resp = scraper.get(url)
    print(f"Status: {resp.status_code}")
    
    # Check for showtimes in HTML
    if "03:05 PM" in resp.text:
        print("Found showtime in HTML (SSR)!")
    else:
        print("Showtime NOT found in HTML (Likely CSR).")
        
    # Check for JSON-LD
    soup = BeautifulSoup(resp.text, 'html.parser')
    scripts = soup.find_all('script', type='application/ld+json')
    print(f"Found {len(scripts)} JSON-LD scripts.")
    for s in scripts:
        print(s.string[:100])
        
    # Check for __NEXT_DATA__ (Common in Next.js apps)
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        print("Found __NEXT_DATA__!")
        data = json.loads(next_data.string)
        print("Keys:", data.keys())
        # Inspect props
        if 'props' in data:
            print("Props keys:", data['props'].keys())
            if 'pageProps' in data['props']:
                 print("PageProps keys:", data['props']['pageProps'].keys())

except Exception as e:
    print(f"Error: {e}")
