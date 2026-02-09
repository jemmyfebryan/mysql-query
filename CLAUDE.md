# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a FastAPI service that exposes MySQL databases as HTTP endpoints. It supports both single database connections (via `.env`) and multiple database connections (via `config.json`). The service provides two query modes:

1. **Public mode** (no API key): Only read-only queries (`SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `WITH`)
2. **Secure mode** (with API key): Full SQL access (INSERT, UPDATE, DELETE, etc.)

## Development Commands

### Virtual Environment
```bash
make venv        # Create/update virtual environment and install dependencies
```

### Running the Application
The project supports two deployment modes via the Makefile:

**PM2 mode (default, local development):**
```bash
make run         # Start via PM2
make stop        # Stop the service
make logs        # View logs
make restart     # Restart the service
make remove      # Remove from PM2
```

**Docker mode:**
```bash
USE_DOCKER=true make build    # Build Docker image
USE_DOCKER=true make run      # Run in container
USE_DOCKER=true make stop     # Stop container
USE_DOCKER=true make logs     # View logs
USE_DOCKER=true make shell    # Access container shell
USE_DOCKER=true make rebuild  # Full rebuild and restart
```

### Direct Python execution
```bash
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8085 --reload
```

## Architecture

### Entry Point
- **`main.py`**: FastAPI application initialization, database engine creation, endpoint registration

### Core Modules

**`core/register_connection.py`** - Dynamic endpoint registration
- `register_mysql_endpoint(app, db_name, engine)`: Creates POST endpoints for database queries
- Handles both secure (with API key) and public (read-only) query modes
- All registered endpoints follow pattern: `/mysql/{db_name}` or `/query` (single DB)

**`core/models.py`** - Pydantic request models
- `QueryRequest`: Standard query request with optional `api_key` and `params`
- `SecureQueryRequest`: Legacy model requiring `api_key`

**`api/api_key.py`** - API key generation and verification
- `generate_api_key(user_id, valid_days, unlimited)`: Creates HMAC-signed API keys
- `verify_api_key(api_key)`: Validates signature and expiry
- Keys are base64-encoded tokens containing: `user_id:expiry:signature`

**`core/logger.py`** - Colored logging utility
- `get_logger(name)`: Returns logger with ANSI color-coded output
- Prevents duplicate handlers on repeated calls

### Database Connection Pattern

The service creates SQLAlchemy async engines using `mysql+aiomysql` driver:

1. **Single DB** (`.env`): Creates `single_db_engine`, registers at `/query` and legacy `/secure_query`
2. **Multiple DBs** (`config.json`): Creates engine for each config entry, registers at `/mysql/{NAME}`

All engines use connection pooling with `pool_pre_ping=True` and `pool_recycle=3600`.

### Query Execution Flow

1. Request arrives at registered endpoint (e.g., `/mysql/mydb` or `/query`)
2. If `api_key` present → verify → full SQL access
3. If no `api_key` → enforce read-only statements only
4. Execute query with SQLAlchemy `text()` and optional `params`
5. Return rows for SELECT, or status message for mutations (with `last_insert_id` for INSERTs)

## Configuration Files

**`.env`**: Single database connection + SECRET_KEY for API signing
```
MYSQL_DB=
MYSQL_HOST=
MYSQL_USER=
MYSQL_PASS=
SECRET_KEY=
```

**`config.json`**: Multiple database connections (optional)
```json
{
    "mysql": [
        {
            "NAME": "endpoint_name",
            "MYSQL_DB": "database_name",
            "MYSQL_HOST": "host_ip",
            "MYSQL_USER": "username",
            "MYSQL_PASS": "password",
            "MYSQL_PORT": 3306
        }
    ]
}
```

## Key Implementation Details

- Database URLs are constructed using `sqlalchemy.engine.URL.create()` to handle password escaping properly
- The `/secure_query` endpoint (main.py:89-127) has a bug: references undefined `engine` variable instead of `single_db_engine`
- Parameterized queries supported via `params` dict in request payload
- API key expiry of `0` means unlimited validity
