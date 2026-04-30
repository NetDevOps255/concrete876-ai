#!/usr/bin/env python3
"""
Generate bcrypt password hash for ADMIN_PASSWORD_HASH in .env

Usage:
    python3 scripts/hash_password.py
    python3 scripts/hash_password.py mypassword
"""
import sys
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

if len(sys.argv) > 1:
    password = sys.argv[1]
else:
    import getpass
    password = getpass.getpass("Enter admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("ERROR: Passwords do not match")
        sys.exit(1)

hashed = pwd_context.hash(password)
print(f"\nAdd this to your .env:\n\nADMIN_PASSWORD_HASH={hashed}\n")
