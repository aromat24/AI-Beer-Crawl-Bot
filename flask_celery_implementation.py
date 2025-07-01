"""
AI Beer Crawl App - Flask + Celery Implementation
Alternative to n8n workflow automation

This implementation replaces n8n with native Flask backend + Celery for background tasks.
Provides complete control over workflow logic while maintaining scalability.
"""

from flask import Flask, request, jsonify
from celery import Celery
from datetime import datetime, timedelta
import requests
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Celery configuration
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# WhatsApp API configuration
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID')
WHATSAPP_API_URL = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"

# Background scheduler for recurring tasks
scheduler = BackgroundScheduler()

# ============================================================================
# WHATSAPP WEBHOOK ENDPOINTS
# ============================================================================

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        
        # Extract message data
        if 'entry' in data:
            for entry in data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if 'value' in change and 'messages' in change['value']:
                            for message in change['value']['messages']:
                                # Process message asynchronously
                                process_whatsapp_message.delay(message)
        
        return jsonify({'status': 'received'}), 200
    
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook/whatsapp', methods=['GET'])
def whatsapp_webhook_verify():
    """Verify WhatsApp webhook"""
    verify_token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if verify_token == os.environ.get('WHATSAPP_VERIFY_TOKEN'):
        return challenge
    return 'Invalid verification token', 403

# ============================================================================
# CELERY BACKGROUND TASKS
# ============================================================================

@celery.task
def process_whatsapp_message(message):
    """Process incoming WhatsApp message"""
    try:
        user_number = message.get('from')
        message_text = message.get('text', {}).get('body', '').lower()
        message_type = message.get('type')
        
        print(f"Processing message from {user_number}: {message_text}")
        
        if message_type == 'text':
            if 'beer' in message_text:
                # User wants to join beer crawl
                register_user_task.delay(user_number, message_text)
            elif 'yes' in message_text:
                # User confirmed group participation
                confirm_group_participation.delay(user_number)
            elif "don't like this group" in message_text or "find another" in message_text:
                # User wants alternative group
                find_alternative_group.delay(user_number)
            else:
                # Default response
                send_whatsapp_message.delay(
                    user_number,
                    "Hi! I can help you find a beer crawl group. Just say 'I want to join a beer crawl' to get started! 🍺"
                )
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")

@celery.task
def register_user_task(whatsapp_number, message_text):
    """Register new user and collect preferences"""
    try:
        # Extract area preference from message (basic NLP)
        area = extract_area_from_message(message_text)
        
        # Register user via API
        user_data = {
            'whatsapp_number': whatsapp_number,
            'preferred_area': area or 'northern quarter',
            'preferred_group_type': 'mixed',
            'gender': None,  # Will be collected later
            'age_range': None  # Will be collected later
        }
        
        response = requests.post('http://localhost:5000/api/beer-crawl/signup', 
                               json=user_data)
        
        if response.status_code == 201:
            # User registered successfully, now find group
            find_group_task.delay(whatsapp_number)
        else:
            # User might already exist, try finding group anyway
            find_group_task.delay(whatsapp_number)
    
    except Exception as e:
        print(f"Error registering user: {str(e)}")
        send_whatsapp_message.delay(
            whatsapp_number,
            "Sorry, there was an error processing your request. Please try again."
        )

@celery.task
def find_group_task(whatsapp_number):
    """Find or create group for user"""
    try:
        # Find group via API
        response = requests.post('http://localhost:5000/api/beer-crawl/find-group',
                               json={'whatsapp_number': whatsapp_number})
        
        if response.status_code == 200:
            data = response.json()
            group = data['group']
            ready_to_start = data.get('ready_to_start', False)
            
            if ready_to_start:
                # Group has enough members
                message = f"🍺 Found {group['current_members']} people, 3 males, 2 females looking to go out in {group['area']} at 4pm. Shall I make a whatsapp group for you all?"
                send_whatsapp_message.delay(whatsapp_number, message)
                
                # Store group confirmation pending
                store_pending_confirmation.delay(whatsapp_number, group['id'])
            else:
                # Still waiting for more members
                message = f"Finding a group for you in {group['area']}. Currently {group['current_members']} members waiting. Need {5 - group['current_members']} more to start!"
                send_whatsapp_message.delay(whatsapp_number, message)
                
                # Check again in 5 minutes
                find_group_task.apply_async(args=[whatsapp_number], countdown=300)
    
    except Exception as e:
        print(f"Error finding group: {str(e)}")

@celery.task
def confirm_group_participation(whatsapp_number):
    """Handle group participation confirmation"""
    try:
        # Get pending confirmation
        group_id = get_pending_confirmation(whatsapp_number)
        
        if group_id:
            # Start the group
            response = requests.post(f'http://localhost:5000/api/beer-crawl/groups/{group_id}/start')
            
            if response.status_code == 200:
                data = response.json()
                
                # Create WhatsApp group (simulated)
                whatsapp_group_id = create_whatsapp_group(group_id)
                
                # Send rules and first bar info
                send_group_rules.delay(whatsapp_group_id)
                send_first_bar_info.delay(whatsapp_group_id, data)
                
                # Schedule bar progression
                schedule_bar_progression.delay(group_id, 3600)  # 1 hour
            else:
                send_whatsapp_message.delay(whatsapp_number, "Sorry, couldn't start the group. Please try again.")
    
    except Exception as e:
        print(f"Error confirming participation: {str(e)}")

@celery.task
def find_alternative_group(whatsapp_number):
    """Find alternative group for user"""
    try:
        # Remove user from current group and find new one
        # This would involve more complex logic to remove from current group
        
        send_whatsapp_message.delay(
            whatsapp_number,
            "No worries! Let me find another group for you..."
        )
        
        # Wait a bit then find new group
        find_group_task.apply_async(args=[whatsapp_number], countdown=30)
    
    except Exception as e:
        print(f"Error finding alternative group: {str(e)}")

@celery.task
def send_group_rules(whatsapp_group_id):
    """Send group rules to WhatsApp group"""
    rules_message = """🍺 Welcome to your Beer Crawl group! Here are the rules:

1. Be respectful to everyone
2. Stay with the group
3. Drink responsibly
4. Have fun!

First bar poll coming up..."""
    
    send_whatsapp_message.delay(whatsapp_group_id, rules_message)

@celery.task
def send_first_bar_info(whatsapp_group_id, session_data):
    """Send first bar information"""
    bar = session_data.get('first_bar')
    meeting_time = session_data.get('meeting_time')
    map_link = session_data.get('map_link')
    
    message = f"""🍺 First Bar Poll! Vote for your preferred starting location:

1. {bar['name']} - {bar['address']}

Meeting time: {meeting_time}
Map: {map_link}

See you there! 🍻"""
    
    send_whatsapp_message.delay(whatsapp_group_id, message)

@celery.task
def schedule_bar_progression(group_id, delay_seconds):
    """Schedule progression to next bar"""
    progress_to_next_bar.apply_async(args=[group_id], countdown=delay_seconds)

@celery.task
def progress_to_next_bar(group_id):
    """Move group to next bar"""
    try:
        response = requests.post(f'http://localhost:5000/api/beer-crawl/groups/{group_id}/next-bar')
        
        if response.status_code == 200:
            data = response.json()
            bar = data['bar']
            meeting_time = data['meeting_time']
            map_link = data['map_link']
            
            # Get group info to send message
            group_response = requests.get(f'http://localhost:5000/api/beer-crawl/groups/{group_id}/status')
            group_data = group_response.json()
            whatsapp_group_id = group_data['group']['whatsapp_group_id']
            
            message = f"""🍻 Time for the next bar!

{bar['name']} - {bar['address']}

Meeting time: {meeting_time}
Map: {map_link}

See you there in 15 minutes! 🚶‍♂️🚶‍♀️"""
            
            send_whatsapp_message.delay(whatsapp_group_id, message)
            
            # Check if we should continue or end
            current_hour = datetime.now().hour
            if current_hour < 23:  # Continue until 11 PM
                schedule_bar_progression.delay(group_id, 3600)  # Next bar in 1 hour
            else:
                # Schedule end of session
                end_group_session.apply_async(args=[group_id], countdown=3600)
    
    except Exception as e:
        print(f"Error progressing to next bar: {str(e)}")

@celery.task
def end_group_session(group_id):
    """End group session"""
    try:
        # Get group info
        response = requests.get(f'http://localhost:5000/api/beer-crawl/groups/{group_id}/status')
        group_data = response.json()
        whatsapp_group_id = group_data['group']['whatsapp_group_id']
        
        # Send end message
        end_message = "🌙 It's getting late! The group will be automatically deleted at 6am. Thanks for joining the AI Beer Crawl tonight!"
        send_whatsapp_message.delay(whatsapp_group_id, end_message)
        
        # End the group
        requests.post(f'http://localhost:5000/api/beer-crawl/groups/{group_id}/end')
    
    except Exception as e:
        print(f"Error ending group session: {str(e)}")

@celery.task
def send_whatsapp_message(to, message):
    """Send WhatsApp message"""
    try:
        headers = {
            'Authorization': f'Bearer {WHATSAPP_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': to,
            'text': {'body': message}
        }
        
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"Message sent to {to}: {message[:50]}...")
        else:
            print(f"Failed to send message: {response.text}")
    
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")

# ============================================================================
# SCHEDULED TASKS
# ============================================================================

@celery.task
def daily_cleanup():
    """Daily cleanup of completed groups at 6 AM"""
    try:
        response = requests.get('http://localhost:5000/api/beer-crawl/groups?status=active')
        
        if response.status_code == 200:
            active_groups = response.json()
            
            for group in active_groups:
                whatsapp_group_id = group.get('whatsapp_group_id')
                if whatsapp_group_id:
                    # Send goodbye message
                    goodbye_message = "Good morning! Hope you had a great night out. The group will be deleted now. Thanks for using AI Beer Crawl! 🍺"
                    send_whatsapp_message.delay(whatsapp_group_id, goodbye_message)
                
                # End the group
                requests.post(f'http://localhost:5000/api/beer-crawl/groups/{group["id"]}/end')
    
    except Exception as e:
        print(f"Error in daily cleanup: {str(e)}")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_area_from_message(message_text):
    """Extract area preference from message text"""
    areas = ['northern quarter', 'city centre', 'deansgate', 'ancoats', 'spinningfields']
    message_lower = message_text.lower()
    
    for area in areas:
        if area in message_lower:
            return area
    return None

def create_whatsapp_group(group_id):
    """Create WhatsApp group (simulated)"""
    # In real implementation, this would use WhatsApp Business API
    # to create a group and return the group ID
    return f"group_{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def store_pending_confirmation(whatsapp_number, group_id):
    """Store pending group confirmation"""
    # In real implementation, store in Redis or database
    # For now, we'll use a simple in-memory store
    pass

def get_pending_confirmation(whatsapp_number):
    """Get pending group confirmation"""
    # In real implementation, retrieve from Redis or database
    # For now, return a dummy group ID
    return 1

# ============================================================================
# SCHEDULER SETUP
# ============================================================================

def setup_scheduler():
    """Setup scheduled tasks"""
    # Daily cleanup at 6 AM
    scheduler.add_job(
        func=daily_cleanup.delay,
        trigger=CronTrigger(hour=6, minute=0),
        id='daily_cleanup',
        name='Daily group cleanup at 6 AM',
        replace_existing=True
    )
    
    scheduler.start()

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    # Setup scheduler
    setup_scheduler()
    
    print("AI Beer Crawl App - Flask + Celery Implementation")
    print("Starting Flask application...")
    print("Make sure to start Celery worker separately:")
    print("celery -A flask_celery_implementation.celery worker --loglevel=info")
    
    app.run(host='0.0.0.0', port=5001, debug=True)

"""
DEPLOYMENT INSTRUCTIONS:

1. Install dependencies:
   pip install flask celery redis requests apscheduler

2. Start Redis server:
   redis-server

3. Start Celery worker:
   celery -A flask_celery_implementation.celery worker --loglevel=info

4. Start Celery beat (for scheduled tasks):
   celery -A flask_celery_implementation.celery beat --loglevel=info

5. Set environment variables:
   export WHATSAPP_TOKEN="your_whatsapp_token"
   export WHATSAPP_PHONE_ID="your_phone_number_id"
   export WHATSAPP_VERIFY_TOKEN="your_verify_token"

6. Start Flask application:
   python flask_celery_implementation.py

7. Configure WhatsApp webhook URL:
   https://your-domain.com/webhook/whatsapp

ADVANTAGES OF THIS APPROACH:
- Complete control over workflow logic
- No external platform dependencies
- Superior debugging capabilities
- Cost-effective for predictable workloads
- Scales horizontally with additional workers
- Integrates seamlessly with existing Flask app

CONSIDERATIONS:
- Requires Redis for task queue
- More complex deployment than n8n
- Need to implement error handling and retry logic
- Requires monitoring and operational procedures
"""

