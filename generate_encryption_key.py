#!/usr/bin/env python3
"""
Generate a proper Fernet encryption key for Railway deployment.
Run this script and copy the output to Railway's ENCRYPTION_KEY environment variable.
"""

from cryptography.fernet import Fernet

def generate_key():
    """Generate a new Fernet encryption key"""
    key = Fernet.generate_key()
    return key.decode()

if __name__ == '__main__':
    print("=" * 70)
    print("🔐 ENCRYPTION KEY GENERATOR")
    print("=" * 70)
    print()
    print("Generated Fernet Encryption Key:")
    print()
    print("┌" + "─" * 68 + "┐")
    key = generate_key()
    print(f"│ {key:66s} │")
    print("└" + "─" * 68 + "┘")
    print()
    print("📋 Instructions:")
    print("1. Copy the key above (all 44 characters)")
    print("2. Go to Railway → Backend service → Variables")
    print("3. Find or add: ENCRYPTION_KEY")
    print("4. Paste the key and save")
    print("5. Backend will auto-redeploy")
    print()
    print("⚠️  IMPORTANT: After updating this key, you must re-enter all")
    print("   API keys in your frontend (Settings → API Keys)")
    print()
    print("=" * 70)
