import sqlite3
import os
import re
import requests
from twilio.rest import Client
from database import get_db_connection

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.environ.get('TWILIO_FROM_WHATSAPP')
TWILIO_TO = os.environ.get('TWILIO_TO_WHATSAPP')

# GitHub Configuration
GITHUB_REPO = "phanindrasai27/movienotify"
ALERTS_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/alerts.json"

def send_whatsapp(message):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM, TWILIO_TO]):
        print("Twilio credentials missing. Skipping notification.")
        print(f"Message: {message}")
        return

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_FROM,
            to=TWILIO_TO
        )
        print(f"WhatsApp sent: {msg.sid}")
    except Exception as e:
        print(f"Error sending WhatsApp: {e}")

def fetch_alerts_from_github():
    try:
        response = requests.get(ALERTS_URL)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch alerts.json: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return []

def check_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get alerts from GitHub
    alerts = fetch_alerts_from_github()
    
    if not alerts:
        print("No alerts found.")
        return

    for alert in alerts:
        movie_name = alert.get('name')
        city = alert.get('city')
        filters = alert.get('filters', [])
        
        print(f"\nChecking alert: {movie_name} in {city}")
        
        # Build query to find matching movies
        query = 'SELECT m.title, m.slug FROM movies m WHERE 1=1'
        params = []
        
        # Match movie name (partial match)
        if movie_name and movie_name != "Custom Link":
            query += ' AND LOWER(m.title) LIKE LOWER(?)'
            params.append(f"%{movie_name}%")
        
        # Match city
        if city:
            query += ' AND m.city = ?'
            params.append(city)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if results:
            # Found matching movies!
            msg_lines = [f"🎬 Alert! Found tickets for '{movie_name}' in {city}:"]
            
            for row in results:
                title = row['title']
                slug = row['slug']
                
                # Construct URL
                if '-movie-tickets-in-' in slug:
                    url = f"https://www.district.in/movies/{slug}"
                else:
                    url = f"https://in.bookmyshow.com/movies/{city.lower()}/{slug}"
                
                msg_lines.append(f"\n*{title}*")
                msg_lines.append(f"🔗 {url}")
                
                # Check filters if specified
                if filters:
                    msg_lines.append(f"Filters: {', '.join(filters)}")
            
            message = "\n".join(msg_lines)
            send_whatsapp(message)
            print(f"✅ Notification sent for: {movie_name}")
        else:
            print(f"No matches found for: {movie_name}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_alerts()

