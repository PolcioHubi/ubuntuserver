#!/usr/bin/env python3
"""Test users endpoint"""
from app import app
import json

with app.test_client() as client:
    with app.app_context():
        # Simulate admin login
        with client.session_transaction() as sess:
            sess['admin_logged_in'] = True
        
        # Test /admin/api/users endpoint
        response = client.get('/admin/api/users')
        data = json.loads(response.data)
        
        print("=== /admin/api/users ===")
        print(f"Status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        
        if 'stats' in data:
            stats = data['stats']
            print(f"\nStatystyki:")
            print(f"  total_users: {stats.get('total_users')}")
            print(f"  total_files: {stats.get('total_files')}")
            print(f"  total_size: {stats.get('total_size')}")
        
        if 'users_data' in data:
            users = data['users_data'].get('users', [])
            print(f"\nLiczba użytkowników w users_data: {len(users)}")
