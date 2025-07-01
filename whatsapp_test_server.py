#!/usr/bin/env python3
"""
WhatsApp Bot Testing Server with ngrok integration
This server helps test WhatsApp webhook integration with live messaging
"""
import sys
import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from flask import Flask, request, jsonify, render_template_string
from src.utils.error_handling import setup_error_handlers, configure_logging
from src.tasks.celery_tasks import process_whatsapp_message

def create_whatsapp_test_app():
    """Create Flask app for WhatsApp testing"""
    app = Flask(__name__)
    app.config['DEBUG'] = True
    app.config['TESTING'] = False
    
    # Setup error handling
    configure_logging(app)
    setup_error_handlers(app)
    
    # Store received messages for debugging
    received_messages = []
    
    @app.route('/')
    def dashboard():
        """WhatsApp Testing Dashboard"""
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>🤖 WhatsApp Bot Testing Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5em; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .status-card {
            background: rgba(255, 255, 255, 0.2);
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #4CAF50;
        }
        .webhook-url {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-family: monospace;
            word-break: break-all;
        }
        .test-commands {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .message-log {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            border-radius: 10px;
            max-height: 400px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
        }
        .btn {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 5px;
        }
        .btn:hover { background: #45a049; }
        .refresh-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #FF9800;
        }
    </style>
    <script>
        function refreshMessages() {
            fetch('/api/messages')
                .then(response => response.json())
                .then(data => {
                    const log = document.getElementById('messageLog');
                    log.innerHTML = data.messages.map(msg => 
                        `<div>[${msg.timestamp}] ${msg.content}</div>`
                    ).join('');
                    log.scrollTop = log.scrollHeight;
                });
        }
        
        function testWebhook() {
            fetch('/test/webhook', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    "object": "whatsapp_business_account",
                    "entry": [{
                        "id": "test",
                        "changes": [{
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "test"},
                                "messages": [{
                                    "id": "test_msg_001",
                                    "from": "+1234567890",
                                    "timestamp": Math.floor(Date.now() / 1000),
                                    "text": {"body": "join"},
                                    "type": "text"
                                }]
                            },
                            "field": "messages"
                        }]
                    }]
                })
            })
            .then(response => response.json())
            .then(data => {
                alert('Test message sent! Check the message log below.');
                refreshMessages();
            });
        }
        
        setInterval(refreshMessages, 5000); // Refresh every 5 seconds
        window.onload = refreshMessages;
    </script>
</head>
<body>
    <button class="btn refresh-btn" onclick="refreshMessages()">🔄 Refresh</button>
    
    <div class="container">
        <h1>🤖 WhatsApp Bot Testing Dashboard</h1>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>📡 Webhook Status</h3>
                <p><strong>Server:</strong> ✅ Running</p>
                <p><strong>Port:</strong> 5000</p>
                <p><strong>Environment:</strong> Testing</p>
            </div>
            
            <div class="status-card">
                <h3>🔗 ngrok Integration</h3>
                <p><strong>Status:</strong> Ready for ngrok</p>
                <p><strong>Command:</strong> <code>ngrok http 5000</code></p>
                <p><strong>Webhook Path:</strong> <code>/webhook/whatsapp</code></p>
            </div>
            
            <div class="status-card">
                <h3>📱 WhatsApp Setup</h3>
                <p><strong>Business API:</strong> Configure webhook URL</p>
                <p><strong>Verify Token:</strong> beer_crawl_verify</p>
                <p><strong>Events:</strong> messages</p>
            </div>
        </div>
        
        <div class="webhook-url">
            <h3>🌐 Webhook URL (Update with your ngrok URL):</h3>
            <div>https://YOUR_NGROK_URL.ngrok.io/webhook/whatsapp</div>
            <small>Replace YOUR_NGROK_URL with the actual ngrok subdomain</small>
        </div>
        
        <div class="test-commands">
            <h3>🧪 Testing Commands</h3>
            <button class="btn" onclick="testWebhook()">📤 Send Test Message</button>
            <a href="/webhook/whatsapp?hub.verify_token=beer_crawl_verify&hub.challenge=test123" class="btn" target="_blank">🔍 Test Webhook Verification</a>
            <a href="/api/debug" class="btn" target="_blank">🐛 Debug Info</a>
        </div>
        
        <div>
            <h3>📝 Message Log</h3>
            <div id="messageLog" class="message-log">
                Loading messages...
            </div>
        </div>
    </div>
</body>
</html>
        """)
    
    @app.route('/webhook/whatsapp', methods=['GET', 'POST'])
    def whatsapp_webhook():
        """WhatsApp webhook endpoint with enhanced logging"""
        if request.method == 'GET':
            # Webhook verification
            verify_token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            
            app.logger.info(f"Webhook verification attempt: token={verify_token}, challenge={challenge}")
            
            expected_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'beer_crawl_verify')
            
            if verify_token == expected_token:
                app.logger.info("✅ Webhook verification successful")
                received_messages.append({
                    'timestamp': datetime.now().isoformat(),
                    'content': f"✅ Webhook verified with token: {verify_token}"
                })
                return challenge
            else:
                app.logger.warning(f"❌ Webhook verification failed. Expected: {expected_token}, Got: {verify_token}")
                received_messages.append({
                    'timestamp': datetime.now().isoformat(),
                    'content': f"❌ Verification failed. Expected: {expected_token}, Got: {verify_token}"
                })
                return 'Invalid verify token', 403
        
        elif request.method == 'POST':
            # Handle incoming WhatsApp message
            try:
                data = request.get_json()
                app.logger.info(f"📱 Received WhatsApp webhook: {json.dumps(data, indent=2)}")
                
                # Log the message for debugging
                received_messages.append({
                    'timestamp': datetime.now().isoformat(),
                    'content': f"📱 WhatsApp Message: {json.dumps(data, indent=2)}"
                })
                
                # Process message with Celery (if available)
                try:
                    # Check if message contains actual content
                    if 'entry' in data and data['entry']:
                        for entry in data['entry']:
                            if 'changes' in entry:
                                for change in entry['changes']:
                                    if 'value' in change and 'messages' in change['value']:
                                        messages = change['value']['messages']
                                        for message in messages:
                                            phone = message.get('from', 'unknown')
                                            text = message.get('text', {}).get('body', '')
                                            
                                            app.logger.info(f"Processing message from {phone}: '{text}'")
                                            received_messages.append({
                                                'timestamp': datetime.now().isoformat(),
                                                'content': f"🔄 Processing: {phone} -> '{text}'"
                                            })
                                            
                                            # Simulate processing
                                            if text.lower() in ['join', 'beer', 'crawl']:
                                                response_msg = f"🍺 Hey there! Welcome to AI Beer Crawl! We received your '{text}' message."
                                                app.logger.info(f"Would send response: {response_msg}")
                                                received_messages.append({
                                                    'timestamp': datetime.now().isoformat(),
                                                    'content': f"📤 Would respond: {response_msg}"
                                                })
                    
                    # Try to process with Celery
                    process_whatsapp_message.delay(data)
                    app.logger.info("✅ Message queued for Celery processing")
                    
                except Exception as celery_error:
                    app.logger.warning(f"⚠️ Celery not available: {celery_error}")
                    received_messages.append({
                        'timestamp': datetime.now().isoformat(),
                        'content': f"⚠️ Celery processing failed: {celery_error}"
                    })
                
                return jsonify({'status': 'received'}), 200
            
            except Exception as e:
                app.logger.error(f"💥 Error processing WhatsApp webhook: {e}")
                received_messages.append({
                    'timestamp': datetime.now().isoformat(),
                    'content': f"💥 Error: {e}"
                })
                return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/test/webhook', methods=['POST'])
    def test_webhook():
        """Test endpoint to simulate WhatsApp message"""
        data = request.get_json()
        app.logger.info(f"🧪 Test webhook called with: {json.dumps(data, indent=2)}")
        
        # Forward to actual webhook
        from flask import current_app
        with current_app.test_request_context('/webhook/whatsapp', method='POST', json=data):
            return whatsapp_webhook()
    
    @app.route('/api/messages')
    def get_messages():
        """Get received messages for the dashboard"""
        return jsonify({
            'messages': received_messages[-50:],  # Last 50 messages
            'count': len(received_messages)
        })
    
    @app.route('/api/debug')
    def debug_info():
        """Debug information endpoint"""
        return jsonify({
            'environment': {
                'WHATSAPP_WEBHOOK_VERIFY_TOKEN': os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'beer_crawl_verify'),
                'CELERY_BROKER_URL': os.getenv('CELERY_BROKER_URL', 'not set'),
                'REDIS_URL': os.getenv('REDIS_URL', 'not set'),
            },
            'server_info': {
                'debug': app.config['DEBUG'],
                'testing': app.config['TESTING'],
                'python_path': sys.path[:3],
            },
            'recent_messages': received_messages[-10:],
            'total_messages': len(received_messages)
        })
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'whatsapp-bot-test',
            'timestamp': datetime.now().isoformat(),
            'messages_received': len(received_messages)
        })
    
    return app

if __name__ == '__main__':
    print("🤖 Starting WhatsApp Bot Testing Server")
    print("=" * 50)
    
    app = create_whatsapp_test_app()
    
    print("✅ WhatsApp webhook configured")
    print("✅ Testing dashboard ready")
    print("✅ Debug endpoints available")
    print("\n🌐 Server starting at: http://localhost:5000")
    print("📱 Webhook URL: http://localhost:5000/webhook/whatsapp")
    print("🎛️ Dashboard: http://localhost:5000")
    print("\n🔗 To expose with ngrok:")
    print("   1. Run: ngrok http 5000")
    print("   2. Copy the https://xxx.ngrok.io URL")
    print("   3. Set WhatsApp webhook to: https://xxx.ngrok.io/webhook/whatsapp")
    print("   4. Use verify token: beer_crawl_verify")
    print("\n🔧 Use Ctrl+C to stop the server\n")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 WhatsApp testing server stopped!")
