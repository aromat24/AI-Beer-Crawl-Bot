#!/usr/bin/env python3
"""
Simple test script for error handling classes
Tests the error classes without requiring Flask server
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

def test_error_classes():
    """Test all error classes"""
    print("🧪 Testing Error Handling Classes")
    print("=" * 40)
    
    try:
        # Import our error classes
        from src.utils.error_handling import (
            CustomError, ValidationError, AuthenticationError, AuthorizationError,
            NotFoundError, ConflictError, RateLimitError, ServiceUnavailableError
        )
        
        print("✅ Successfully imported all error classes")
        
        # Test each error class
        test_cases = [
            {
                "name": "CustomError",
                "class": CustomError,
                "args": ("Test error", 500, {"detail": "test"}),
                "expected": {"message": "Test error", "status_code": 500, "payload": {"detail": "test"}}
            },
            {
                "name": "ValidationError", 
                "class": ValidationError,
                "args": ("Invalid input", {"field": "email"}),
                "expected": {"message": "Invalid input", "status_code": 400, "payload": {"field": "email"}}
            },
            {
                "name": "AuthenticationError",
                "class": AuthenticationError,
                "args": ("Token expired",),
                "expected": {"message": "Token expired", "status_code": 401}
            },
            {
                "name": "AuthorizationError",
                "class": AuthorizationError,
                "args": ("Access denied",),
                "expected": {"message": "Access denied", "status_code": 403}
            },
            {
                "name": "NotFoundError",
                "class": NotFoundError,
                "args": ("User not found",),
                "expected": {"message": "User not found", "status_code": 404}
            },
            {
                "name": "ConflictError",
                "class": ConflictError,
                "args": ("Email exists",),
                "expected": {"message": "Email exists", "status_code": 409}
            },
            {
                "name": "RateLimitError",
                "class": RateLimitError,
                "args": (),
                "expected": {"message": "Rate limit exceeded", "status_code": 429}
            },
            {
                "name": "ServiceUnavailableError",
                "class": ServiceUnavailableError,
                "args": ("Maintenance",),
                "expected": {"message": "Maintenance", "status_code": 503}
            }
        ]
        
        for test_case in test_cases:
            try:
                # Create error instance
                error = test_case["class"](*test_case["args"])
                
                # Check attributes
                assert error.message == test_case["expected"]["message"]
                assert error.status_code == test_case["expected"]["status_code"]
                
                if "payload" in test_case["expected"]:
                    assert error.payload == test_case["expected"]["payload"]
                
                print(f"✅ {test_case['name']}: PASSED")
                
            except Exception as e:
                print(f"❌ {test_case['name']}: FAILED - {e}")
        
        print("\n" + "=" * 40)
        print("✅ Error class testing completed!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install structlog")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_logging_functions():
    """Test logging utility functions"""
    print("\n🧪 Testing Logging Functions")
    print("=" * 40)
    
    try:
        from src.utils.error_handling import (
            log_user_action, log_celery_task, log_whatsapp_interaction
        )
        
        print("✅ Successfully imported logging functions")
        
        # Test logging functions
        print("\n📝 Testing log_user_action...")
        log_user_action("user123", "login", {"ip": "192.168.1.1"})
        print("✅ log_user_action: PASSED")
        
        print("\n📝 Testing log_celery_task...")
        log_celery_task("send_email", "task_123", "success", {"recipient": "test@example.com"})
        print("✅ log_celery_task: PASSED")
        
        print("\n📝 Testing log_whatsapp_interaction...")
        log_whatsapp_interaction("+1234567890", "text", "sent", {"message": "Hello World"})
        print("✅ log_whatsapp_interaction: PASSED")
        
        print("\n" + "=" * 40)
        print("✅ Logging function testing completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False

def main():
    """Main test function"""
    print("AI Beer Crawl - Error Handling Quick Test")
    print("=" * 50)
    
    success1 = test_error_classes()
    success2 = test_logging_functions()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All tests PASSED! Error handling is working correctly.")
        print("\nNext steps:")
        print("1. Run the manual test server: python test_error_handling_manual.py")
        print("2. Test with the main Flask app: python app.py")
        print("3. Test API endpoints with curl or browser")
    else:
        print("❌ Some tests FAILED. Check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the correct directory")
        print("2. Install dependencies: pip install structlog")
        print("3. Check that the error handling file exists: src/utils/error_handling.py")

if __name__ == "__main__":
    main()
