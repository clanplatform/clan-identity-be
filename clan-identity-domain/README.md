# Clan Identity Domain - Backend Microservices

A scalable FastAPI-based microservices architecture for identity and access management, built with Python, PostgreSQL, and Redis.

## Architecture

This project implements a microservices architecture with the following services:

- **Auth Service** (Port 8001): Authentication and authorization
- **User Service** (Port 8002): User management
- **Session Service** (Port 8003): Session management
- **RBAC Service** (Port 8004): Role-based access control
- **OAuth Service** (Port 8005): OAuth 2.0 provider

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Container**: Docker & Docker Compose
- **Language**: Python 3.12

## Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Make (optional, for convenience commands)

## Quick Start

### 1. Clone and Setup

```bash
cd clan-identity-domain
cp .env.example .env
# Edit .env with your configuration
```

### 2. Build and Run

Using Make (recommended):
```bash
make dev-setup
```

Or using Docker Compose directly:
```bash
docker-compose build
docker-compose up -d
docker-compose exec auth-service alembic upgrade head
```

### 3. Verify Services

Check all services are running:
```bash
make ps
```

Access API documentation:
- Auth Service: http://localhost:8001/docs
- User Service: http://localhost:8002/docs
- Session Service: http://localhost:8003/docs
- RBAC Service: http://localhost:8004/docs
- OAuth Service: http://localhost:8005/docs

## Development

### Common Commands

```bash
# Start all services
make up

# Stop all services
make down

# View logs
make logs

# View logs for specific service
make logs-user

# Run tests
make test

# Access database
make shell-db

# Access Redis
make shell-redis

# Restart services
make restart
```

### Project Structure

```
clan-identity-domain/
├── libs/
│   └── identity_shared/         # Shared utilities
│       ├── database.py
│       ├── redis_client.py
│       ├── security.py
│       └── config.py
├── services/
│   ├── auth-service/
│   ├── user-service/
│   ├── session-service/
│   ├── rbac-service/
│   └── oauth-service/
├── deploy/
│   ├── Dockerfile
│   └── init-db.sh
├── config/
│   └── environments/
├── docker-compose.yml
└── Makefile
```

### Environment Variables

Key environment variables in `.env`:

- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `REDIS_PASSWORD`: Redis password
- `SECRET_KEY`: Application secret key
- `JWT_SECRET_KEY`: JWT signing key
- `ENVIRONMENT`: development/production

### Adding a New Service

1. Create service directory: `services/new-service/`
2. Add service configuration to `docker-compose.yml`
3. Create database for service (update `init-db.sh`)
4. Build and start: `docker-compose up -d new-service`

### Database Migrations

Each service manages its own database:

```bash
# Create migration
docker-compose exec auth-service alembic revision --autogenerate -m "description"

# Apply migrations
make migrate
```

## Testing

```bash
# Run all tests
make test

# Test specific service
docker-compose exec user-service pytest -v

# With coverage
docker-compose exec user-service pytest --cov=app --cov-report=html
```

## Production Deployment

1. Update `.env` with production values
2. Change `SECRET_KEY` and `JWT_SECRET_KEY`
3. Set `ENVIRONMENT=production`
4. Use proper password for PostgreSQL and Redis
5. Configure proper CORS origins
6. Use external managed databases for production
7. Set up proper logging and monitoring

## Security Notes

- Change all default passwords before deployment
- Use strong secret keys (min 32 characters)
- Configure CORS properly for production
- Enable SSL/TLS for database connections
- Use environment-specific configurations
- Implement rate limiting
- Regular security updates

## Monitoring

Health check endpoints available at `/health` for each service.

## Troubleshooting

### Services won't start
```bash
# Check logs
make logs

# Check service status
make ps

# Rebuild containers
make clean-all
make build
```

### Database connection issues
```bash
# Check database logs
make logs-db

# Access database directly
make shell-db
```

### Redis connection issues
```bash
# Check Redis logs
make logs-redis

# Access Redis CLI
make shell-redis
```

## License

[Your License Here]

## Contributors

[Your Team/Contributors]
