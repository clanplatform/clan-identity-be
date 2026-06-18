"""
FastAPI Middleware for Request/Response Encryption
Automatically encrypts responses and decrypts requests for all API endpoints
"""

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, List, Optional
import json
import logging
from urllib.parse import urlparse

from .encryption import EncryptionManager

logger = logging.getLogger(__name__)


class EncryptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle request/response encryption
    
    Request Flow:
    1. Check if request has encrypted payload
    2. If encrypted, decrypt and replace request body
    3. Pass to endpoint handler
    
    Response Flow:
    1. Capture response from endpoint
    2. If encryption enabled and path not excluded, encrypt response
    3. Return encrypted response
    """
    
    def __init__(
        self,
        app,
        encryption_manager: EncryptionManager,
        enabled: bool = True,
        exclude_paths: Optional[List[str]] = None,
        service_name: str = "default",
        require_encryption: bool = False
    ):
        """
        Initialize encryption middleware
        
        Args:
            app: FastAPI application
            encryption_manager: EncryptionManager instance
            enabled: Enable/disable encryption (useful for dev/staging)
            exclude_paths: List of URL paths to exclude from encryption
            service_name: Service identifier for key selection
            require_encryption: If True, reject non-encrypted requests
        """
        super().__init__(app)
        self.encryption_manager = encryption_manager
        self.enabled = enabled
        self.exclude_paths = exclude_paths or ["/health", "/", "/docs", "/redoc", "/openapi.json"]
        self.service_name = service_name
        self.require_encryption = require_encryption
        
        logger.info(
            f"Encryption middleware initialized - "
            f"Enabled: {enabled}, "
            f"Service: {service_name}, "
            f"Excluded paths: {exclude_paths}"
        )
    
    def _should_encrypt(self, path: str) -> bool:
        """Check if path should be encrypted"""
        if not self.enabled:
            return False
        
        # Check excluded paths
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return False
        
        return True
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with encryption"""
        
        path = request.url.path
        should_encrypt = self._should_encrypt(path)
        
        # === DECRYPT INCOMING REQUEST ===
        if should_encrypt and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read request body
                body = await request.body()
                
                if body:
                    try:
                        body_json = json.loads(body)
                        
                        # Check if request is encrypted
                        if "encrypted_data" in body_json and "nonce" in body_json:
                            logger.debug(f"Decrypting request for {path}")
                            
                            # Decrypt payload
                            decrypted_data = self.encryption_manager.decrypt(
                                encrypted_data=body_json["encrypted_data"],
                                nonce=body_json["nonce"],
                                service_name=self.service_name,
                                associated_data=path.encode('utf-8')
                            )
                            
                            # Replace request body with decrypted data
                            decrypted_body = json.dumps(decrypted_data).encode('utf-8')
                            
                            # Create new request with decrypted body
                            async def receive():
                                return {"type": "http.request", "body": decrypted_body}
                            
                            request._receive = receive
                            
                            logger.info(f"✓ Successfully decrypted request for {path}")
                        
                        elif self.require_encryption:
                            # If encryption is required but request is not encrypted
                            logger.warning(f"Unencrypted request rejected for {path}")
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "error": "encryption_required",
                                    "message": "This endpoint requires encrypted requests"
                                }
                            )
                    
                    except json.JSONDecodeError:
                        # Not JSON, pass through
                        pass
                    except ValueError as e:
                        # Decryption failed
                        logger.error(f"Decryption failed for {path}: {e}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "error": "decryption_failed",
                                "message": "Failed to decrypt request payload"
                            }
                        )
            
            except Exception as e:
                logger.error(f"Error processing encrypted request: {e}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "internal_error",
                        "message": "Error processing request"
                    }
                )
        
        # === CALL ENDPOINT HANDLER ===
        response = await call_next(request)
        
        # === ENCRYPT OUTGOING RESPONSE ===
        if should_encrypt and response.status_code < 400:
            try:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                if response_body:
                    try:
                        # Parse response JSON
                        response_json = json.loads(response_body)
                        
                        # Don't encrypt if already encrypted
                        if "encrypted_data" not in response_json:
                            logger.debug(f"Encrypting response for {path}")
                            
                            # Encrypt response
                            encrypted_response = self.encryption_manager.encrypt(
                                data=response_json,
                                service_name=self.service_name,
                                associated_data=path.encode('utf-8')
                            )
                            
                            # Add metadata
                            encrypted_response["encrypted"] = True
                            encrypted_response["path"] = path
                            
                            logger.info(f"✓ Successfully encrypted response for {path}")
                            
                            # Return encrypted response
                            return JSONResponse(
                                content=encrypted_response,
                                status_code=response.status_code,
                                headers=dict(response.headers),
                                media_type="application/json"
                            )
                    
                    except json.JSONDecodeError:
                        # Not JSON, return as-is
                        pass
                    except Exception as e:
                        logger.error(f"Encryption failed for {path}: {e}")
                        # Return original response on encryption failure
                
                # Return original response
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            
            except Exception as e:
                logger.error(f"Error processing response encryption: {e}", exc_info=True)
                # Return original response on error
        
        return response


class SelectiveEncryptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware with fine-grained control over which endpoints use encryption
    Uses decorator or path pattern matching
    """
    
    def __init__(
        self,
        app,
        encryption_manager: EncryptionManager,
        enabled: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        service_name: str = "default"
    ):
        """
        Args:
            include_patterns: Only encrypt paths matching these patterns (e.g., ["/api/v1/users/*"])
            exclude_patterns: Never encrypt paths matching these patterns
        """
        super().__init__(app)
        self.encryption_manager = encryption_manager
        self.enabled = enabled
        self.include_patterns = include_patterns or ["*"]  # Default: encrypt all
        self.exclude_patterns = exclude_patterns or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.service_name = service_name
    
    def _should_encrypt(self, path: str) -> bool:
        """Check if path matches encryption rules"""
        if not self.enabled:
            return False
        
        # Check exclusions first
        for pattern in self.exclude_patterns:
            if self._matches_pattern(path, pattern):
                return False
        
        # Check inclusions
        for pattern in self.include_patterns:
            if self._matches_pattern(path, pattern):
                return True
        
        return False
    
    @staticmethod
    def _matches_pattern(path: str, pattern: str) -> bool:
        """Simple wildcard pattern matching"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return path.endswith(pattern[1:])
        return path == pattern
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process with selective encryption"""
        path = request.url.path
        should_encrypt = self._should_encrypt(path)

        if should_encrypt and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    try:
                        body_json = json.loads(body)
                        if "encrypted_data" in body_json and "nonce" in body_json:
                            decrypted_data = self.encryption_manager.decrypt(
                                encrypted_data=body_json["encrypted_data"],
                                nonce=body_json["nonce"],
                                service_name=self.service_name,
                                associated_data=path.encode("utf-8"),
                            )
                            decrypted_body = json.dumps(decrypted_data).encode("utf-8")

                            async def receive():
                                return {"type": "http.request", "body": decrypted_body}

                            request._receive = receive
                    except json.JSONDecodeError:
                        pass
                    except ValueError as e:
                        logger.error(f"Decryption failed for {path}: {e}")
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"error": "decryption_failed", "message": "Failed to decrypt request payload"},
                        )
            except Exception as e:
                logger.error(f"Error processing encrypted request: {e}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "internal_error", "message": "Error processing request"},
                )

        response = await call_next(request)

        if should_encrypt and response.status_code < 400:
            try:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                if response_body:
                    try:
                        response_json = json.loads(response_body)
                        if "encrypted_data" not in response_json:
                            encrypted_response = self.encryption_manager.encrypt(
                                data=response_json,
                                service_name=self.service_name,
                                associated_data=path.encode("utf-8"),
                            )
                            encrypted_response["encrypted"] = True
                            return JSONResponse(
                                content=encrypted_response,
                                status_code=response.status_code,
                                headers=dict(response.headers),
                                media_type="application/json",
                            )
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        logger.error(f"Encryption failed for {path}: {e}")

                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception as e:
                logger.error(f"Error processing response encryption: {e}", exc_info=True)

        return response


def setup_encryption_middleware(
    app,
    encryption_manager: Optional[EncryptionManager],
    config: dict
):
    """
    Setup encryption middleware with configuration
    
    Args:
        app: FastAPI application
        encryption_manager: EncryptionManager instance (None = disabled)
        config: Configuration dict with keys:
            - enabled: bool
            - exclude_paths: List[str]
            - service_name: str
            - require_encryption: bool
    """
    if encryption_manager and config.get("enabled", True):
        app.add_middleware(
            EncryptionMiddleware,
            encryption_manager=encryption_manager,
            enabled=config.get("enabled", True),
            exclude_paths=config.get("exclude_paths", []),
            service_name=config.get("service_name", "default"),
            require_encryption=config.get("require_encryption", False)
        )
        logger.info("✓ Encryption middleware added to application")
    else:
        logger.warning("⚠ Encryption middleware disabled or not configured")
