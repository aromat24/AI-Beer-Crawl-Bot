#!/usr/bin/env python3
import sqlite3

def debug_database():
    conn = sqlite3.connect('/workspaces/Beer_Crawl/instance/app.db')
    cursor = conn.cursor()
    
    print("=== DATABASE DEBUG ===")
    
    # Check users table
    print("\nUSERS table columns:")
    try:
        cursor.execute('PRAGMA table_info(users)')
        for col in cursor.fetchall():
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Error checking users table: {e}")
    
    # Check crawl_groups table
    print("\nCRAWL_GROUPS table columns:")
    try:
        cursor.execute('PRAGMA table_info(crawl_groups)')
        for col in cursor.fetchall():
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Error checking crawl_groups table: {e}")
    
    # Sample data
    print("\nSample users data:")
    try:
        cursor.execute('SELECT * FROM users LIMIT 3')
        for row in cursor.fetchall():
            print(f"  {row}")
    except Exception as e:
        print(f"Error getting users data: {e}")
    
    print("\nSample crawl_groups data:")
    try:
        cursor.execute('SELECT * FROM crawl_groups LIMIT 3')
        for row in cursor.fetchall():
            print(f"  {row}")
    except Exception as e:
        print(f"Error getting crawl_groups data: {e}")
    
    conn.close()

if __name__ == "__main__":
    debug_database()
