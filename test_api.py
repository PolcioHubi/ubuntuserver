#!/usr/bin/env python3
"""Test registered users endpoint"""
from app import app
import json

with app.test_client() as client:
    with app.app_context():
        # Simulate admin login first
        from flask import session
        with client.session_transaction() as sess:
            sess['admin_logged_in'] = True
        
        # Test the endpoint
        response = client.get('/admin/api/registered-users')
        data = json.loads(response.data)
        
        print(f"Status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        
        if 'users' in data:
            print(f"Liczba użytkowników w odpowiedzi: {len(data['users'])}")
            print("\nUżytkownicy:")
            for user in data['users']:
                print(f"  - {user['username']}")
        else:
            print(f"Error: {data.get('error')}")
