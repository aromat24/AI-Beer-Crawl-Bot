#!/usr/bin/env python3
"""
Simple Flask test to debug startup issues
"""
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Simple Flask is working'})

@app.route('/')
def home():
    return jsonify({'message': 'Hello from simple Flask app'})

if __name__ == '__main__':
    print("Starting simple Flask app...")
    port = int(os.environ.get('PORT', 5000))
    print(f"Port: {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
