#!/usr/bin/env python3
"""
Simple test admin dashboard
"""
import os
import sqlite3
import redis
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/test')
def test():
    return jsonify({'status': 'ok', 'message': 'Admin dashboard is working'})

@app.route('/test/db')
def test_db():
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({'status': 'ok', 'tables': tables})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/test/redis')
def test_redis():
    try:
        client = redis.from_url('redis://localhost:6379', db=0, decode_responses=True)
        client.ping()
        return jsonify({'status': 'ok', 'message': 'Redis connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/test/users')
def test_users():
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM users LIMIT 3")
        users = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'status': 'ok', 
            'count': count,
            'sample_users': users
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
