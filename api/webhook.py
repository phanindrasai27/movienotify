from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from github import Github
import os
import json

app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def bot():
    # 1. Get the message from Twilio
    incoming_msg = request.values.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()

    # 2. Authenticate with GitHub
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPO") # e.g., "username/repo"
    
    if not github_token or not repo_name:
        msg.body("⚠️ Error: Server misconfiguration (Missing GitHub secrets).")
        return str(resp)

    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        file_path = "config.json"
        
        # 3. Handle Commands
        if incoming_msg.lower().startswith("track "):
            # Extract URL
            new_url = incoming_msg[6:].strip()
            
            # Update config.json in GitHub
            contents = repo.get_contents(file_path)
            current_config = json.loads(contents.decoded_content.decode())
            current_config["url"] = new_url
            
            # Commit changes
            repo.update_file(
                path=file_path,
                message=f"Update movie URL via WhatsApp: {new_url}",
                content=json.dumps(current_config, indent=2),
                sha=contents.sha
            )
            
            msg.body(f"✅ Roger that! Now tracking: {new_url}")
            
        elif incoming_msg.lower() == "status":
            contents = repo.get_contents(file_path)
            current_config = json.loads(contents.decoded_content.decode())
            current_url = current_config.get("url", "Unknown")
            msg.body(f"🕵️ Currently tracking: {current_url}")
            
        else:
            msg.body("🤖 I didn't understand that.\n\nCommands:\n- 'Track [URL]': Change movie\n- 'Status': Check current movie")

    except Exception as e:
        msg.body(f"⚠️ Error processing request: {str(e)}")

    return str(resp)

if __name__ == '__main__':
    app.run()
