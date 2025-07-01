#!/usr/bin/env python3
"""
Test Celery tasks functionality
"""
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tasks.celery_tasks import send_whatsapp_message, process_whatsapp_message

def test_celery_tasks():
    """Test Celery task execution"""
    print("Testing Celery tasks...")
    
    # Test sending a WhatsApp message (will simulate since we don't have real tokens)
    print("1. Testing WhatsApp message sending...")
    task = send_whatsapp_message.delay("+1234567890", "Test message from Celery!")
    print(f"   Task ID: {task.id}")
    print(f"   Task status: {task.status}")
    
    # Test processing a WhatsApp message
    print("2. Testing WhatsApp message processing...")
    test_message = {
        'from': '+1234567890',
        'type': 'text',
        'text': {'body': 'I want to join a beer crawl in northern quarter'}
    }
    
    task = process_whatsapp_message.delay(test_message)
    print(f"   Task ID: {task.id}")
    print(f"   Task status: {task.status}")
    
    print("Celery tasks submitted successfully!")
    print("Check the Celery worker logs to see task execution.")

if __name__ == '__main__':
    test_celery_tasks()
