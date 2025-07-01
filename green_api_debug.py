#!/usr/bin/env python3
"""
Quick Green API Join Test
Test the complete join flow with Green API integration
"""
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

def test_join_flow():
    """Test the complete join flow"""
    print("🧪 Testing Green API Join Flow")
    print("=" * 50)
    
    try:
        # 1. Test Green API connection
        print("1️⃣ Testing Green API connection...")
        from src.integrations.green_api import green_api_client
        
        print(f"   Instance ID: {green_api_client.instance_id}")
        print(f"   Phone: {green_api_client.phone_number}")
        print(f"   Configured: {green_api_client.configured}")
        
        if not green_api_client.configured:
            print("❌ Green API not configured!")
            return False
        
        # Check instance state
        state = green_api_client.get_state_instance()
        print(f"   State: {state.get('stateInstance', 'Unknown')}")
        
        # 2. Test webhook processing
        print("\n2️⃣ Testing webhook processing...")
        from src.integrations.green_api import process_green_api_webhook
        
        # Simulate Green API webhook for "join" message
        fake_webhook = {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": int(green_api_client.instance_id),
                "wid": f"{green_api_client.phone_number.replace('+', '')}@c.us",
                "typeInstance": "whatsapp"
            },
            "timestamp": int(time.time()),
            "idMessage": f"TEST_{int(time.time())}",
            "senderData": {
                "chatId": f"{green_api_client.phone_number.replace('+', '')}@c.us",
                "chatName": "Test User",
                "senderName": "Test User"
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {
                    "textMessage": "join"
                }
            }
        }
        
        processed = process_green_api_webhook(fake_webhook)
        if processed:
            print(f"   ✅ Webhook processed successfully")
            print(f"   From: {processed.get('from')}")
            print(f"   Text: {processed.get('text', {}).get('body')}")
        else:
            print("   ❌ Failed to process webhook")
            return False
        
        # 3. Test message sending
        print("\n3️⃣ Testing message sending...")
        result = green_api_client.send_message(
            green_api_client.phone_number, 
            "🧪 Test: Green API join flow working!"
        )
        
        if result.get('error'):
            print(f"   ❌ Send failed: {result.get('error')}")
            return False
        else:
            print(f"   ✅ Message sent: {result.get('idMessage')}")
        
        # 4. Test Celery task (without actually running)
        print("\n4️⃣ Testing Celery task...")
        from src.tasks.celery_tasks import send_whatsapp_message, process_whatsapp_message
        
        # Check if USE_GREEN_API is set correctly
        from src.tasks.celery_tasks import USE_GREEN_API, GREEN_API_INSTANCE_ID, GREEN_API_TOKEN
        print(f"   USE_GREEN_API: {USE_GREEN_API}")
        print(f"   Instance ID: {GREEN_API_INSTANCE_ID}")
        print(f"   Token: {'Set' if GREEN_API_TOKEN else 'Not set'}")
        
        if not USE_GREEN_API:
            print("   ❌ USE_GREEN_API is False - environment variables not loaded!")
            print("   💡 Try restarting Celery worker after updating .env file")
            return False
        
        print("   ✅ Celery configuration looks good")
        
        print("\n🎉 All tests passed!")
        print("\n📋 Next steps:")
        print("1. Make sure your Green API webhook URL is set to your ngrok URL")
        print("2. Restart Celery worker to pick up new environment variables")
        print("3. Send 'join' to your WhatsApp number and check logs")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_environment():
    """Check environment configuration"""
    print("🔧 Environment Check")
    print("=" * 30)
    
    env_vars = [
        'GREEN_API_INSTANCE_ID',
        'GREEN_API_TOKEN', 
        'GREEN_API_URL',
        'WHATSAPP_PHONE_NUMBER'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'TOKEN' in var:
                print(f"✅ {var}: {value[:10]}...")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
    
    print()

def manual_send_test():
    """Manual test to send a message"""
    print("📤 Manual Send Test")
    print("=" * 30)
    
    try:
        from src.integrations.green_api import green_api_client
        
        if not green_api_client.configured:
            print("❌ Green API not configured")
            return
        
        phone = input(f"Phone number (default: {green_api_client.phone_number}): ").strip()
        if not phone:
            phone = green_api_client.phone_number
        
        message = input("Message (default: 'Test from AI Beer Crawl'): ").strip()
        if not message:
            message = "🧪 Test from AI Beer Crawl - manual send test"
        
        print(f"Sending to {phone}: {message}")
        result = green_api_client.send_message(phone, message)
        
        if result.get('error'):
            print(f"❌ Failed: {result.get('error')}")
        else:
            print(f"✅ Sent! Message ID: {result.get('idMessage')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🍺 AI Beer Crawl - Green API Debug Tool")
    print("=" * 60)
    
    while True:
        print("\nSelect an option:")
        print("1. Check environment variables")
        print("2. Test complete join flow")
        print("3. Manual send test")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            check_environment()
        elif choice == '2':
            test_join_flow()
        elif choice == '3':
            manual_send_test()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")
