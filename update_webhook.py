#!/usr/bin/env python3
"""
Update Green API webhook URL with current ngrok tunnel
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def update_webhook():
    instance_id = os.getenv('GREEN_API_INSTANCE_ID')
    token = os.getenv('GREEN_API_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if not all([instance_id, token, webhook_url]):
        print("❌ Missing required environment variables:")
        print(f"   GREEN_API_INSTANCE_ID: {instance_id}")
        print(f"   GREEN_API_TOKEN: {'***' if token else 'None'}")
        print(f"   WEBHOOK_URL: {webhook_url}")
        return False
    
    # Use the actual Green API URL format
    api_url = f"https://7105.api.greenapi.com/waInstance{instance_id}/setSettings/{token}"
    
    settings = {
        "webhookUrl": f"{webhook_url}/webhook/whatsapp",
        "webhookUrlToken": os.getenv('WHATSAPP_VERIFY_TOKEN', 'test_verify_token_12345'),
        "getSettings": True,
        "sendMessages": True,
        "receiveNotifications": True
    }
    
    try:
        print(f"🔄 Updating webhook to: {webhook_url}/webhook/whatsapp")
        response = requests.post(api_url, json=settings, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Webhook updated successfully!")
            print(f"   Webhook URL: {webhook_url}/webhook/whatsapp")
            print(f"   API Response: {response.json()}")
            return True
        else:
            print(f"❌ Failed to update webhook: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating webhook: {e}")
        return False

def get_current_settings():
    """Get current Green API settings"""
    instance_id = os.getenv('GREEN_API_INSTANCE_ID')
    token = os.getenv('GREEN_API_TOKEN')
    
    if not all([instance_id, token]):
        print("❌ Missing Green API credentials")
        return None
    
    api_url = f"https://7105.api.greenapi.com/waInstance{instance_id}/getSettings/{token}"
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get settings: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting settings: {e}")
        return None

def test_webhook():
    """Test webhook endpoint"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ No webhook URL configured")
        return False
    
    test_url = f"{webhook_url}/webhook/whatsapp"
    
    try:
        # Test GET request (verification)
        response = requests.get(test_url, params={
            'hub.verify_token': os.getenv('WHATSAPP_VERIFY_TOKEN', 'test_verify_token_12345'),
            'hub.challenge': 'test_challenge'
        }, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Webhook endpoint is responding: {test_url}")
            return True
        else:
            print(f"❌ Webhook endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Green API Webhook Configuration")
    print("=" * 50)
    
    # Show current settings
    print("\n📋 Current Green API Settings:")
    settings = get_current_settings()
    if settings:
        print(f"   Webhook URL: {settings.get('webhookUrl', 'Not set')}")
        print(f"   Webhook Token: {settings.get('webhookUrlToken', 'Not set')}")
    
    # Test webhook endpoint
    print("\n🧪 Testing webhook endpoint...")
    test_webhook()
    
    # Update webhook
    print("\n🔄 Updating webhook...")
    success = update_webhook()
    
    if success:
        print("\n✅ Webhook configuration complete!")
    else:
        print("\n❌ Webhook configuration failed!")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your Green API credentials in .env file")
        print("   2. Ensure your Green API instance is active")
        print("   3. Verify ngrok tunnel is running")
        print("   4. Check if Flask app is accessible via ngrok URL")
