"""
Celery tasks for AI Beer Crawl App
Background task processing for WhatsApp integration and scheduled operations
"""

from celery import Celery
from datetime import datetime, timedelta
import requests
import os
import random
import redis
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import bot response manager and user state manager
from src.utils.bot_responses import get_bot_response
from src.utils.user_state import user_state_manager

# Redis connection for deduplication
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=1,  # Use db=1 for deduplication (separate from Celery queue)
    decode_responses=True
)

# Celery configuration
celery = Celery('beer_crawl_tasks')
celery.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# WhatsApp API configuration
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID')
WHATSAPP_API_URL = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"

# Green API configuration
GREEN_API_INSTANCE_ID = os.environ.get('GREEN_API_INSTANCE_ID')
GREEN_API_TOKEN = os.environ.get('GREEN_API_TOKEN')
USE_GREEN_API = bool(GREEN_API_INSTANCE_ID and GREEN_API_TOKEN)

API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')

# Deduplication configuration
MESSAGE_COOLDOWN = int(os.environ.get('MESSAGE_COOLDOWN', 30))  # seconds
USER_COOLDOWN = int(os.environ.get('USER_COOLDOWN', 10))  # seconds  
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 300))  # 5 minutes
RATE_LIMIT_MAX = int(os.environ.get('RATE_LIMIT_MAX', 5))  # max messages per window

# ============================================================================
# MESSAGE DEDUPLICATION HELPERS
# ============================================================================

def create_message_key(user_number, message_text, message_type):
    """Create a unique key for message deduplication"""
    # Normalize the message for comparison
    normalized = f"{user_number}:{message_type}:{message_text.strip().lower()}"
    return f"msg_dedupe:{hashlib.md5(normalized.encode()).hexdigest()}"

def is_duplicate_message(user_number, message_text, message_type, cooldown_seconds=None):
    """
    Check if this is a duplicate message within the cooldown period
    Returns True if duplicate, False if new/allowed
    """
    if cooldown_seconds is None:
        cooldown_seconds = MESSAGE_COOLDOWN
        
    try:
        message_key = create_message_key(user_number, message_text, message_type)
        
        # Check if this exact message was recently processed
        if redis_client.exists(message_key):
            print(f"🚫 Duplicate message from {user_number}: {message_text[:50]}...")
            return True
        
        # Also check for recent activity from this user (general cooldown)
        user_cooldown_key = f"user_cooldown:{user_number}"
        if redis_client.exists(user_cooldown_key):
            print(f"⏳ User {user_number} in cooldown period")
            return True
        
        # Mark this message as processed
        redis_client.setex(message_key, cooldown_seconds, "1")
        
        # Set user cooldown (shorter than message cooldown)
        redis_client.setex(user_cooldown_key, USER_COOLDOWN, "1")
        
        return False
        
    except Exception as e:
        print(f"❌ Error in deduplication check: {e}")
        # If Redis fails, allow the message to prevent blocking
        return False

def get_user_message_count(user_number, window_seconds=300):
    """Get count of messages from user in the last window_seconds"""
    try:
        count_key = f"msg_count:{user_number}"
        current_count = redis_client.get(count_key)
        return int(str(current_count)) if current_count else 0
    except:
        return 0

def increment_user_message_count(user_number, window_seconds=300):
    """Increment and return user message count"""
    try:
        count_key = f"msg_count:{user_number}"
        current_count = redis_client.incr(count_key)
        if current_count == 1:
            # Set expiration on first increment
            redis_client.expire(count_key, window_seconds)
        return int(str(current_count)) if current_count else 1
    except:
        return 1

def clear_user_deduplication(user_number):
    """Clear all deduplication data for a specific user (useful for testing)"""
    try:
        # Get all keys related to this user
        keys_to_delete = []
        
        # Message deduplication keys
        for key in redis_client.scan_iter(match=f"msg_dedupe:*{user_number}*"):
            keys_to_delete.append(key)
        
        # User cooldown key
        keys_to_delete.append(f"user_cooldown:{user_number}")
        
        # Message count key
        keys_to_delete.append(f"msg_count:{user_number}")
        
        # Delete all keys
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            print(f"🧹 Cleared {len(keys_to_delete)} deduplication keys for {user_number}")
            return len(keys_to_delete)
        return 0
    except Exception as e:
        print(f"❌ Error clearing deduplication for {user_number}: {e}")
        return 0

@celery.task
def clear_all_deduplication():
    """Clear all deduplication data (admin function)"""
    try:
        count = 0
        # Clear all deduplication-related keys
        for pattern in ["msg_dedupe:*", "user_cooldown:*", "msg_count:*"]:
            keys = list(redis_client.scan_iter(match=pattern))
            if keys:
                redis_client.delete(*keys)
                count += len(keys)
        
        print(f"🧹 Cleared {count} deduplication keys total")
        return {'status': 'success', 'cleared_keys': count}
    except Exception as e:
        print(f"❌ Error clearing all deduplication: {e}")
        return {'status': 'error', 'error': str(e)}

# ============================================================================
# WHATSAPP MESSAGE PROCESSING TASKS
# ============================================================================

@celery.task(bind=True, max_retries=3)
def process_whatsapp_message(self, message):
    """Process incoming WhatsApp message with deduplication"""
    try:
        user_number = message.get('from')
        message_text = message.get('text', {}).get('body', '').lower()
        message_type = message.get('type')
        
        print(f"📥 Received message from {user_number}: {message_text}")
        
        # Deduplication check
        if is_duplicate_message(user_number, message_text, message_type):
            print(f"🚫 Duplicate/cooldown - ignoring message from {user_number}")
            return {'status': 'ignored', 'reason': 'duplicate_or_cooldown'}
        
        # Rate limiting check
        message_count = increment_user_message_count(user_number, RATE_LIMIT_WINDOW)
        if message_count > RATE_LIMIT_MAX:  # Max messages per window
            print(f"🚨 Rate limit exceeded for {user_number} (count: {message_count})")
            send_whatsapp_message.delay(
                user_number,
                get_bot_response("rate_limit", minutes=RATE_LIMIT_WINDOW//60)
            )
            return {'status': 'rate_limited', 'count': message_count}
        
        print(f"✅ Processing message from {user_number}: {message_text}")
        
        if message_type == 'text':
            # Check if user is in signup flow
            user_state = user_state_manager.get_user_state(user_number)
            
            if user_state:
                # User is in signup flow - handle based on current state
                handle_signup_flow.delay(user_number, message_text, user_state)
            elif any(keyword in message_text for keyword in ['beer', 'crawl', 'join', 'sign up', 'signup']):
                # Start new signup flow
                start_signup_flow.delay(user_number)
            elif 'yes' in message_text:
                # User confirmed group participation
                confirm_group_participation.delay(user_number)
            elif "don't like this group" in message_text or "find another" in message_text:
                # User wants alternative group
                find_alternative_group.delay(user_number)
            elif 'help' in message_text:
                # Show help
                send_whatsapp_message.delay(
                    user_number,
                    get_bot_response("help")
                )
            else:
                # Default response
                send_whatsapp_message.delay(
                    user_number,
                    get_bot_response("welcome")
                )
    
    except Exception as exc:
        print(f"Error processing message: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery.task(bind=True, max_retries=3)
def start_signup_flow(self, whatsapp_number):
    """Start the signup flow for a new user"""
    try:
        # Check if user already exists
        response = requests.get(f'{API_BASE_URL}/api/user/{whatsapp_number}', timeout=30)
        
        if response.status_code == 200:
            # User exists - go directly to finding group
            find_group_task.delay(whatsapp_number)
            return {'status': 'existing_user', 'redirected_to_group_finding': True}
        
        # Start signup flow - collect area preference
        user_state_manager.set_user_state(
            whatsapp_number, 
            user_state_manager.STATES['COLLECTING_AREA']
        )
        
        areas = user_state_manager.get_formatted_areas()
        send_whatsapp_message.delay(
            whatsapp_number,
            get_bot_response("signup_start", areas=areas)
        )
        
        return {'status': 'signup_started'}
        
    except Exception as exc:
        print(f"Error starting signup flow: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery.task(bind=True, max_retries=3)
def handle_signup_flow(self, whatsapp_number, message_text, user_state):
    """Handle user responses during signup flow"""
    try:
        current_state = user_state.get('state')
        
        if current_state == user_state_manager.STATES['COLLECTING_AREA']:
            # Extract area from message
            area = user_state_manager.extract_area_from_message(message_text)
            
            if area:
                # Valid area - update state and ask for group type
                user_state_manager.update_user_data(whatsapp_number, 'preferred_area', area)
                user_state_manager.set_user_state(
                    whatsapp_number, 
                    user_state_manager.STATES['COLLECTING_GROUP_TYPE'],
                    user_state.get('data', {})
                )
                
                group_types = user_state_manager.get_formatted_group_types()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_group_type", group_types=group_types)
                )
            else:
                # Invalid area - ask again
                areas = user_state_manager.get_formatted_areas()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_area_invalid", areas=areas)
                )
        
        elif current_state == user_state_manager.STATES['COLLECTING_GROUP_TYPE']:
            # Extract group type from message
            group_type = user_state_manager.extract_group_type_from_message(message_text)
            
            if group_type:
                # Valid group type - update state and ask for gender
                user_state_manager.update_user_data(whatsapp_number, 'preferred_group_type', group_type)
                user_state_manager.set_user_state(
                    whatsapp_number, 
                    user_state_manager.STATES['COLLECTING_GENDER'],
                    user_state.get('data', {})
                )
                
                genders = user_state_manager.get_formatted_genders()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_gender", genders=genders)
                )
            else:
                # Invalid group type - ask again
                group_types = user_state_manager.get_formatted_group_types()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_group_type_invalid", group_types=group_types)
                )
        
        elif current_state == user_state_manager.STATES['COLLECTING_GENDER']:
            # Extract gender from message
            gender = user_state_manager.extract_gender_from_message(message_text)
            
            if gender:
                # Valid gender - update state and ask for age
                user_state_manager.update_user_data(whatsapp_number, 'gender', gender)
                user_state_manager.set_user_state(
                    whatsapp_number, 
                    user_state_manager.STATES['COLLECTING_AGE'],
                    user_state.get('data', {})
                )
                
                age_ranges = user_state_manager.get_formatted_age_ranges()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_age", age_ranges=age_ranges)
                )
            else:
                # Invalid gender - ask again
                genders = user_state_manager.get_formatted_genders()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_gender_invalid", genders=genders)
                )
        
        elif current_state == user_state_manager.STATES['COLLECTING_AGE']:
            # Extract age range from message
            age_range = user_state_manager.extract_age_range_from_message(message_text)
            
            if age_range:
                # Valid age range - complete signup
                user_state_manager.update_user_data(whatsapp_number, 'age_range', age_range)
                user_state_manager.set_user_state(
                    whatsapp_number, 
                    user_state_manager.STATES['COMPLETED'],
                    user_state.get('data', {})
                )
                
                # Complete the registration
                complete_user_registration.delay(whatsapp_number)
            else:
                # Invalid age range - ask again
                age_ranges = user_state_manager.get_formatted_age_ranges()
                send_whatsapp_message.delay(
                    whatsapp_number,
                    get_bot_response("signup_age_invalid", age_ranges=age_ranges)
                )
        
        return {'status': 'processed', 'state': current_state}
        
    except Exception as exc:
        print(f"Error handling signup flow: {str(exc)}")
        # Clear user state on error
        user_state_manager.clear_user_state(whatsapp_number)
        send_whatsapp_message.delay(
            whatsapp_number,
            get_bot_response("error")
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery.task(bind=True, max_retries=3) 
def complete_user_registration(self, whatsapp_number):
    """Complete user registration with collected data"""
    try:
        # Get completed signup data
        signup_data = user_state_manager.get_signup_completion_data(whatsapp_number)
        
        if not signup_data:
            send_whatsapp_message.delay(
                whatsapp_number,
                get_bot_response("signup_timeout")
            )
            return {'status': 'error', 'reason': 'no_signup_data'}
        
        # Register user via API
        user_data = {
            'whatsapp_number': whatsapp_number,
            'preferred_area': signup_data.get('preferred_area'),
            'preferred_group_type': signup_data.get('preferred_group_type', 'mixed'),
            'gender': signup_data.get('gender'),
            'age_range': signup_data.get('age_range')
        }
        
        response = requests.post(f'{API_BASE_URL}/api/beer-crawl/signup', 
                               json=user_data, timeout=30)
        
        if response.status_code == 201:
            # User registered successfully
            send_whatsapp_message.delay(
                whatsapp_number,
                get_bot_response("signup_success", 
                    area=signup_data.get('preferred_area', '').title(),
                    group_type=signup_data.get('preferred_group_type', '').title(),
                    gender=signup_data.get('gender', '').title(),
                    age_range=signup_data.get('age_range', '')
                )
            )
            
            # Clear signup state
            user_state_manager.clear_user_state(whatsapp_number)
            
            # Find group for user
            find_group_task.delay(whatsapp_number)
            
        elif response.status_code == 400:
            # User might already exist, try finding group anyway
            user_state_manager.clear_user_state(whatsapp_number)
            find_group_task.delay(whatsapp_number)
        else:
            send_whatsapp_message.delay(
                whatsapp_number,
                get_bot_response("error")
            )
            user_state_manager.clear_user_state(whatsapp_number)
    
    except requests.RequestException as exc:
        print(f"Error completing user registration: {str(exc)}")
        user_state_manager.clear_user_state(whatsapp_number)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        print(f"Error completing user registration: {str(exc)}")
        user_state_manager.clear_user_state(whatsapp_number)
        send_whatsapp_message.delay(
            whatsapp_number,
            get_bot_response("error")
        )

@celery.task(bind=True, max_retries=3)
def find_group_task(self, whatsapp_number):
    """Find or create group for user"""
    try:
        # Find group via API
        response = requests.post(f'{API_BASE_URL}/api/beer-crawl/find-group',
                               json={'whatsapp_number': whatsapp_number}, 
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            group = data['group']
            ready_to_start = data.get('ready_to_start', False)
            
            if ready_to_start:
                # Group has enough members
                message = f"🍺 Found {group['current_members']} people looking to go out in {group['area']} at 4pm. Shall I make a WhatsApp group for you all?"
                send_whatsapp_message.delay(whatsapp_number, message)
                
                # Store group confirmation pending
                store_pending_confirmation.delay(whatsapp_number, group['id'])
            else:
                # Still waiting for more members
                needed = group['max_members'] - group['current_members']
                message = f"Finding a group for you in {group['area']}. Currently {group['current_members']} members waiting. Need {needed} more to start!"
                send_whatsapp_message.delay(whatsapp_number, message)
                
                # Check again in 5 minutes
                find_group_task.apply_async(args=[whatsapp_number], countdown=300)
        
        elif response.status_code == 201:
            # New group created
            data = response.json()
            group = data['group']
            message = f"Created a new group for {group['area']}! Looking for {group['max_members'] - 1} more people to join. I'll let you know when we're ready!"
            send_whatsapp_message.delay(whatsapp_number, message)
            
            # Check again in 5 minutes
            find_group_task.apply_async(args=[whatsapp_number], countdown=300)
        else:
            send_whatsapp_message.delay(
                whatsapp_number,
                "Sorry, couldn't find or create a group right now. Please try again later."
            )
    
    except requests.RequestException as exc:
        print(f"Error finding group: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        print(f"Error finding group: {str(exc)}")

@celery.task(bind=True, max_retries=3)
def confirm_group_participation(self, whatsapp_number):
    """Handle group participation confirmation"""
    try:
        # Get pending confirmation
        group_id = get_pending_confirmation(whatsapp_number)
        
        if group_id:
            # Start the group
            response = requests.post(f'{API_BASE_URL}/api/beer-crawl/groups/{group_id}/start',
                                   timeout=30)
            
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
        else:
            send_whatsapp_message.delay(whatsapp_number, "No pending group confirmation found.")
    
    except requests.RequestException as exc:
        print(f"Error confirming participation: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        print(f"Error confirming participation: {str(exc)}")

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
    
    except Exception as exc:
        print(f"Error finding alternative group: {str(exc)}")

# ============================================================================
# GROUP MANAGEMENT TASKS
# ============================================================================

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
    
    if not bar:
        send_whatsapp_message.delay(whatsapp_group_id, "Sorry, no bar information available.")
        return
    
    message = f"""🍺 First Bar! Vote for your preferred starting location:

📍 {bar['name']} - {bar['address']}

⏰ Meeting time: {meeting_time if meeting_time else 'TBD'}
🗺️ Map: {map_link if map_link else 'Location details coming soon'}

See you there! 🍻"""
    
    send_whatsapp_message.delay(whatsapp_group_id, message)

@celery.task(bind=True, max_retries=3)
def schedule_bar_progression(self, group_id, delay_seconds):
    """Schedule progression to next bar"""
    try:
        progress_to_next_bar.apply_async(args=[group_id], countdown=delay_seconds)
    except Exception as exc:
        print(f"Error scheduling bar progression: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)

@celery.task(bind=True, max_retries=3)
def progress_to_next_bar(self, group_id):
    """Move group to next bar"""
    try:
        response = requests.post(f'{API_BASE_URL}/api/beer-crawl/groups/{group_id}/next-bar',
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'bar' in data:
                # Moving to next bar
                bar = data['bar']
                meeting_time = data['meeting_time']
                map_link = data['map_link']
                
                # Get group info to send message
                group_response = requests.get(f'{API_BASE_URL}/api/beer-crawl/groups/{group_id}/status',
                                            timeout=30)
                
                if group_response.status_code == 200:
                    group_data = group_response.json()
                    whatsapp_group_id = group_data['group'].get('whatsapp_group_id')
                    
                    if whatsapp_group_id:
                        message = f"""🍻 Time for the next bar!

📍 {bar['name']} - {bar['address']}

⏰ Meeting time: {meeting_time}
🗺️ Map: {map_link if map_link else 'Getting directions...'}

See you there in 15 minutes! 🚶‍♂️🚶‍♀️"""
                        
                        send_whatsapp_message.delay(whatsapp_group_id, message)
                        
                        # Check if we should continue or end
                        current_hour = datetime.now().hour
                        if current_hour < 23:  # Continue until 11 PM
                            schedule_bar_progression.delay(group_id, 3600)  # Next bar in 1 hour
                        else:
                            # Schedule end of session
                            end_group_session.apply_async(args=[group_id], countdown=3600)
            else:
                # Crawl completed
                end_group_session.delay(group_id)
                
    except requests.RequestException as exc:
        print(f"Error progressing to next bar: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        print(f"Error progressing to next bar: {str(exc)}")

@celery.task(bind=True, max_retries=3)
def end_group_session(self, group_id):
    """End group session"""
    try:
        # Get group info
        response = requests.get(f'{API_BASE_URL}/api/beer-crawl/groups/{group_id}/status',
                              timeout=30)
        
        if response.status_code == 200:
            group_data = response.json()
            whatsapp_group_id = group_data['group'].get('whatsapp_group_id')
            
            if whatsapp_group_id:
                # Send end message
                end_message = "🌙 It's getting late! The group will be automatically deleted at 6am. Thanks for joining the AI Beer Crawl tonight!"
                send_whatsapp_message.delay(whatsapp_group_id, end_message)
        
        # End the group
        requests.post(f'{API_BASE_URL}/api/beer-crawl/groups/{group_id}/end', timeout=30)
    
    except requests.RequestException as exc:
        print(f"Error ending group session: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        print(f"Error ending group session: {str(exc)}")

# ============================================================================
# WHATSAPP COMMUNICATION TASKS
# ============================================================================

@celery.task(bind=True, max_retries=3)
def send_whatsapp_message(self, to, message):
    """Send WhatsApp message using Green API"""
    try:
        # Try Green API first if configured
        if USE_GREEN_API:
            from src.integrations.green_api import green_api_client
            result = green_api_client.send_message(to, message)
            
            if result.get('error'):
                print(f"Green API error sending to {to}: {result.get('error')}")
                raise requests.RequestException(f"Green API error: {result.get('error')}")
            else:
                print(f"Green API message sent to {to}: {message[:50]}...")
                return result
        
        # Fallback to Facebook WhatsApp Business API
        elif WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
            headers = {
                'Authorization': f'Bearer {WHATSAPP_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'to': to,
                'text': {'body': message}
            }
            
            response = requests.post(WHATSAPP_API_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                print(f"Facebook API message sent to {to}: {message[:50]}...")
                return response.json()
            else:
                print(f"Failed to send message via Facebook API: {response.text}")
                if response.status_code >= 400:
                    raise requests.RequestException(f"WhatsApp API error: {response.status_code}")
        
        else:
            print(f"WhatsApp not configured. Would send to {to}: {message[:50]}...")
            return
    
    except requests.RequestException as exc:
        print(f"Error sending WhatsApp message: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        print(f"Error sending WhatsApp message: {str(exc)}")

# ============================================================================
# SCHEDULED MAINTENANCE TASKS
# ============================================================================

@celery.task(bind=True, max_retries=2)
def daily_cleanup(self):
    """Daily cleanup of completed groups at 6 AM"""
    try:
        response = requests.get(f'{API_BASE_URL}/api/beer-crawl/groups?status=active', timeout=30)
        
        if response.status_code == 200:
            active_groups = response.json()
            
            for group in active_groups:
                whatsapp_group_id = group.get('whatsapp_group_id')
                if whatsapp_group_id:
                    # Send goodbye message
                    goodbye_message = "Good morning! Hope you had a great night out. The group will be deleted now. Thanks for using AI Beer Crawl! 🍺"
                    send_whatsapp_message.delay(whatsapp_group_id, goodbye_message)
                
                # End the group
                requests.post(f'{API_BASE_URL}/api/beer-crawl/groups/{group["id"]}/end', timeout=30)
    
    except requests.RequestException as exc:
        print(f"Error in daily cleanup: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)  # Retry in 5 minutes
    except Exception as exc:
        print(f"Error in daily cleanup: {str(exc)}")

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
    # For now, we'll use a simple in-memory store (replace with Redis)
    pass

def get_pending_confirmation(whatsapp_number):
    """Get pending group confirmation"""
    # In real implementation, retrieve from Redis or database
    # For now, return a dummy group ID (replace with Redis lookup)
    return 1

# ============================================================================
# PERIODIC TASKS SETUP
# ============================================================================

from celery.schedules import crontab

celery.conf.beat_schedule = {
    'daily-cleanup': {
        'task': 'src.tasks.celery_tasks.daily_cleanup',
        'schedule': crontab(hour='6', minute='0'),  # Run at 6:00 AM daily
    },
}

if __name__ == '__main__':
    print("Starting Celery worker...")
    print("Run this worker with: celery -A src.tasks.celery_tasks.celery worker --loglevel=info")
    print("Run beat scheduler with: celery -A src.tasks.celery_tasks.celery beat --loglevel=info")
