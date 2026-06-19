#!/bin/bash
# Auth Service Database Initialization Script (Bash)
# Creates clan_identity database and all required tables

set -e  # Exit on error

# Default configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-root}"
POSTGRES_DB="${POSTGRES_DB:-clan_identity}"

USE_PYTHON=true
USE_SQL=false

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
Auth Service Database Initialization Script

Usage:
    ./init_db.sh [options]

Options:
    -h, --host <host>       PostgreSQL host (default: localhost)
    -p, --port <port>       PostgreSQL port (default: 5432)
    -u, --user <user>       PostgreSQL user (default: postgres)
    -w, --password <pass>   PostgreSQL password (default: root)
    -d, --database <db>     Database name (default: clan_identity)
    --python                Use Python script for initialization (default)
    --sql                   Use SQL script for initialization
    --help                  Show this help message

Examples:
    # Initialize with defaults using Python
    ./init_db.sh

    # Initialize with custom credentials
    ./init_db.sh -h db.example.com -p 5433 -u admin -w secret

    # Initialize using SQL script
    ./init_db.sh --sql

    # Initialize from Docker
    ./init_db.sh -h postgres -u postgres -w root

Environment Variables:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    can be set to override defaults
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            POSTGRES_HOST="$2"
            shift 2
            ;;
        -p|--port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        -u|--user)
            POSTGRES_USER="$2"
            shift 2
            ;;
        -w|--password)
            POSTGRES_PASSWORD="$2"
            shift 2
            ;;
        -d|--database)
            POSTGRES_DB="$2"
            shift 2
            ;;
        --python)
            USE_PYTHON=true
            USE_SQL=false
            shift
            ;;
        --sql)
            USE_SQL=true
            USE_PYTHON=false
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            ;;
    esac
done

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}Auth Service Database Initialization${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Host:     ${POSTGRES_HOST}"
echo -e "  Port:     ${POSTGRES_PORT}"
echo -e "  User:     ${POSTGRES_USER}"
echo -e "  Database: ${POSTGRES_DB}"
echo ""

# Export environment variables
export POSTGRES_HOST
export POSTGRES_PORT
export POSTGRES_USER
export POSTGRES_PASSWORD
export POSTGRES_DB

# Check PostgreSQL connection
echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if command -v pg_isready &> /dev/null; then
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
    else
        echo -e "${RED}ERROR: Cannot connect to PostgreSQL${NC}"
        echo -e "${RED}Please ensure PostgreSQL is running and credentials are correct${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}WARNING: pg_isready not found, skipping connection check${NC}"
fi
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ "$USE_SQL" = true ]; then
    echo -e "${YELLOW}Using SQL script for initialization...${NC}"
    
    SQL_SCRIPT="$SCRIPT_DIR/init_db.sql"
    
    if [ ! -f "$SQL_SCRIPT" ]; then
        echo -e "${RED}ERROR: SQL script not found at $SQL_SCRIPT${NC}"
        exit 1
    fi
    
    # Set PGPASSWORD for non-interactive authentication
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Run SQL script
    echo -e "${YELLOW}Executing SQL initialization script...${NC}"
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -f "$SQL_SCRIPT"; then
        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}✓ Database initialized successfully!${NC}"
        echo -e "${GREEN}============================================${NC}"
    else
        echo ""
        echo -e "${RED}ERROR: SQL script execution failed${NC}"
        exit 1
    fi
    
    # Clear password from environment
    unset PGPASSWORD
    
else
    echo -e "${YELLOW}Using Python script for initialization...${NC}"
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        echo -e "${RED}ERROR: Python not found${NC}"
        echo -e "${RED}Please install Python or use --sql flag${NC}"
        exit 1
    fi
    
    PYTHON_CMD=$(command -v python3 || command -v python)
    echo -e "${GREEN}✓ Python found: $PYTHON_CMD${NC}"
    echo ""
    
    PYTHON_SCRIPT="$SCRIPT_DIR/init_db.py"
    
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        echo -e "${RED}ERROR: Python script not found at $PYTHON_SCRIPT${NC}"
        exit 1
    fi
    
    # Run Python script
    echo -e "${YELLOW}Executing Python initialization script...${NC}"
    echo ""
    
    if $PYTHON_CMD "$PYTHON_SCRIPT"; then
        echo ""
        echo -e "${GREEN}Python initialization completed successfully!${NC}"
    else
        echo ""
        echo -e "${RED}ERROR: Python script execution failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Verify tables: psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c '\\dt'"
echo -e "  2. Start the auth service: python main.py"
echo -e "  3. Check service health: curl http://localhost:8001/health"
echo ""
