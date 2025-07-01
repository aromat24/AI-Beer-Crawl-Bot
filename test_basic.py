#!/usr/bin/env python3
"""
Test error handling without external dependencies
"""
import sys
import os

print("🧪 Error Handling Test (No External Deps)")
print("=" * 45)

# Add paths
sys.path.insert(0, 'src')

# Test basic error classes without imports
print("\n1. Testing basic error functionality...")

class TestCustomError(Exception):
    """Test version of CustomError"""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

# Test error creation
try:
    error = TestCustomError("Test error", 400, {"field": "test"})
    print(f"   ✅ Error created: '{error.message}' (status: {error.status_code})")
    print(f"   ✅ Payload: {error.payload}")
except Exception as e:
    print(f"   ❌ Error creation failed: {e}")

# Test Flask integration separately
print("\n2. Testing Flask imports...")
try:
    from flask import Flask, jsonify
    print("   ✅ Flask imported successfully")
    
    app = Flask(__name__)
    
    @app.route('/test')
    def test():
        return jsonify({"status": "ok"})
    
    print("   ✅ Flask app created with test route")
    
except Exception as e:
    print(f"   ❌ Flask test failed: {e}")

print("\n3. Testing actual error handling import...")
try:
    # Try importing piece by piece
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "error_handling", 
        "src/utils/error_handling.py"
    )
    error_module = importlib.util.module_from_spec(spec)
    
    print("   ✅ Module spec created")
    
    # This might fail, but let's see where
    spec.loader.exec_module(error_module)
    print("   ✅ Module loaded successfully")
    
    # Test creating an error
    CustomError = error_module.CustomError
    error = CustomError("Test", 500)
    print(f"   ✅ CustomError works: {error.message}")
    
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 45)
print("✅ Basic test completed!")
