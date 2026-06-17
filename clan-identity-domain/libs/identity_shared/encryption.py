"""
Payload Encryption/Decryption Utilities for API Endpoints
Implements AES-256-GCM authenticated encryption for request/response payloads
"""

import base64
import json
import os
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.exceptions import InvalidTag
import secrets
import logging

logger = logging.getLogger(__name__)


class PayloadEncryption:
    """
    Handles encryption and decryption of API request/response payloads
    Uses AES-256-GCM for authenticated encryption with additional data (AEAD)
    """
    
    def __init__(self, encryption_key: str):
        """
        Initialize encryption with base64-encoded key
        
        Args:
            encryption_key: Base64-encoded 32-byte key for AES-256
        """
        try:
            # Decode base64 key
            self.key = base64.b64decode(encryption_key)
            
            # Validate key length (32 bytes for AES-256)
            if len(self.key) != 32:
                raise ValueError(f"Invalid key length: {len(self.key)}. Expected 32 bytes for AES-256")
            
            # Initialize AES-GCM cipher
            self.cipher = AESGCM(self.key)
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError(f"Invalid encryption key: {e}")
    
    def encrypt_payload(
        self, 
        data: Union[Dict, str, bytes],
        associated_data: Optional[bytes] = None
    ) -> Dict[str, str]:
        """
        Encrypt payload data
        
        Args:
            data: Data to encrypt (dict, string, or bytes)
            associated_data: Optional additional authenticated data (AAD)
        
        Returns:
            Dictionary with encrypted data and nonce
            {
                "encrypted_data": base64-encoded ciphertext,
                "nonce": base64-encoded nonce,
                "tag": base64-encoded authentication tag (included in ciphertext)
            }
        """
        try:
            # Convert data to bytes
            if isinstance(data, dict):
                plaintext = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                plaintext = data.encode('utf-8')
            elif isinstance(data, bytes):
                plaintext = data
            else:
                plaintext = str(data).encode('utf-8')
            
            # Generate random nonce (96 bits / 12 bytes recommended for GCM)
            nonce = secrets.token_bytes(12)
            
            # Encrypt with authenticated encryption
            # GCM automatically appends 16-byte authentication tag to ciphertext
            ciphertext = self.cipher.encrypt(
                nonce=nonce,
                data=plaintext,
                associated_data=associated_data
            )
            
            # Return base64-encoded components
            return {
                "encrypted_data": base64.b64encode(ciphertext).decode('utf-8'),
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "algorithm": "AES-256-GCM"
            }
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt payload: {e}")
    
    def decrypt_payload(
        self,
        encrypted_data: str,
        nonce: str,
        associated_data: Optional[bytes] = None,
        return_json: bool = True
    ) -> Union[Dict, str, bytes]:
        """
        Decrypt payload data
        
        Args:
            encrypted_data: Base64-encoded ciphertext
            nonce: Base64-encoded nonce
            associated_data: Optional additional authenticated data (must match encryption)
            return_json: If True, attempt to parse as JSON
        
        Returns:
            Decrypted data (dict if JSON parseable and return_json=True, else bytes/str)
        """
        try:
            # Decode base64 components
            ciphertext = base64.b64decode(encrypted_data)
            nonce_bytes = base64.b64decode(nonce)
            
            # Decrypt and verify authentication tag
            plaintext = self.cipher.decrypt(
                nonce=nonce_bytes,
                data=ciphertext,
                associated_data=associated_data
            )
            
            # Convert to string
            plaintext_str = plaintext.decode('utf-8')
            
            # Try to parse as JSON if requested
            if return_json:
                try:
                    return json.loads(plaintext_str)
                except json.JSONDecodeError:
                    return plaintext_str
            
            return plaintext_str
            
        except InvalidTag:
            logger.error("Decryption failed: Invalid authentication tag")
            raise ValueError("Failed to decrypt payload: Authentication verification failed")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt payload: {e}")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random 256-bit (32-byte) encryption key
        
        Returns:
            Base64-encoded key suitable for AES-256
        """
        key = secrets.token_bytes(32)
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: Password to derive key from
            salt: Optional salt (generates new one if not provided)
        
        Returns:
            Tuple of (base64_key, base64_salt)
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode('utf-8'))
        
        return (
            base64.b64encode(key).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )


class EncryptionManager:
    """
    Manages multiple encryption instances for different services/contexts
    Supports key rotation and service-specific encryption
    """
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize with configuration dictionary
        
        Args:
            config: Dictionary mapping service names to encryption keys
                    e.g., {"default": "key1", "auth": "key2", "user": "key3"}
        """
        self.encryptors: Dict[str, PayloadEncryption] = {}
        
        for service_name, key in config.items():
            if key and key.strip():
                try:
                    self.encryptors[service_name] = PayloadEncryption(key)
                    logger.info(f"Initialized encryption for service: {service_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize encryption for {service_name}: {e}")
    
    def get_encryptor(self, service_name: str = "default") -> Optional[PayloadEncryption]:
        """
        Get encryptor for specific service
        
        Args:
            service_name: Service identifier (falls back to "default" if not found)
        
        Returns:
            PayloadEncryption instance or None
        """
        encryptor = self.encryptors.get(service_name)
        if not encryptor and service_name != "default":
            encryptor = self.encryptors.get("default")
        return encryptor
    
    def encrypt(
        self,
        data: Any,
        service_name: str = "default",
        associated_data: Optional[bytes] = None
    ) -> Dict[str, str]:
        """Encrypt data using service-specific key"""
        encryptor = self.get_encryptor(service_name)
        if not encryptor:
            raise ValueError(f"No encryption key configured for service: {service_name}")
        return encryptor.encrypt_payload(data, associated_data)
    
    def decrypt(
        self,
        encrypted_data: str,
        nonce: str,
        service_name: str = "default",
        associated_data: Optional[bytes] = None,
        return_json: bool = True
    ) -> Any:
        """Decrypt data using service-specific key"""
        encryptor = self.get_encryptor(service_name)
        if not encryptor:
            raise ValueError(f"No encryption key configured for service: {service_name}")
        return encryptor.decrypt_payload(encrypted_data, nonce, associated_data, return_json)


# Utility functions for easy access
def create_encryption_from_env(
    default_key_var: str = "PAYLOAD_ENCRYPTION_KEY",
    service_keys: Optional[Dict[str, str]] = None
) -> Optional[EncryptionManager]:
    """
    Create EncryptionManager from environment variables
    
    Args:
        default_key_var: Environment variable name for default key
        service_keys: Optional dict mapping service names to env var names
    
    Returns:
        EncryptionManager instance or None if no keys configured
    """
    config = {}
    
    # Get default key
    default_key = os.getenv(default_key_var)
    if default_key:
        config["default"] = default_key
    
    # Get service-specific keys
    if service_keys:
        for service_name, env_var in service_keys.items():
            key = os.getenv(env_var)
            if key:
                config[service_name] = key
    
    if not config:
        logger.warning("No encryption keys configured in environment")
        return None
    
    return EncryptionManager(config)


# Example usage and testing
if __name__ == "__main__":
    # Generate a new key
    print("Generated Key:", PayloadEncryption.generate_key())
    
    # Test encryption/decryption
    key = PayloadEncryption.generate_key()
    encryptor = PayloadEncryption(key)
    
    test_data = {
        "username": "testuser",
        "email": "test@example.com",
        "sensitive_data": "This should be encrypted"
    }
    
    print("\nOriginal Data:", test_data)
    
    # Encrypt
    encrypted = encryptor.encrypt_payload(test_data)
    print("\nEncrypted:", encrypted)
    
    # Decrypt
    decrypted = encryptor.decrypt_payload(
        encrypted["encrypted_data"],
        encrypted["nonce"]
    )
    print("\nDecrypted Data:", decrypted)
    
    print("\n✓ Encryption/Decryption successful!")
