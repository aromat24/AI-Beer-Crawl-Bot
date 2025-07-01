"""
Green API WhatsApp Integration Module
Handles WhatsApp messaging through Green API service
"""
import os
import requests
import json
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class GreenAPIClient:
    """Green API WhatsApp client for sending and receiving messages"""
    
    def __init__(self):
        self.instance_id = os.environ.get('GREEN_API_INSTANCE_ID', '7105273198')
        self.token = os.environ.get('GREEN_API_TOKEN', 'b8ed3b46b6c046e0a87997ccbfffe38eb7932e1730b747848d')
        self.base_url = os.environ.get('GREEN_API_URL', 'https://7105.api.greenapi.com')
        self.phone_number = os.environ.get('WHATSAPP_PHONE_NUMBER', '+66955124860')
        
        if not self.instance_id or not self.token:
            logger.warning("Green API credentials not configured")
            self.configured = False
        else:
            self.configured = True
            logger.info(f"Green API client initialized for instance {self.instance_id} with phone {self.phone_number}")
    
    def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send a text message via Green API
        
        Args:
            phone_number: Recipient's phone number (with country code)
            message: Message text to send
            
        Returns:
            Dict containing response from Green API
        """
        if not self.configured:
            logger.error("Green API not configured. Cannot send message.")
            return {"error": "Green API not configured"}
        
        # Clean phone number (remove + and spaces)
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        if not clean_phone.endswith('@c.us'):
            clean_phone = f"{clean_phone}@c.us"
        
        url = f"{self.base_url}/waInstance{self.instance_id}/sendMessage/{self.token}"
        
        payload = {
            "chatId": clean_phone,
            "message": message
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Message sent successfully to {phone_number}: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to {phone_number}: {str(e)}")
            return {"error": str(e)}
    
    def send_template_message(self, phone_number: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a template message (for structured messages)
        
        Args:
            phone_number: Recipient's phone number
            template_data: Template data structure
            
        Returns:
            Dict containing response from Green API
        """
        if not self.configured:
            logger.error("Green API not configured. Cannot send template message.")
            return {"error": "Green API not configured"}
        
        # For now, convert template to simple text message
        message = template_data.get('text', str(template_data))
        return self.send_message(phone_number, message)
    
    def get_account_settings(self) -> Dict[str, Any]:
        """
        Get Green API account settings and status
        
        Returns:
            Dict containing account information
        """
        if not self.configured:
            return {"error": "Green API not configured"}
        
        url = f"{self.base_url}/waInstance{self.instance_id}/getSettings/{self.token}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get account settings: {str(e)}")
            return {"error": str(e)}
    
    def get_state_instance(self) -> Dict[str, Any]:
        """
        Get current state of the WhatsApp instance
        
        Returns:
            Dict containing instance state
        """
        if not self.configured:
            return {"error": "Green API not configured"}
        
        url = f"{self.base_url}/waInstance{self.instance_id}/getStateInstance/{self.token}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get instance state: {str(e)}")
            return {"error": str(e)}
    
    def process_incoming_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming webhook from Green API
        
        Args:
            webhook_data: Raw webhook data from Green API
            
        Returns:
            Processed message data or None if not a message
        """
        try:
            # Green API webhook structure
            if webhook_data.get('typeWebhook') == 'incomingMessageReceived':
                message_data = webhook_data.get('messageData', {})
                sender_data = webhook_data.get('senderData', {})
                
                # Extract phone number (remove @c.us suffix)
                phone_number = sender_data.get('chatId', '').replace('@c.us', '')
                if phone_number.startswith('7'):  # If it starts with country code without +
                    phone_number = '+' + phone_number
                
                # Extract message text
                message_text = ''
                if message_data.get('typeMessage') == 'textMessage':
                    message_text = message_data.get('textMessageData', {}).get('textMessage', '')
                
                processed_message = {
                    'from': phone_number,
                    'text': {'body': message_text},
                    'type': 'text',
                    'timestamp': str(webhook_data.get('timestamp', '')),
                    'message_id': message_data.get('idMessage', ''),
                    'raw_data': webhook_data
                }
                
                logger.info(f"Processed Green API message from {phone_number}: {message_text}")
                return processed_message
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to process Green API webhook: {str(e)}")
            return None

# Create global instance
green_api_client = GreenAPIClient()

def send_whatsapp_message_green_api(phone_number: str, message: str) -> Dict[str, Any]:
    """
    Send WhatsApp message using Green API (compatibility function)
    
    Args:
        phone_number: Recipient's phone number
        message: Message text
        
    Returns:
        Result of the send operation
    """
    return green_api_client.send_message(phone_number, message)

def process_green_api_webhook(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process Green API webhook (compatibility function)
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Processed message or None
    """
    return green_api_client.process_incoming_webhook(webhook_data)
