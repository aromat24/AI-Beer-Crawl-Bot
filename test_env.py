#!/usr/bin/env python3
"""Test environment variables"""
import os
from dotenv import load_dotenv

print("Before loading .env:")
print(f"GREEN_API_INSTANCE_ID: {os.environ.get('GREEN_API_INSTANCE_ID')}")
print(f"GREEN_API_TOKEN: {os.environ.get('GREEN_API_TOKEN')}")

load_dotenv()

print("\nAfter loading .env:")
print(f"GREEN_API_INSTANCE_ID: {os.environ.get('GREEN_API_INSTANCE_ID')}")
print(f"GREEN_API_TOKEN: {os.environ.get('GREEN_API_TOKEN')}")

USE_GREEN_API = bool(os.environ.get('GREEN_API_INSTANCE_ID') and os.environ.get('GREEN_API_TOKEN'))
print(f"USE_GREEN_API: {USE_GREEN_API}")
