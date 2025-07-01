"""
User State Management System
Handles conversation flow and user registration states
"""
import redis
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Redis connection for user states
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=3,  # Use db=3 for user states (separate from other Redis usage)
    decode_responses=True
)

class UserStateManager:
    """Manage user conversation states and signup flow"""
    
    # Signup flow states
    STATES = {
        'NEW': 'new',
        'COLLECTING_AREA': 'collecting_area',
        'COLLECTING_GROUP_TYPE': 'collecting_group_type', 
        'COLLECTING_GENDER': 'collecting_gender',
        'COLLECTING_AGE': 'collecting_age',
        'COMPLETED': 'completed'
    }
    
    # Available areas
    AREAS = [
        'northern quarter',
        'city centre', 
        'deansgate',
        'ancoats',
        'spinningfields'
    ]
    
    # Group types
    GROUP_TYPES = [
        'mixed',
        'males only',
        'females only'
    ]
    
    # Age ranges
    AGE_RANGES = [
        '18-25',
        '26-35', 
        '36-45',
        '46+'
    ]
    
    # Gender options
    GENDER_OPTIONS = [
        'male',
        'female',
        'prefer not to say'
    ]
    
    def __init__(self):
        self.state_timeout = 1800  # 30 minutes timeout for incomplete signups
    
    def get_user_state(self, whatsapp_number: str) -> Optional[Dict[str, Any]]:
        """Get current user state"""
        try:
            state_json = redis_client.get(f"user_state:{whatsapp_number}")
            if state_json:
                state = json.loads(str(state_json))
                # Check if state has expired
                if 'created_at' in state:
                    created = datetime.fromisoformat(state['created_at'])
                    if datetime.now() - created > timedelta(seconds=self.state_timeout):
                        self.clear_user_state(whatsapp_number)
                        return None
                return state
            return None
        except Exception as e:
            print(f"❌ Error getting user state for {whatsapp_number}: {e}")
            return None
    
    def set_user_state(self, whatsapp_number: str, state: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Set user state with optional data"""
        try:
            state_data = {
                'state': state,
                'whatsapp_number': whatsapp_number,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'data': data or {}
            }
            
            redis_client.setex(
                f"user_state:{whatsapp_number}",
                self.state_timeout,
                json.dumps(state_data)
            )
            return True
        except Exception as e:
            print(f"❌ Error setting user state for {whatsapp_number}: {e}")
            return False
    
    def update_user_data(self, whatsapp_number: str, key: str, value: str) -> bool:
        """Update specific field in user state data"""
        try:
            state = self.get_user_state(whatsapp_number)
            if state:
                state['data'][key] = value
                state['updated_at'] = datetime.now().isoformat()
                
                redis_client.setex(
                    f"user_state:{whatsapp_number}",
                    self.state_timeout,
                    json.dumps(state)
                )
                return True
            return False
        except Exception as e:
            print(f"❌ Error updating user data for {whatsapp_number}: {e}")
            return False
    
    def clear_user_state(self, whatsapp_number: str) -> bool:
        """Clear user state"""
        try:
            redis_client.delete(f"user_state:{whatsapp_number}")
            return True
        except Exception as e:
            print(f"❌ Error clearing user state for {whatsapp_number}: {e}")
            return False
    
    def is_valid_area(self, area: str) -> bool:
        """Check if area is valid"""
        return area.lower() in self.AREAS
    
    def is_valid_group_type(self, group_type: str) -> bool:
        """Check if group type is valid"""
        return group_type.lower() in self.GROUP_TYPES
    
    def is_valid_gender(self, gender: str) -> bool:
        """Check if gender is valid"""
        return gender.lower() in self.GENDER_OPTIONS
    
    def is_valid_age_range(self, age_range: str) -> bool:
        """Check if age range is valid"""
        return age_range in self.AGE_RANGES
    
    def get_formatted_areas(self) -> str:
        """Get formatted list of available areas"""
        return "\\n".join([f"📍 {area.title()}" for area in self.AREAS])
    
    def get_formatted_group_types(self) -> str:
        """Get formatted list of group types"""
        return "\\n".join([f"👥 {group_type.title()}" for group_type in self.GROUP_TYPES])
    
    def get_formatted_genders(self) -> str:
        """Get formatted list of gender options"""
        return "\\n".join([f"👤 {gender.title()}" for gender in self.GENDER_OPTIONS])
    
    def get_formatted_age_ranges(self) -> str:
        """Get formatted list of age ranges"""
        return "\\n".join([f"🎂 {age_range}" for age_range in self.AGE_RANGES])
    
    def extract_area_from_message(self, message: str) -> Optional[str]:
        """Extract area from user message"""
        message_lower = message.lower()
        for area in self.AREAS:
            if area in message_lower:
                return area
        return None
    
    def extract_group_type_from_message(self, message: str) -> Optional[str]:
        """Extract group type from user message"""
        message_lower = message.lower()
        for group_type in self.GROUP_TYPES:
            if group_type in message_lower:
                return group_type
        return None
    
    def extract_gender_from_message(self, message: str) -> Optional[str]:
        """Extract gender from user message"""
        message_lower = message.lower()
        for gender in self.GENDER_OPTIONS:
            if gender in message_lower:
                return gender
        return None
    
    def extract_age_range_from_message(self, message: str) -> Optional[str]:
        """Extract age range from user message"""
        for age_range in self.AGE_RANGES:
            if age_range in message:
                return age_range
        return None
    
    def get_signup_completion_data(self, whatsapp_number: str) -> Optional[Dict[str, Any]]:
        """Get completed signup data"""
        state = self.get_user_state(whatsapp_number)
        if state and state.get('state') == self.STATES['COMPLETED']:
            return state.get('data', {})
        return None

# Global instance
user_state_manager = UserStateManager()
