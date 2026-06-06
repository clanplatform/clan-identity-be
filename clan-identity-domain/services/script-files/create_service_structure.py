#!/usr/bin/env python3
"""
Script to create complete application structure for all services
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Services to create structure for
SERVICES = {
    "auth-service": {
        "name": "Auth Service",
        "db": "auth_service",
        "redis_db": "0",
        "routes": ["auth"]
    },
    "session-service": {
        "name": "Session Service",
        "db": "session_service",
        "redis_db": "2",
        "routes": ["sessions"]
    },
    "rbac-service": {
        "name": "RBAC Service",
        "db": "rbac_service",
        "redis_db": "3",
        "routes": ["rbac"]
    },
    "oauth-service": {
        "name": "OAuth Service",
        "db": "oauth_service",
        "redis_db": "4",
        "routes": ["oauth"]
    }
}

# Directory structure template
STRUCTURE = [
    "app/__init__.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/db/__init__.py",
    "app/db/database.py",
    "app/models/__init__.py",
    "app/api/__init__.py",
    "app/api/routes/__init__.py",
]


def create_structure(service_name, config):
    """Create directory structure for a service"""
    service_dir = BASE_DIR / service_name
    print(f"\nCreating structure for {service_name}...")
    
    # Create directories and files
    for path in STRUCTURE:
        full_path = service_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not full_path.exists():
            full_path.touch()
            print(f"  ✓ Created {path}")
        else:
            print(f"  - Exists {path}")
    
    # Create route files
    for route in config["routes"]:
        route_file = service_dir / f"app/api/routes/{route}.py"
        if not route_file.exists():
            route_file.touch()
            print(f"  ✓ Created app/api/routes/{route}.py")


if __name__ == "__main__":
    print("="*80)
    print("Creating Service Structure")
    print("="*80)
    
    for service_name, config in SERVICES.items():
        create_structure(service_name, config)
    
    print("\n" + "="*80)
    print("✓ Service structure creation complete!")
    print("="*80)
