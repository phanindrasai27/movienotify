import sqlite3
import os
import re
from twilio.rest import Client
from database import get_db_connection

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.environ.get('TWILIO_FROM_WHATSAPP')
TWILIO_TO = os.environ.get('TWILIO_TO_WHATSAPP')

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

def check_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get active requests
    cursor.execute('SELECT * FROM tracking_requests WHERE is_active = 1')
    requests = cursor.fetchall()
    
    if not requests:
        print("No active tracking requests.")
        return

    for req in requests:
        print(f"Checking request: {req['movie_pattern']} in {req['city']}")
        
        # Build query
        # We want to find showtimes for movies matching the pattern
        # in the specified city.
        
        query = '''
            SELECT m.title, t.name, s.show_time, s.show_date, s.link
            FROM showtimes s
            JOIN movies m ON s.movie_id = m.id
            JOIN theatres t ON s.theatre_id = t.id
            WHERE m.city = ?
        '''
        params = [req['city']]
        
        if req['movie_pattern']:
            query += ' AND m.title LIKE ?'
            params.append(f"%{req['movie_pattern']}%")
            
        if req['theatre_pattern']:
            query += ' AND t.name LIKE ?'
            params.append(f"%{req['theatre_pattern']}%")
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if results:
            # Found matches!
            # Group by movie
            matches = {}
            for r in results:
                title = r['title']
                if title not in matches: matches[title] = []
                matches[title].append(f"{r['name']} @ {r['show_time']}")
            
            # Construct message
            msg_lines = [f"🎬 Alert! Found tickets for '{req['movie_pattern']}' in {req['city']}:"]
            for title, shows in matches.items():
                msg_lines.append(f"\n*{title}*")
                for s in shows[:5]: # Limit to 5 per movie
                    msg_lines.append(f"- {s}")
                if len(shows) > 5:
                    msg_lines.append(f"...and {len(shows)-5} more.")
            
            message = "\n".join(msg_lines)
            send_whatsapp(message)
            
            # Update last_notified (optional logic to avoid spam)
            # cursor.execute('UPDATE tracking_requests SET last_notified_at = CURRENT_TIMESTAMP WHERE id = ?', (req['id'],))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_alerts()
