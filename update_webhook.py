#!/usr/bin/env python3
"""Update Green API webhook URL"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Green API credentials
INSTANCE_ID = os.environ.get('GREEN_API_INSTANCE_ID')
TOKEN = os.environ.get('GREEN_API_TOKEN')
BASE_URL = os.environ.get('GREEN_API_URL')

# New webhook URL
NGROK_URL = "https://5d7f-49-49-241-112.ngrok-free.app"
WEBHOOK_URL = f"{NGROK_URL}/webhook/whatsapp"

print(f"Updating webhook URL to: {WEBHOOK_URL}")

# Update settings
url = f"{BASE_URL}/waInstance{INSTANCE_ID}/setSettings/{TOKEN}"
data = {
    "webhookUrl": WEBHOOK_URL,
    "incomingWebhook": "yes",
    "outgoingWebhook": "yes"
}

print(f"Sending request to: {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Webhook URL updated successfully!")
        
        # Verify the update
        verify_url = f"{BASE_URL}/waInstance{INSTANCE_ID}/getSettings/{TOKEN}"
        verify_response = requests.get(verify_url, timeout=30)
        
        if verify_response.status_code == 200:
            settings = verify_response.json()
            current_webhook = settings.get('webhookUrl')
            print(f"Current webhook URL: {current_webhook}")
            
            if current_webhook == WEBHOOK_URL:
                print("✅ Webhook URL verified successfully!")
            else:
                print(f"❌ Webhook URL mismatch. Expected: {WEBHOOK_URL}, Got: {current_webhook}")
        else:
            print(f"❌ Failed to verify webhook URL: {verify_response.text}")
    else:
        print(f"❌ Failed to update webhook URL: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
