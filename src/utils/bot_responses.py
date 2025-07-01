"""
Bot Response Management System
Configurable responses for the WhatsApp bot
"""
import redis
import json
from typing import Dict, Any

# Redis connection for bot responses
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=2,  # Use db=2 for bot responses (separate from other Redis usage)
    decode_responses=True
)

class BotResponseManager:
    """Manage bot responses and messages"""
    
    DEFAULT_RESPONSES = {
        "welcome": "Hi! I can help you find a beer crawl group. Just say 'I want to join a beer crawl' to get started! 🍺",
        "signup_start": "🍺 Welcome to Beer Crawl! Let's get you set up.\n\nFirst, which area would you like to explore?\n\n{areas}\n\nJust type the area name!",
        "signup_area_invalid": "🤔 I don't recognize that area. Please choose from:\n\n{areas}",
        "signup_group_type": "Great choice! 🎯 Now, what type of group would you prefer?\n\n{group_types}\n\nJust type your preference!",
        "signup_group_type_invalid": "Please choose from these group types:\n\n{group_types}",
        "signup_gender": "Perfect! 👤 What's your gender? (This helps with group matching)\n\n{genders}\n\nOr just type your preference!",
        "signup_gender_invalid": "Please choose from:\n\n{genders}",
        "signup_age": "Almost done! 🎂 What's your age range?\n\n{age_ranges}\n\nJust type the range!",
        "signup_age_invalid": "Please choose from these age ranges:\n\n{age_ranges}",
        "signup_success": "🎉 Perfect! You're all set up!\n\n📋 Your preferences:\n• Area: {area}\n• Group type: {group_type}\n• Gender: {gender}\n• Age: {age_range}\n\nLet me find you a perfect group...",
        "signup_timeout": "⏰ Your signup session has timed out. Type 'join' to start again!",
        "group_found": "Great! I found a group for you in {area}. Your group has {member_count} members and will visit {bar_count} bars.",
        "group_full": "The group you requested is now full! Let me find you another one...",
        "no_groups_available": "No groups are currently available in your area. Would you like me to create a new one for you?",
        "creating_group": "Creating a new beer crawl group for you in {area}! 🍻",
        "group_ready": "Your group is ready! Meet at {bar_name} at {time}. Have fun! 🍺",
        "rate_limit": "⚠️ Please slow down! You're sending too many messages. Try again in {minutes} minutes.",
        "error": "Sorry, there was an error processing your request. Please try again.",
        "help": "I can help you:\n• Join a beer crawl: 'I want to join a beer crawl'\n• Find groups in specific areas\n• Create new groups\n\nJust tell me what you'd like to do! 🍺",
        "goodbye": "Thanks for using Beer Crawl! Have a great time! 🍻",
        "invalid_area": "I don't recognize that area. Available areas: Northern Quarter, City Centre, Deansgate, Ancoats, Spinningfields",
        "group_cancelled": "Your beer crawl has been cancelled. You can join another group anytime!",
        "reminder": "🍺 Reminder: Your beer crawl starts in 30 minutes at {bar_name}!",
        "next_bar": "Time to move to the next bar! 🚶‍♂️ Head to {bar_name} at {address}",
        "crawl_complete": "🎉 Beer crawl complete! Hope you had an amazing time! Rate your experience and share photos!"
    }
    
    def __init__(self):
        self._initialize_responses()
    
    def _initialize_responses(self):
        """Initialize default responses if not already set"""
        try:
            existing = redis_client.get('bot_responses')
            if not existing:
                self.save_responses(self.DEFAULT_RESPONSES)
                print("✅ Initialized default bot responses")
        except Exception as e:
            print(f"❌ Error initializing bot responses: {e}")
    
    def get_response(self, response_key: str, **kwargs) -> str:
        """Get a bot response by key with optional formatting"""
        try:
            responses = self.get_all_responses()
            template = responses.get(response_key, self.DEFAULT_RESPONSES.get(response_key, ""))
            
            if kwargs:
                return template.format(**kwargs)
            return template
        except Exception as e:
            print(f"❌ Error getting response '{response_key}': {e}")
            return self.DEFAULT_RESPONSES.get(response_key, "")
    
    def get_all_responses(self) -> Dict[str, str]:
        """Get all bot responses"""
        try:
            responses_json = redis_client.get('bot_responses')
            if responses_json:
                return json.loads(str(responses_json))
            return self.DEFAULT_RESPONSES
        except Exception as e:
            print(f"❌ Error getting all responses: {e}")
            return self.DEFAULT_RESPONSES
    
    def save_responses(self, responses: Dict[str, str]) -> bool:
        """Save bot responses to Redis"""
        try:
            redis_client.set('bot_responses', json.dumps(responses))
            print("✅ Bot responses saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error saving responses: {e}")
            return False
    
    def update_response(self, response_key: str, message: str) -> bool:
        """Update a single bot response"""
        try:
            responses = self.get_all_responses()
            responses[response_key] = message
            return self.save_responses(responses)
        except Exception as e:
            print(f"❌ Error updating response '{response_key}': {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset all responses to defaults"""
        return self.save_responses(self.DEFAULT_RESPONSES)
    
    def get_response_keys(self) -> list:
        """Get list of all response keys"""
        return list(self.get_all_responses().keys())

# Global instance
bot_response_manager = BotResponseManager()

def get_bot_response(response_key: str, **kwargs) -> str:
    """Convenience function to get bot responses"""
    return bot_response_manager.get_response(response_key, **kwargs)
