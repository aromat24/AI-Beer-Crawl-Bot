#!/usr/bin/env python3
"""
WhatsApp Webhook Debugger
Monitor and debug incoming WhatsApp webhooks from Green API
"""
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

app = Flask(__name__)

# Store recent webhooks for debugging
recent_webhooks = []
MAX_STORED_WEBHOOKS = 50

@app.route('/webhook/debug', methods=['GET', 'POST'])
def debug_webhook():
    """Debug webhook endpoint - logs all incoming requests"""
    timestamp = datetime.utcnow().isoformat()
    
    webhook_data = {
        'timestamp': timestamp,
        'method': request.method,
        'headers': dict(request.headers),
        'args': dict(request.args),
        'json': request.get_json() if request.is_json else None,
        'data': request.get_data(as_text=True) if request.data else None,
        'form': dict(request.form) if request.form else None
    }
    
    # Store webhook
    recent_webhooks.append(webhook_data)
    if len(recent_webhooks) > MAX_STORED_WEBHOOKS:
        recent_webhooks.pop(0)
    
    # Log to console
    print(f"\n🔍 WEBHOOK DEBUG [{timestamp}]")
    print("=" * 60)
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {json.dumps(dict(request.headers), indent=2)}")
    
    if request.is_json:
        print(f"JSON Data: {json.dumps(request.get_json(), indent=2)}")
    elif request.data:
        print(f"Raw Data: {request.get_data(as_text=True)}")
    elif request.form:
        print(f"Form Data: {json.dumps(dict(request.form), indent=2)}")
    
    print("=" * 60)
    
    # Try to process as Green API webhook
    if request.method == 'POST' and request.is_json:
        try:
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()
            
            print("🔄 Attempting to process webhook...")
            
            from src.integrations.green_api import process_green_api_webhook
            data = request.get_json()
            
            print(f"📥 Webhook data type: {data.get('typeWebhook')}")
            print(f"📥 Message type: {data.get('messageData', {}).get('typeMessage')}")
            
            processed = process_green_api_webhook(data)
            print(f"🔄 Processing result: {processed}")
            
            if processed:
                print(f"✅ Processed Green API message:")
                print(f"   From: {processed.get('from')}")
                print(f"   Text: {processed.get('text', {}).get('body')}")
                print(f"   Type: {processed.get('type')}")
                
                # Trigger processing
                print("🚀 Triggering Celery task...")
                from src.tasks.celery_tasks import process_whatsapp_message
                task = process_whatsapp_message.delay(processed)
                print(f"   ✅ Task created with ID: {task.id}")
                
                return jsonify({
                    'status': 'processed',
                    'processed_message': processed,
                    'task_id': task.id
                })
            else:
                print("❌ Failed to process as Green API webhook")
                print(f"   Raw data: {json.dumps(data, indent=2)}")
                
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
    
    return jsonify({'status': 'received', 'timestamp': timestamp})

@app.route('/webhook/recent')
def recent_webhooks_view():
    """View recent webhooks"""
    return jsonify({
        'total_webhooks': len(recent_webhooks),
        'recent_webhooks': recent_webhooks[-10:],  # Last 10
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/webhook/clear')
def clear_webhooks():
    """Clear stored webhooks"""
    global recent_webhooks
    count = len(recent_webhooks)
    recent_webhooks.clear()
    return jsonify({
        'message': f'Cleared {count} stored webhooks',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/test/green-api-status')
def green_api_status():
    """Check Green API status and configuration"""
    try:
        from src.integrations.green_api import green_api_client
        
        # Get current status
        state = green_api_client.get_state_instance()
        settings = green_api_client.get_account_settings()
        
        return jsonify({
            'configured': green_api_client.configured,
            'instance_id': green_api_client.instance_id,
            'phone_number': green_api_client.phone_number,
            'base_url': green_api_client.base_url,
            'instance_state': state,
            'account_settings': settings,
            'webhook_url_in_green_api': settings.get('webhookUrl', 'Not set'),
            'expected_webhook_url': request.url_root + 'webhook/whatsapp'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/test/send-join')
def test_send_join():
    """Simulate sending a join message"""
    try:
        # Create a fake Green API webhook for "join" message
        fake_webhook = {
            "typeWebhook": "incomingMessageReceived",
            "instanceData": {
                "idInstance": 7105273198,
                "wid": "66955124860@c.us",
                "typeInstance": "whatsapp"
            },
            "timestamp": int(time.time()),
            "idMessage": f"TEST_{int(time.time())}",
            "senderData": {
                "chatId": "66955124860@c.us",  # Your own number
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
        
        print(f"\n🧪 SIMULATING JOIN MESSAGE")
        print("=" * 40)
        print(json.dumps(fake_webhook, indent=2))
        
        # Process the fake webhook
        from src.integrations.green_api import process_green_api_webhook
        processed = process_green_api_webhook(fake_webhook)
        
        if processed:
            print(f"✅ Processed message: {processed}")
            
            # Trigger Celery task
            from src.tasks.celery_tasks import process_whatsapp_message
            task = process_whatsapp_message.delay(processed)
            
            return jsonify({
                'status': 'success',
                'simulated_webhook': fake_webhook,
                'processed_message': processed,
                'task_id': task.id
            })
        else:
            return jsonify({
                'status': 'failed',
                'error': 'Failed to process simulated webhook'
            })
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

@app.route('/webhook/catch-all', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def catch_all_webhook():
    """Catch all webhook endpoint to see any incoming traffic"""
    timestamp = datetime.utcnow().isoformat()
    
    print(f"\n🎯 CATCH-ALL WEBHOOK [{timestamp}]")
    print("=" * 60)
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Path: {request.path}")
    print(f"Headers: {json.dumps(dict(request.headers), indent=2)}")
    
    if request.is_json:
        print(f"JSON Data: {json.dumps(request.get_json(), indent=2)}")
    elif request.data:
        print(f"Raw Data: {request.get_data(as_text=True)}")
    elif request.form:
        print(f"Form Data: {json.dumps(dict(request.form), indent=2)}")
    
    print("=" * 60)
    
    return jsonify({
        'status': 'caught',
        'timestamp': timestamp,
        'method': request.method,
        'path': request.path
    })

@app.route('/')
def index():
    """Debug dashboard"""
    return f"""
    <h1>🔍 WhatsApp Webhook Debugger</h1>
    <h2>Debug Endpoints:</h2>
    <ul>
        <li><a href="/webhook/recent">Recent Webhooks</a></li>
        <li><a href="/webhook/clear">Clear Webhooks</a></li>
        <li><a href="/test/green-api-status">Green API Status</a></li>
        <li><a href="/test/send-join">Test Join Message</a></li>
    </ul>
    
    <h2>Webhook URLs:</h2>
    <ul>
        <li><strong>Debug Webhook:</strong> {request.url_root}webhook/debug</li>
        <li><strong>Main Webhook:</strong> {request.url_root}webhook/whatsapp</li>
    </ul>
    
    <h2>Instructions:</h2>
    <ol>
        <li>Set your Green API webhook URL to: <code>{request.url_root}webhook/debug</code></li>
        <li>Send a message to your WhatsApp number</li>
        <li>Check <a href="/webhook/recent">Recent Webhooks</a> to see the data</li>
        <li>Use <a href="/test/send-join">Test Join Message</a> to simulate the flow</li>
    </ol>
    
    <p><em>Last updated: {datetime.utcnow().isoformat()}</em></p>
    """

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🔍 Starting WhatsApp Webhook Debugger")
    print("=" * 50)
    print("This tool will help debug WhatsApp webhook issues.")
    print("Set your Green API webhook URL to include '/webhook/debug'")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
