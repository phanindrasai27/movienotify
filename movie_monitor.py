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
        phone = alert.get("phone") # User's WhatsApp number
        filters = alert.get("filters", []) # List of keywords e.g. ["IMAX", "PVR"]
        
        if not movie_url:
            continue

        print(f"Checking: {movie_name} ({movie_url})")
        if filters:
            print(f"  Filters: {filters}")

        try:
            response = requests.get(movie_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            page_text = soup.get_text().lower()
            
            if "book tickets" in page_text:
                print(f"  'Book Tickets' found for {movie_name}.")
                
                # If no filters, notify immediately
                if not filters:
                    print(f"  No filters set. Sending notification.")
                    send_whatsapp_message(phone, f"🎟️ Tickets available for *{movie_name}*! \n\nBook now: {movie_url}")
                    continue
                
                # If filters exist, try to find the booking link
                # BMS usually has a 'book tickets' button that links to the showtimes page
                # We look for an <a> tag containing 'book tickets' or similar class
                booking_link = None
                
                # Strategy 1: Look for link with "book tickets" text
                for a in soup.find_all('a', href=True):
                    if "book tickets" in a.get_text().lower():
                        booking_link = a['href']
                        break
                
                # Strategy 2: Look for common BMS booking button classes (fallback)
                if not booking_link:
                    # This is a guess, BMS changes classes often. 
                    # But often the URL itself changes from /movies/... to /buytickets/...
                    # If we are already on the movie page, we might need to construct the URL
                    pass

                if booking_link:
                    # Handle relative URLs
                    if not booking_link.startswith('http'):
                        booking_link = "https://in.bookmyshow.com" + booking_link
                        
                    print(f"  Checking booking page: {booking_link}")
                    
                    try:
                        booking_response = requests.get(booking_link, headers=headers)
                        booking_response.raise_for_status()
                        booking_soup = BeautifulSoup(booking_response.text, 'html.parser')
                        booking_text = booking_soup.get_text().lower()
                        
                        # Check for ANY of the filters
                        found_filters = [f for f in filters if f.lower() in booking_text]
                        
                        if found_filters:
                            print(f"  ✅ Found matching filters: {found_filters}")
                            send_whatsapp_message(phone, f"🎟️ Tickets available for *{movie_name}*! \n\nMatches: {', '.join(found_filters)}\nBook now: {booking_link}")
                        else:
                            print(f"  ❌ Tickets open, but no matching filters found.")
                            
                    except Exception as e:
                        print(f"  Error checking booking page: {e}")
                        # Fallback: Notify anyway if we can't check filters? 
                        # No, user asked for filters to avoid spam.
                else:
                    print("  Could not find booking link to verify filters. Skipping notification.")
            else:
                print(f"  Tickets not yet available for {movie_name}.")

        except Exception as e:
            print(f"Error checking {movie_name}: {e}")

if __name__ == "__main__":
    check_tickets()
