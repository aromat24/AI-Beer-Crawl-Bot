import pytest
from unittest.mock import Mock, patch
from src.tasks.celery_tasks import (
    process_whatsapp_message,
    register_user_task,
    find_group_task,
    send_whatsapp_message,
    extract_area_from_message
)

class TestCeleryTasks:
    """Test suite for Celery background tasks."""
    
    def test_extract_area_from_message(self):
        """Test area extraction from message text."""
        test_cases = [
            ("I want to go to northern quarter", "northern quarter"),
            ("Looking for drinks in city centre", "city centre"),
            ("Deansgate sounds good", "deansgate"),
            ("Ancoats area please", "ancoats"),
            ("Meet in spinningfields", "spinningfields"),
            ("Just want beer", None),
        ]
        
        for message, expected_area in test_cases:
            result = extract_area_from_message(message)
            assert result == expected_area

    @patch('src.tasks.celery_tasks.register_user_task.delay')
    @patch('src.tasks.celery_tasks.confirm_group_participation.delay')
    @patch('src.tasks.celery_tasks.find_alternative_group.delay')
    @patch('src.tasks.celery_tasks.send_whatsapp_message.delay')
    def test_process_whatsapp_message(self, mock_send, mock_alt, mock_confirm, mock_register):
        """Test WhatsApp message processing."""
        
        # Test beer crawl message
        message = {
            'from': '+1234567890',
            'type': 'text',
            'text': {'body': 'I want to join a beer crawl'}
        }
        
        # Call the task directly (not async)
        process_whatsapp_message(message)
        mock_register.assert_called_once_with('+1234567890', 'i want to join a beer crawl')
        
        # Test confirmation message
        message['text']['body'] = 'yes'
        process_whatsapp_message(message)
        mock_confirm.assert_called_once_with('+1234567890')
        
        # Test alternative group request
        message['text']['body'] = "don't like this group"
        process_whatsapp_message(message)
        mock_alt.assert_called_once_with('+1234567890')
        
        # Test default response
        message['text']['body'] = 'hello'
        process_whatsapp_message(message)
        mock_send.assert_called()

    @patch('src.tasks.celery_tasks.requests.post')
    @patch('src.tasks.celery_tasks.find_group_task.delay')
    def test_register_user_task(self, mock_find_group, mock_post):
        """Test user registration task."""
        
        # Mock successful registration
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        register_user_task('+1234567890', 'I want beer in northern quarter')
        
        # Check API call was made with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['whatsapp_number'] == '+1234567890'
        assert call_args[1]['json']['preferred_area'] == 'northern quarter'
        
        # Check find_group_task was called
        mock_find_group.assert_called_once_with('+1234567890')

    @patch('src.tasks.celery_tasks.requests.post')
    @patch('src.tasks.celery_tasks.send_whatsapp_message.delay')
    @patch('src.tasks.celery_tasks.store_pending_confirmation.delay')
    @patch('src.tasks.celery_tasks.find_group_task.apply_async')
    def test_find_group_task(self, mock_find_async, mock_store, mock_send, mock_post):
        """Test find group task."""
        
        # Mock group ready to start
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'group': {
                'id': 1,
                'area': 'northern quarter',
                'current_members': 5,
                'max_members': 5
            },
            'ready_to_start': True
        }
        mock_post.return_value = mock_response
        
        find_group_task('+1234567890')
        
        # Check message was sent
        mock_send.assert_called_once()
        message = mock_send.call_args[0][1]
        assert 'Found 5 people' in message
        assert 'Shall I make a whatsapp group' in message
        
        # Check confirmation was stored
        mock_store.assert_called_once_with('+1234567890', 1)

    @patch('src.tasks.celery_tasks.requests.post')
    @patch('os.environ.get')
    def test_send_whatsapp_message(self, mock_env, mock_post):
        """Test WhatsApp message sending."""
        
        # Mock environment variables
        mock_env.side_effect = lambda key, default=None: {
            'WHATSAPP_TOKEN': 'test_token',
            'WHATSAPP_PHONE_ID': 'test_phone_id'
        }.get(key, default)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        send_whatsapp_message('+1234567890', 'Test message')
        
        # Check API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check headers
        headers = call_args[1]['headers']
        assert headers['Authorization'] == 'Bearer test_token'
        assert headers['Content-Type'] == 'application/json'
        
        # Check payload
        data = call_args[1]['json']
        assert data['messaging_product'] == 'whatsapp'
        assert data['to'] == '+1234567890'
        assert data['text']['body'] == 'Test message'

    @patch('src.tasks.celery_tasks.WHATSAPP_TOKEN', None)
    @patch('src.tasks.celery_tasks.WHATSAPP_PHONE_ID', None)
    def test_send_whatsapp_message_no_config(self):
        """Test WhatsApp message sending without configuration."""
        
        # Should not raise an exception, just print a message
        try:
            send_whatsapp_message('+1234567890', 'Test message')
        except Exception as e:
            pytest.fail(f"send_whatsapp_message raised an exception: {e}")

    @patch('src.tasks.celery_tasks.requests.get')
    @patch('src.tasks.celery_tasks.requests.post')
    @patch('src.tasks.celery_tasks.send_whatsapp_message.delay')
    def test_daily_cleanup(self, mock_send, mock_post, mock_get):
        """Test daily cleanup task."""
        from src.tasks.celery_tasks import daily_cleanup
        
        # Mock active groups response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'id': 1, 'whatsapp_group_id': 'group_1'},
            {'id': 2, 'whatsapp_group_id': 'group_2'}
        ]
        mock_get.return_value = mock_response
        
        # Mock end group response
        mock_end_response = Mock()
        mock_end_response.status_code = 200
        mock_post.return_value = mock_end_response
        
        daily_cleanup()
        
        # Check goodbye messages were sent
        assert mock_send.call_count == 2
        
        # Check groups were ended
        assert mock_post.call_count == 2
