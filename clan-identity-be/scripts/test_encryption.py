#!/usr/bin/env python3
"""
Test encryption/decryption functionality
Usage: python test_encryption.py [--key ENCRYPTION_KEY]
"""

import argparse
import json
import sys
import os

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))

from identity_shared.encryption import PayloadEncryption


def test_encryption(encryption_key: str = None):
    """Test encryption and decryption"""
    
    print("=" * 70)
    print("🧪 ENCRYPTION FUNCTIONALITY TEST")
    print("=" * 70)
    
    # Generate key if not provided
    if not encryption_key:
        print("\n⚠️  No key provided, generating new test key...\n")
        encryption_key = PayloadEncryption.generate_key()
        print(f"Test Key: {encryption_key}\n")
    
    # Initialize encryptor
    try:
        encryptor = PayloadEncryption(encryption_key)
        print("✓ Encryptor initialized successfully\n")
    except Exception as e:
        print(f"✗ Failed to initialize encryptor: {e}")
        return False
    
    # Test data
    test_cases = [
        {
            "name": "Login Request",
            "data": {
                "email": "test@example.com",
                "password": "SecurePassword123!",
                "remember_me": True
            },
            "path": "/api/v1/login"
        },
        {
            "name": "User Registration",
            "data": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "MySecret456!",
                "first_name": "John",
                "last_name": "Doe"
            },
            "path": "/api/v1/register"
        },
        {
            "name": "Payment Data",
            "data": {
                "card_number": "4111111111111111",
                "cvv": "123",
                "expiry": "12/25",
                "amount": 99.99
            },
            "path": "/api/v1/payment"
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print("-" * 70)
        
        # Display original data
        print(f"Original Data:")
        print(json.dumps(test_case['data'], indent=2))
        
        # Encrypt
        try:
            encrypted = encryptor.encrypt_payload(
                test_case['data'],
                associated_data=test_case['path'].encode('utf-8')
            )
            print(f"\n✓ Encryption successful")
            print(f"  Encrypted Data: {encrypted['encrypted_data'][:50]}...")
            print(f"  Nonce: {encrypted['nonce']}")
            print(f"  Algorithm: {encrypted['algorithm']}")
        except Exception as e:
            print(f"\n✗ Encryption failed: {e}")
            all_passed = False
            continue
        
        # Decrypt
        try:
            decrypted = encryptor.decrypt_payload(
                encrypted['encrypted_data'],
                encrypted['nonce'],
                associated_data=test_case['path'].encode('utf-8')
            )
            print(f"\n✓ Decryption successful")
            print(f"Decrypted Data:")
            print(json.dumps(decrypted, indent=2))
        except Exception as e:
            print(f"\n✗ Decryption failed: {e}")
            all_passed = False
            continue
        
        # Verify data integrity
        if decrypted == test_case['data']:
            print(f"\n✓ Data integrity verified")
        else:
            print(f"\n✗ Data integrity check failed")
            all_passed = False
        
        print("\n")
    
    # Test tampering detection
    print("Test: Tampering Detection")
    print("-" * 70)
    
    test_data = {"sensitive": "data"}
    encrypted = encryptor.encrypt_payload(test_data)
    
    # Tamper with encrypted data
    tampered_data = encrypted['encrypted_data'][:-4] + "XXXX"
    
    try:
        decryptor = encryptor.decrypt_payload(tampered_data, encrypted['nonce'])
        print("✗ Tampering detection failed - should have raised error")
        all_passed = False
    except ValueError as e:
        print(f"✓ Tampering detected and rejected: {str(e)[:50]}...")
    
    # Final result
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Test encryption/decryption functionality"
    )
    parser.add_argument(
        "--key",
        type=str,
        help="Encryption key to test (base64 encoded). If not provided, generates a new one."
    )
    
    args = parser.parse_args()
    
    success = test_encryption(args.key)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
