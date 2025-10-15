#!/usr/bin/env python3
"""Check database contents"""
from app import app, db
from models import User, File

with app.app_context():
    users_count = User.query.count()
    files_count = File.query.count()
    
    print(f"Użytkownicy w bazie: {users_count}")
    print(f"Pliki w bazie: {files_count}")
    
    if users_count > 0:
        print("\nPierwszych 5 użytkowników:")
        for user in User.query.limit(5).all():
            print(f"  - {user.username} (utworzony: {user.created_at})")
    
    if files_count > 0:
        print(f"\nPierwszych 5 plików:")
        for file in File.query.limit(5).all():
            print(f"  - {file.filename} ({file.user_username})")
