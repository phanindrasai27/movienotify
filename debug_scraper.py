import cloudscraper
from bs4 import BeautifulSoup
import json

scraper = cloudscraper.create_scraper()
url = "https://www.district.in/movies/"

print(f"Fetching {url}...")
try:
    resp = scraper.get(url)
    print(f"Status: {resp.status_code}")
    
    with open("district_dump.html", "w") as f:
        f.write(resp.text)
        
    print("Saved district_dump.html")
    
    # Quick check for keywords
    if "__NEXT_DATA__" in resp.text:
        print("Found __NEXT_DATA__ in text")
    else:
        print("No __NEXT_DATA__ found")
        
    if "window.__INITIAL_STATE__" in resp.text:
        print("Found window.__INITIAL_STATE__")
        
except Exception as e:
    print(f"Error: {e}")
