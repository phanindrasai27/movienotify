import os
import requests
from bs4 import BeautifulSoup
import sys
import json
from twilio.rest import Client

def send_whatsapp_message(to_number, message):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_FROM_WHATSAPP") # e.g., "whatsapp:+14155238886"
    
    # Use the number from the alert if present, otherwise fallback to env var (for legacy/testing)
    to_whatsapp = to_number if to_number else os.environ.get("TWILIO_TO_WHATSAPP")
    
    if not account_sid or not auth_token:
        print("Error: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set.")
        return

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message,
            from_=from_whatsapp,
            to=to_whatsapp
        )
        print(f"Notification sent successfully to {to_whatsapp}! SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

def get_alerts():
    # Read from alerts.json
    try:
        with open("alerts.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading alerts.json: {e}")
        return []

def check_tickets():
    alerts = get_alerts()
    if not alerts:
        print("No alerts found in alerts.json.")
        return

    print(f"Checking {len(alerts)} alerts...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    for alert in alerts:
        movie_url = alert.get("url")
        movie_name = alert.get("name", "Unknown Movie")
        phone = alert.get("phone") 
        filters = alert.get("filters", []) 
        
        if not movie_url:
            continue

        print(f"Checking: {movie_name}")
        
        # Separate filters
        time_filters = [f.split(':')[1] for f in filters if f.startswith('TIME:')]
        text_filters = [f for f in filters if not f.startswith('TIME:')]

        try:
            response = requests.get(movie_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text().lower()
            
            if "book tickets" in page_text:
                print(f"  'Book Tickets' found.")
                
                # If no filters, notify
                if not filters:
                    send_whatsapp_message(phone, f"🎟️ Tickets available for *{movie_name}*! \n\nBook: {movie_url}")
                    continue

                # Find booking link
                booking_link = None
                for a in soup.find_all('a', href=True):
                    if "book tickets" in a.get_text().lower():
                        booking_link = a['href']
                        break
                
                if booking_link:
                    if not booking_link.startswith('http'):
                        booking_link = "https://in.bookmyshow.com" + booking_link
                        
                    print(f"  Checking showtimes: {booking_link}")
                    try:
                        booking_response = requests.get(booking_link, headers=headers)
                        booking_soup = BeautifulSoup(booking_response.text, 'html.parser')
                        booking_text = booking_soup.get_text().lower()
                        
                        # 1. Check Text Filters (IMAX, PVR)
                        matches_text = False
                        if text_filters:
                            found = [f for f in text_filters if f.lower() in booking_text]
                            if found:
                                matches_text = True
                                print(f"    Matched text filters: {found}")
                        else:
                            matches_text = True # No text filters = pass

                        # 2. Check Time Filters (Morning, Evening)
                        matches_time = False
                        if time_filters:
                            # Heuristic: Look for time strings like "10:00 AM", "06:30 PM"
                            # This is tricky without a proper parser, but we can scan the text
                            # for times and categorize them.
                            import re
                            times_found = re.findall(r'(\d{1,2}):(\d{2})\s?(AM|PM)', booking_response.text, re.IGNORECASE)
                            
                            for h, m, p in times_found:
                                hour = int(h)
                                period = p.upper()
                                if period == 'PM' and hour != 12: hour += 12
                                if period == 'AM' and hour == 12: hour = 0
                                
                                # Categories
                                is_morning = 5 <= hour < 12
                                is_afternoon = 12 <= hour < 16
                                is_evening = 16 <= hour < 20
                                is_night = hour >= 20 or hour < 5
                                
                                if 'MORNING' in time_filters and is_morning: matches_time = True
                                if 'AFTERNOON' in time_filters and is_afternoon: matches_time = True
                                if 'EVENING' in time_filters and is_evening: matches_time = True
                                if 'NIGHT' in time_filters and is_night: matches_time = True
                                
                            if matches_time:
                                print(f"    Matched time filters.")
                        else:
                            matches_time = True # No time filters = pass

                        if matches_text and matches_time:
                            send_whatsapp_message(phone, f"🎟️ Tickets found for *{movie_name}*! \n\nFilters Matched! \nBook: {booking_link}")
                        else:
                            print("    Filters did not match.")

                    except Exception as e:
                        print(f"  Error checking booking page: {e}")
                else:
                    print("  Could not find booking link.")
            else:
                print(f"  Not open yet.")

        except Exception as e:
            print(f"Error checking {movie_name}: {e}")

if __name__ == "__main__":
    check_tickets()
