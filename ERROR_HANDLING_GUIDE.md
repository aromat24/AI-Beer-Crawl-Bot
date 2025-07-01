# Error Handling Testing Guide

## ✅ **TEST RESULTS: ALL PASSED!** 

Your error handling system is working perfectly! Here's how to test and use it:

## 🧪 **How to Test Error Handling**

### 1. **Quick Test** (Recommended)
```bash
cd /workspaces/Beer_Crawl
python test_final.py
```

### 2. **Individual Component Tests**
```bash
# Test just the error classes
python test_basic.py

# Test with manual scenarios  
python test_manual.py

# Start interactive test server
python test_error_server.py
# Then visit: http://localhost:5001
```

### 3. **Integration with Main App**
```bash
# Test with your main Flask app
python app.py
# Then test endpoints:
curl http://localhost:5000/health
curl http://localhost:5000/api/beer-crawl/bars
```

## 🔧 **How to Use Error Handling in Your Code**

### 1. **Setup in Flask App**
```python
from src.utils.error_handling import setup_error_handlers, configure_logging

app = Flask(__name__)

# Setup error handling (do this once)
configure_logging(app)
setup_error_handlers(app)
```

### 2. **Use Error Classes in Routes**
```python
from src.utils.error_handling import ValidationError, NotFoundError, AuthenticationError

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    # Validate input
    if user_id <= 0:
        raise ValidationError(
            "Invalid user ID", 
            {"field": "user_id", "value": user_id, "min": 1}
        )
    
    # Check authentication
    if not request.headers.get('Authorization'):
        raise AuthenticationError("API key required")
    
    # Database lookup
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(
            f"User {user_id} not found",
            {"user_id": user_id, "table": "users"}
        )
    
    return jsonify(user.to_dict())
```

### 3. **Available Error Classes**

| Error Class | Status Code | Use Case |
|-------------|-------------|----------|
| `ValidationError` | 400 | Invalid input data |
| `AuthenticationError` | 401 | Login/token issues |
| `AuthorizationError` | 403 | Permission denied |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Data conflicts |
| `RateLimitError` | 429 | Too many requests |
| `ServiceUnavailableError` | 503 | Service down |
| `CustomError` | Custom | Any custom error |

### 4. **Error Response Format**
All errors return consistent JSON:
```json
{
  "error": "Validation error message",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00Z",
  "details": {
    "field": "email",
    "value": "invalid-email"
  }
}
```

## 📋 **Real-World Examples**

### Email Validation
```python
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    if not data.get('email') or '@' not in data['email']:
        raise ValidationError(
            "Invalid email format",
            {
                "field": "email", 
                "value": data.get('email'),
                "expected": "user@domain.com"
            }
        )
    
    # Continue with user creation...
```

### Authentication Check
```python
@app.route('/api/protected')
def protected_route():
    token = request.headers.get('Authorization')
    
    if not token:
        raise AuthenticationError("Authorization header required")
    
    if not verify_token(token):
        raise AuthenticationError("Invalid or expired token")
    
    # Continue with protected logic...
```

### Database Lookups
```python
@app.route('/api/bars/<int:bar_id>')
def get_bar(bar_id):
    bar = Bar.query.get(bar_id)
    
    if not bar:
        raise NotFoundError(
            f"Bar {bar_id} not found",
            {
                "bar_id": bar_id,
                "available_bars": [b.id for b in Bar.query.limit(5).all()]
            }
        )
    
    return jsonify(bar.to_dict())
```

## 🔍 **Testing Your Error Handling**

### Manual Testing with Curl
```bash
# Test validation error
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid-email"}'

# Test authentication error
curl http://localhost:5000/api/protected

# Test not found error
curl http://localhost:5000/api/bars/99999
```

### Automated Testing
```python
def test_validation_error(client):
    response = client.post('/api/users', json={'email': 'invalid'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'Invalid email format' in data['error']
    assert data['details']['field'] == 'email'
```

## 🎯 **Best Practices**

1. **Always include helpful context** in error payloads
2. **Use specific error classes** instead of generic ones
3. **Log errors** for debugging (already handled automatically)
4. **Return consistent JSON structure** (handled by error handlers)
5. **Test error scenarios** as part of your test suite

## 🚀 **Next Steps**

1. ✅ **Error handling is working** - all tests passed!
2. 🔧 **Integrate into your routes** - use the examples above
3. 🧪 **Add tests** - test your error scenarios
4. 📊 **Monitor in production** - errors are logged automatically
5. 🔍 **Customize as needed** - extend error classes for your use cases

Your error handling system is production-ready! 🎉
