#!/usr/bin/env python3
"""
Generate encryption keys for API endpoint encryption
Usage: python generate_encryption_keys.py [--count N]
"""

import argparse
import sys
import os

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))

from identity_shared.encryption import PayloadEncryption


def generate_keys(count: int = 1, services: list = None):
    """Generate encryption keys"""
    
    if services:
        print("=" * 70)
        print("🔐 SERVICE-SPECIFIC ENCRYPTION KEYS")
        print("=" * 70)
        print("\nAdd these to your .env.prod file:\n")
        
        for service in services:
            key = PayloadEncryption.generate_key()
            env_var = f"{service.upper()}_SERVICE_ENCRYPTION_KEY"
            print(f"{env_var}={key}")
        
        print("\n" + "=" * 70)
    
    else:
        print("=" * 70)
        print("🔐 ENCRYPTION KEY GENERATOR")
        print("=" * 70)
        print(f"\nGenerating {count} encryption key(s)...\n")
        
        for i in range(count):
            key = PayloadEncryption.generate_key()
            
            if count == 1:
                print(f"PAYLOAD_ENCRYPTION_KEY={key}")
            else:
                print(f"Key {i+1}: {key}")
        
        print("\n" + "=" * 70)
        print("⚠️  SECURITY WARNING:")
        print("=" * 70)
        print("1. Never commit these keys to version control")
        print("2. Store securely in environment variables or secret manager")
        print("3. Use different keys for dev/uat/prod environments")
        print("4. Rotate keys periodically")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AES-256 encryption keys for API endpoints"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of keys to generate (default: 1)"
    )
    parser.add_argument(
        "--services",
        action="store_true",
        help="Generate keys for all microservices"
    )
    
    args = parser.parse_args()
    
    if args.services:
        services = ["auth", "user", "oauth", "rbac", "session"]
        generate_keys(services=services)
    else:
        generate_keys(count=args.count)


if __name__ == "__main__":
    main()
