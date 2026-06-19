# Auth Service Database Initialization Script (PowerShell)
# Creates clan_identity database and all required tables

param(
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$User = "postgres",
    [string]$Password = "root",
    [string]$Database = "clan_identity",
    [switch]$UsePython,
    [switch]$UseSQL,
    [switch]$Help
)

function Show-Help {
    Write-Host @"
Auth Service Database Initialization Script

Usage:
    .\init_db.ps1 [options]

Options:
    -Host <string>      PostgreSQL host (default: localhost)
    -Port <int>         PostgreSQL port (default: 5432)
    -User <string>      PostgreSQL user (default: postgres)
    -Password <string>  PostgreSQL password (default: root)
    -Database <string>  Database name (default: clan_identity)
    -UsePython          Use Python script for initialization (default)
    -UseSQL             Use SQL script for initialization
    -Help               Show this help message

Examples:
    # Initialize with defaults using Python
    .\init_db.ps1

    # Initialize with custom credentials using Python
    .\init_db.ps1 -Host db.example.com -Port 5433 -User admin -Password secret

    # Initialize using SQL script
    .\init_db.ps1 -UseSQL

    # Initialize from Docker
    .\init_db.ps1 -Host postgres -Port 5432 -User postgres -Password root
"@
    exit 0
}

if ($Help) {
    Show-Help
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Auth Service Database Initialization" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Set environment variables
$env:POSTGRES_HOST = $Host
$env:POSTGRES_PORT = $Port
$env:POSTGRES_USER = $User
$env:POSTGRES_PASSWORD = $Password
$env:POSTGRES_DB = $Database

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Host:     $Host" -ForegroundColor White
Write-Host "  Port:     $Port" -ForegroundColor White
Write-Host "  User:     $User" -ForegroundColor White
Write-Host "  Database: $Database" -ForegroundColor White
Write-Host ""

# Check PostgreSQL connection
Write-Host "Checking PostgreSQL connection..." -ForegroundColor Yellow
$pgIsReady = "pg_isready -h $Host -p $Port -U $User"
try {
    $result = Invoke-Expression $pgIsReady 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Cannot connect to PostgreSQL" -ForegroundColor Red
        Write-Host "Please ensure PostgreSQL is running and credentials are correct" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
} catch {
    Write-Host "WARNING: pg_isready not found, skipping connection check" -ForegroundColor Yellow
}
Write-Host ""

# Determine which initialization method to use
if ($UseSQL) {
    Write-Host "Using SQL script for initialization..." -ForegroundColor Yellow
    
    $scriptPath = Join-Path $PSScriptRoot "init_db.sql"
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "ERROR: SQL script not found at $scriptPath" -ForegroundColor Red
        exit 1
    }
    
    # Set PGPASSWORD for non-interactive authentication
    $env:PGPASSWORD = $Password
    
    # Run SQL script
    Write-Host "Executing SQL initialization script..." -ForegroundColor Yellow
    $psqlCmd = "psql -h $Host -p $Port -U $User -d postgres -f `"$scriptPath`""
    
    try {
        Invoke-Expression $psqlCmd
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "============================================" -ForegroundColor Green
            Write-Host "✓ Database initialized successfully!" -ForegroundColor Green
            Write-Host "============================================" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "ERROR: SQL script execution failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "ERROR: Failed to execute SQL script" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
    
    # Clear password from environment
    Remove-Item Env:\PGPASSWORD
    
} else {
    Write-Host "Using Python script for initialization..." -ForegroundColor Yellow
    
    # Check if Python is available
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        Write-Host "ERROR: Python not found" -ForegroundColor Red
        Write-Host "Please install Python or use -UseSQL flag" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Python found: $($pythonCmd.Source)" -ForegroundColor Green
    Write-Host ""
    
    $scriptPath = Join-Path $PSScriptRoot "init_db.py"
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "ERROR: Python script not found at $scriptPath" -ForegroundColor Red
        exit 1
    }
    
    # Run Python script
    Write-Host "Executing Python initialization script..." -ForegroundColor Yellow
    Write-Host ""
    
    try {
        & python $scriptPath
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "Python initialization completed successfully!" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "ERROR: Python script execution failed" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "ERROR: Failed to execute Python script" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Verify tables: psql -h $Host -p $Port -U $User -d $Database -c '\dt'" -ForegroundColor White
Write-Host "  2. Start the auth service: python main.py" -ForegroundColor White
Write-Host "  3. Check service health: curl http://localhost:8001/health" -ForegroundColor White
Write-Host ""
