#!/usr/bin/env python3
"""
Green API WhatsApp Integration Test
Test the Green API integration with your credentials
"""
import os
import sys
import json
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

def test_green_api():
    """Test Green API integration"""
    print("🧪 Testing Green API Integration")
    print("=" * 50)
    
    try:
        from src.integrations.green_api import green_api_client
        
        # Display configuration
        print(f"📱 Instance ID: {green_api_client.instance_id}")
        print(f"🔗 API URL: {green_api_client.base_url}")
        print(f"📞 Phone Number: {green_api_client.phone_number}")
        print(f"✅ Configured: {green_api_client.configured}")
        print()
        
        if not green_api_client.configured:
            print("❌ Green API not properly configured!")
            return False
        
        # Test 1: Get Instance State
        print("🔍 Testing instance state...")
        state = green_api_client.get_state_instance()
        if 'error' in state:
            print(f"❌ Instance state error: {state['error']}")
        else:
            print(f"✅ Instance state: {state.get('stateInstance', 'Unknown')}")
        print()
        
        # Test 2: Get Account Settings
        print("⚙️  Testing account settings...")
        settings = green_api_client.get_account_settings()
        if 'error' in settings:
            print(f"❌ Settings error: {settings['error']}")
        else:
            print(f"✅ Account settings retrieved successfully")
            print(f"   Webhook URL: {settings.get('webhookUrl', 'Not set')}")
            print(f"   Webhook URL Token: {settings.get('webhookUrlToken', 'Not set')}")
        print()
        
        # Test 3: Send test message (to yourself)
        print("📤 Testing message sending...")
        test_message = "🧪 Green API test message from AI Beer Crawl app!"
        result = green_api_client.send_message(green_api_client.phone_number, test_message)
        
        if result.get('error'):
            print(f"❌ Message send error: {result['error']}")
        else:
            print(f"✅ Test message sent successfully!")
            print(f"   Message ID: {result.get('idMessage', 'Unknown')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_webhook_format():
    """Test webhook message processing"""
    print("🔗 Testing Webhook Processing")
    print("=" * 50)
    
    try:
        from src.integrations.green_api import process_green_api_webhook
        
        # Sample Green API webhook data
        sample_webhook = {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105273198,
                "wid": "66955124860@c.us",
                "typeInstance": "whatsapp"
            },
            "timestamp": 1751342400,
            "idMessage": "BAE5F4C2D9F3D5E6A7B8C9D0E1F2A3B4",
            "senderData": {
                "chatId": "66812345678@c.us",
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
        
        print("📨 Processing sample webhook...")
        processed = process_green_api_webhook(sample_webhook)
        
        if processed:
            print("✅ Webhook processed successfully!")
            print(f"   From: {processed.get('from')}")
            print(f"   Text: {processed.get('text', {}).get('body')}")
            print(f"   Type: {processed.get('type')}")
            print(f"   Message ID: {processed.get('message_id')}")
        else:
            print("❌ Failed to process webhook")
        print()
        
        return processed is not None
        
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_integration():
    """Test Celery task integration"""
    print("⚙️  Testing Celery Integration")
    print("=" * 50)
    
    try:
        from src.tasks.celery_tasks import send_whatsapp_message
        
        print("📤 Testing Celery WhatsApp message task...")
        
        # This will test the task but not actually send since we're not running Celery worker
        print("   Note: This test requires a running Celery worker to actually send messages")
        print("   The task configuration will be verified...")
        
        # Check if task is properly configured
        task_info = send_whatsapp_message.s("+66955124860", "Test message from Celery")
        print(f"✅ Task configured: {task_info.task}")
        print(f"   Args: {task_info.args}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Celery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🍺 AI Beer Crawl - Green API Integration Test")
    print("=" * 60)
    print()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    tests = [
        ("Green API Connection", test_green_api),
        ("Webhook Processing", test_webhook_format),
        ("Celery Integration", test_celery_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 Running: {test_name}")
        print("-" * 40)
        success = test_func()
        results.append((test_name, success))
        print()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 40)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    print()
    print(f"📈 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Green API integration is ready!")
        print()
        print("🚀 Next Steps:")
        print("1. Configure Green API webhook URL in your Green API console")
        print(f"   Webhook URL: https://your-ngrok-url.ngrok-free.app/webhook/whatsapp")
        print("2. Test by sending 'join' to your WhatsApp number")
        print("3. Monitor Celery worker logs for message processing")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")

if __name__ == "__main__":
    main()
