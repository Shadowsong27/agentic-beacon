# Project-Level AGENTS.md Guide

A comprehensive guide to creating and maintaining project-specific agent context.

**Last Updated:** 2026-03-07

---

## Overview

Project-level AGENTS.md serves as the **entry point for agents working in your codebase**. It provides project-specific context that agents need to understand your architecture, navigate your code, follow project conventions, and troubleshoot issues.

**Location:** `<project-root>/AGENTS.md`

**Purpose:** Bridge the gap between generic organizational standards (from warehouse) and the specific implementation details of THIS codebase.

---

## Why Project-Level AGENTS.md Matters

### Without Project Context

**Scenario:** Agent needs to add authentication to a new API endpoint.

**What happens:**
- Agent doesn't know where auth logic lives
- Agent doesn't know which auth library you use
- Agent doesn't know your auth patterns (JWT? Session? OAuth?)
- Agent creates inconsistent implementation
- You spend time reviewing and correcting

### With Project Context

**Scenario:** Agent needs to add authentication to a new API endpoint.

**What the agent knows from AGENTS.md:**
```markdown
## Authentication

**Pattern:** JWT-based authentication via `src/auth/middleware.py`

**Adding auth to endpoints:**
1. Import: `from src.auth import require_auth`
2. Decorate: `@require_auth(roles=["admin", "user"])`
3. Access user: `current_user = get_current_user()`

**Example:** See `src/api/users.py:45-60`
```

**What happens:**
- Agent finds existing auth middleware immediately
- Agent follows established patterns consistently
- Agent writes code that matches your architecture
- Review is quick and painless

---

## Core Principle: Reduce Agent Onboarding Time

Think of project-level AGENTS.md as **onboarding documentation for AI agents**. Just like you'd provide context to a new human developer, you provide context to agents.

**Key questions it answers:**
1. **What is this project?** (purpose, scope, boundaries)
2. **How is it structured?** (architecture, modules, dependencies)
3. **Where do I find things?** (code organization, key files)
4. **How do I work with it?** (development workflow, testing, deployment)
5. **What are the gotchas?** (known issues, quirks, workarounds)

---

## What Belongs in Project-Level AGENTS.md

### 1. Project Identity and Context

**Purpose:** Help agents understand what this codebase is and why it exists.

**Include:**
- Project name and purpose
- Business domain and users
- Scope and boundaries (what it does, what it doesn't do)
- Relationship to other services/projects

**Example:**
```markdown
# Project: Customer Data Platform (CDP)

## Purpose

Centralized customer data warehouse that ingests data from multiple sources, transforms it, and provides unified customer profiles via API.

## Users

- **Internal:** Marketing team (customer segments), Sales team (lead scoring)
- **External:** Partner systems via REST API

## Scope

**In scope:**
- Data ingestion from Salesforce, Stripe, Segment
- Customer profile unification and deduplication
- REST API for profile queries

**Out of scope:**
- Real-time streaming (we use batch processing)
- Customer-facing UI (handled by separate frontend service)
- Payment processing (delegated to Stripe)

## Related Services

- **Depends on:** PostgreSQL (primary data store), Redis (cache)
- **Depended on by:** Marketing Dashboard, Sales CRM Integration
- **Integrates with:** Salesforce API, Stripe API, Segment Webhook
```

---

### 2. Architecture Overview

**Purpose:** Give agents a mental model of how the system is structured.

**Include:**
- High-level architecture diagram or description
- Key components and their responsibilities
- Data flow between components
- External dependencies and integrations
- Communication patterns (REST, gRPC, events, etc.)

**Example:**
```markdown
## Architecture

**Pattern:** Layered architecture with clear separation of concerns

```
┌─────────────────────────────────────────────┐
│  API Layer (FastAPI)                        │
│  - REST endpoints                            │
│  - Request validation (Pydantic)            │
│  - Authentication (JWT)                      │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  Service Layer                               │
│  - Business logic                            │
│  - Orchestration                             │
│  - Transaction management                    │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  Data Access Layer                           │
│  - Repository pattern                        │
│  - Database queries (SQLAlchemy)            │
│  - Cache management (Redis)                  │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  Data Storage                                │
│  - PostgreSQL (primary)                      │
│  - Redis (cache + session store)            │
└─────────────────────────────────────────────┘
```

**Key Principles:**
- API layer never calls database directly (must go through service layer)
- Service layer contains ALL business logic
- Data access layer handles ONLY database queries (no business logic)

**External Integrations:**
- Salesforce: Ingest customer data (batch, every 6 hours)
- Stripe: Ingest payment data (webhook + batch reconciliation)
- Segment: Real-time event tracking (webhook)
```

---

### 3. Code Organization

**Purpose:** Help agents navigate your codebase structure.

**Include:**
- Directory structure with explanations
- Module purposes and responsibilities
- Key files and their locations
- Naming conventions for files/directories

**Example:**
```markdown
## Code Organization

### Directory Structure

```
src/
├── api/                    # API layer (FastAPI routes)
│   ├── routes/            # Endpoint definitions
│   │   ├── customers.py   # Customer profile endpoints
│   │   ├── segments.py    # Segment management endpoints
│   │   └── health.py      # Health check endpoints
│   ├── middleware/        # Request/response middleware
│   │   ├── auth.py        # Authentication middleware
│   │   └── logging.py     # Request logging
│   └── schemas/           # Pydantic request/response schemas
│
├── services/              # Service layer (business logic)
│   ├── customer_service.py    # Customer profile operations
│   ├── segment_service.py     # Customer segmentation
│   └── ingestion_service.py   # Data ingestion orchestration
│
├── repositories/          # Data access layer
│   ├── customer_repo.py   # Customer data access
│   ├── event_repo.py      # Event data access
│   └── base_repo.py       # Shared repository patterns
│
├── models/                # Database models (SQLAlchemy)
│   ├── customer.py        # Customer table definition
│   ├── event.py           # Event table definition
│   └── segment.py         # Segment table definition
│
├── integrations/          # External service integrations
│   ├── salesforce/        # Salesforce client + sync logic
│   ├── stripe/            # Stripe webhook handler + sync
│   └── segment/           # Segment webhook handler
│
├── core/                  # Shared utilities
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection + session
│   ├── cache.py           # Redis cache wrapper
│   └── auth.py            # Authentication utilities
│
└── migrations/            # Database migrations (Alembic)
    └── versions/          # Migration scripts
```

### Key Modules

**CustomerService** (`src/services/customer_service.py`)
- **Purpose:** Core business logic for customer profiles
- **Entry point:** `CustomerService.get_profile(customer_id: str)`
- **Responsibilities:**
  - Profile unification (merge data from multiple sources)
  - Deduplication logic
  - Profile enrichment
- **Used by:** API routes, ingestion jobs

**CustomerRepository** (`src/repositories/customer_repo.py`)
- **Purpose:** Database operations for customer data
- **Pattern:** Repository pattern (abstracts database queries)
- **Key methods:**
  - `find_by_id(customer_id: str) -> Customer | None`
  - `find_by_email(email: str) -> list[Customer]`
  - `upsert(customer: Customer) -> Customer`
- **Note:** No business logic here - pure data access only

**SalesforceIntegration** (`src/integrations/salesforce/client.py`)
- **Purpose:** Sync customer data from Salesforce
- **Schedule:** Runs every 6 hours via Airflow DAG
- **Entry point:** `SalesforceClient.sync_customers()`
- **Authentication:** OAuth2 (credentials in environment)

### Naming Conventions

**Files:**
- `snake_case.py` for all Python files
- `{entity}_service.py` for service layer
- `{entity}_repo.py` for repository layer
- `test_{module}.py` for test files

**Classes:**
- `PascalCase` for classes
- Service classes end with `Service` (e.g., `CustomerService`)
- Repository classes end with `Repository` (e.g., `CustomerRepository`)

**Functions:**
- `snake_case` for all functions
- Use verbs for actions: `get_profile()`, `create_customer()`, `update_segment()`
```

---

### 4. Development Workflow

**Purpose:** Help agents set up, run, and test code locally.

**Include:**
- Environment setup steps
- How to run the application locally
- How to run tests
- Database setup and migrations
- Common development commands

**Example:**
```markdown
## Development Workflow

### First-Time Setup

1. **Clone repository:**
   ```bash
   git clone https://github.com/yourorg/customer-data-platform.git
   cd customer-data-platform
   ```

2. **Create virtual environment:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

5. **Set up database:**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis
   
   # Run migrations
   alembic upgrade head
   
   # Seed test data (optional)
   python scripts/seed_test_data.py
   ```

### Running Locally

**Start API server:**
```bash
# Development mode (hot reload)
uvicorn src.main:app --reload --port 8000

# Access at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

**Start background workers:**
```bash
# Start Celery worker for async tasks
celery -A src.worker worker --loglevel=info
```

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run specific test file:**
```bash
pytest tests/services/test_customer_service.py
```

**Run with coverage:**
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Run integration tests only:**
```bash
pytest -m integration
```

**Note:** Integration tests require database:
```bash
docker-compose up -d postgres
export DATABASE_URL="postgresql://test:test@localhost:5432/cdp_test"
pytest -m integration
```

### Database Migrations

**Create new migration:**
```bash
alembic revision --autogenerate -m "Add customer preferences table"
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback last migration:**
```bash
alembic downgrade -1
```

### Common Commands

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/

# All checks (runs in CI)
make lint  # Runs black, ruff, mypy

# Update dependencies
pip-compile requirements.in
pip-sync requirements.txt
```
```

---

### 5. Key Patterns and Conventions

**Purpose:** Document project-specific patterns that differ from generic standards.

**Include:**
- Error handling patterns
- Logging conventions
- Testing patterns
- Configuration management
- Authentication/authorization patterns

**Example:**
```markdown
## Key Patterns

### Error Handling

**Pattern:** Return `Result[T, Error]` types instead of raising exceptions in service layer.

**Rationale:** Explicit error handling, better type safety, easier testing.

**Example:**
```python
# Service layer
def get_customer(customer_id: str) -> Result[Customer, CustomerError]:
    customer = customer_repo.find_by_id(customer_id)
    if not customer:
        return Err(CustomerError.NOT_FOUND)
    return Ok(customer)

# API layer
@router.get("/customers/{customer_id}")
def get_customer_endpoint(customer_id: str):
    result = customer_service.get_customer(customer_id)
    if result.is_err():
        error = result.unwrap_err()
        if error == CustomerError.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Customer not found")
        raise HTTPException(status_code=500, detail="Internal error")
    return result.unwrap()
```

**When to use exceptions:**
- API layer: Convert Result errors to HTTPException
- Validation errors: Pydantic validation (automatically handled by FastAPI)
- Unexpected errors: Let them propagate (caught by global error handler)

### Logging

**Pattern:** Structured logging with `loguru`

**Log levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: Important business events (customer created, segment updated)
- `WARNING`: Degraded functionality (fallback behavior, retry)
- `ERROR`: Operation failed but system continues
- `CRITICAL`: System-level failure (database down, external API unavailable)

**Include in logs:**
```python
from loguru import logger

# Always include relevant IDs
logger.info("Customer profile updated", customer_id=customer_id, user_id=user_id)

# Include timing for slow operations
with logger.contextualize(operation="salesforce_sync"):
    start = time.time()
    result = sync_customers()
    duration = time.time() - start
    logger.info("Salesforce sync completed", duration=duration, records=len(result))
```

**Never log:**
- Passwords or API keys
- PII without redaction (use `redact_email()` helper)
- Large payloads (log size/count instead)

### Testing

**Pattern:** Repository pattern + dependency injection for testability

**Test structure:**
```
tests/
├── unit/              # Fast, isolated tests (no database)
│   ├── services/      # Service layer tests (mock repositories)
│   └── utils/         # Utility function tests
├── integration/       # Tests with database
│   ├── repositories/  # Repository tests (real database)
│   └── api/           # API endpoint tests (real database)
└── e2e/               # Full system tests
    └── scenarios/     # Business scenario tests
```

**Unit test example:**
```python
# tests/unit/services/test_customer_service.py
from unittest.mock import Mock
from src.services.customer_service import CustomerService

def test_get_customer_not_found():
    # Arrange
    mock_repo = Mock()
    mock_repo.find_by_id.return_value = None
    service = CustomerService(repository=mock_repo)
    
    # Act
    result = service.get_customer("nonexistent")
    
    # Assert
    assert result.is_err()
    assert result.unwrap_err() == CustomerError.NOT_FOUND
```

**Integration test example:**
```python
# tests/integration/repositories/test_customer_repo.py
import pytest
from src.repositories.customer_repo import CustomerRepository
from src.models.customer import Customer

@pytest.mark.integration
def test_create_customer(db_session):
    # Arrange
    repo = CustomerRepository(session=db_session)
    customer = Customer(email="test@example.com", name="Test User")
    
    # Act
    created = repo.create(customer)
    
    # Assert
    assert created.id is not None
    found = repo.find_by_id(created.id)
    assert found.email == "test@example.com"
```

**Testing guidelines:**
- Unit tests: Mock external dependencies (database, APIs)
- Integration tests: Use real database, mock external APIs
- E2E tests: Use real database AND real external APIs (or staging environments)
- All tests must clean up after themselves

### Configuration Management

**Pattern:** Pydantic Settings with environment variables

**Configuration file:** `src/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 10
    
    # Redis
    redis_url: str
    
    # External APIs
    salesforce_client_id: str
    salesforce_client_secret: str
    stripe_api_key: str
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Usage:**
```python
from src.core.config import settings

# Access settings
database_url = settings.database_url
```

**Environment variables:**
- Development: `.env` (not committed)
- Staging/Production: Injected by deployment system (Kubernetes secrets)

**Secrets:** Never commit secrets to repository
- Use `.env.example` as template
- Real secrets in `.env` (gitignored)
- In CI: Use GitHub secrets

### Authentication

**Pattern:** JWT-based authentication with role-based access control (RBAC)

**Middleware:** `src/api/middleware/auth.py`

**Adding authentication to endpoints:**
```python
from src.api.middleware.auth import require_auth, get_current_user

@router.get("/customers/{customer_id}")
@require_auth(roles=["admin", "analyst"])
def get_customer(customer_id: str, current_user = Depends(get_current_user)):
    # current_user is automatically injected
    logger.info("Customer accessed", customer_id=customer_id, user_id=current_user.id)
    return customer_service.get_customer(customer_id)
```

**Roles:**
- `admin`: Full access (read + write)
- `analyst`: Read-only access (queries, reports)
- `api_client`: Programmatic access (external integrations)

**JWT tokens:**
- Expiration: 1 hour
- Refresh tokens: 7 days
- Algorithm: RS256 (RSA signatures)
- Public key: Loaded from environment

**Testing with authentication:**
```python
# tests/integration/api/test_customers.py
from tests.helpers.auth import create_test_token

def test_get_customer_requires_auth(client):
    response = client.get("/customers/123")
    assert response.status_code == 401  # Unauthorized

def test_get_customer_with_auth(client):
    token = create_test_token(roles=["analyst"])
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/customers/123", headers=headers)
    assert response.status_code == 200
```
```

---

### 6. External Integrations

**Purpose:** Document how your project interacts with external services.

**Include:**
- List of external dependencies
- Authentication methods
- Rate limits and quotas
- Error handling for external failures
- Local development alternatives (mocks, stubs)

**Example:**
```markdown
## External Integrations

### Salesforce

**Purpose:** Customer data source (accounts, contacts, opportunities)

**Integration type:** Batch sync (every 6 hours)

**Implementation:** `src/integrations/salesforce/client.py`

**Authentication:** OAuth2
- Client ID: Environment variable `SALESFORCE_CLIENT_ID`
- Client Secret: Environment variable `SALESFORCE_CLIENT_SECRET`
- Token refresh: Automatic (handled by library)

**Rate limits:**
- 15,000 API calls per 24 hours
- Current usage: ~2,000 calls per sync (well below limit)

**Error handling:**
- Transient errors (5xx): Retry with exponential backoff (max 3 retries)
- Auth errors (401): Refresh token and retry once
- Rate limit (429): Wait until rate limit resets (check `Retry-After` header)
- Data errors (400): Log error, skip record, continue processing

**Local development:**
- Use `SALESFORCE_MOCK_MODE=true` to enable mock data
- Mock data: `tests/fixtures/salesforce_mock_data.json`
- No real API calls made in mock mode

**Testing:**
```python
# Integration test with mock
@pytest.mark.integration
def test_salesforce_sync_mock_mode(monkeypatch):
    monkeypatch.setenv("SALESFORCE_MOCK_MODE", "true")
    client = SalesforceClient()
    result = client.sync_customers()
    assert len(result) > 0
```

---

### Stripe

**Purpose:** Payment data source (charges, subscriptions, invoices)

**Integration type:** Hybrid
- Webhook (real-time): Payment events
- Batch sync (daily): Full reconciliation

**Implementation:**
- Webhook handler: `src/integrations/stripe/webhook_handler.py`
- Batch sync: `src/integrations/stripe/sync.py`

**Authentication:** API Key
- Secret key: Environment variable `STRIPE_API_KEY`
- Webhook signing secret: `STRIPE_WEBHOOK_SECRET`

**Webhook events we handle:**
- `charge.succeeded`: Payment completed
- `charge.failed`: Payment failed
- `customer.subscription.created`: New subscription
- `customer.subscription.deleted`: Subscription canceled

**Webhook verification:**
```python
# Verify webhook signature (IMPORTANT - prevents spoofing)
import stripe
from src.core.config import settings

def verify_webhook(payload: bytes, signature: str) -> stripe.Event:
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
        return event
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
```

**Local development:**
- Use Stripe CLI to forward webhooks: `stripe listen --forward-to localhost:8000/webhooks/stripe`
- Or use mock mode: `STRIPE_MOCK_MODE=true`

**Rate limits:**
- 100 requests per second
- Current usage: ~10 requests per second (well below limit)

---

### Segment

**Purpose:** Real-time event tracking (user behavior, product usage)

**Integration type:** Webhook (real-time)

**Implementation:** `src/integrations/segment/webhook_handler.py`

**Authentication:** Webhook signature verification
- Shared secret: Environment variable `SEGMENT_WEBHOOK_SECRET`

**Events we track:**
- `page`: Page views
- `track`: Custom events (button clicks, form submissions)
- `identify`: User identification

**Webhook setup:**
- Segment dashboard → Connections → Destinations → Webhooks
- URL: `https://api.yourcompany.com/webhooks/segment`
- Shared secret: Generate and store in environment

**Local development:**
- Use ngrok to expose local server: `ngrok http 8000`
- Configure Segment webhook to ngrok URL
- Or use mock events: `POST /webhooks/segment/mock`

**Error handling:**
- Always return 200 (even if processing fails)
- Log errors and send to dead letter queue
- Segment will retry failed webhooks with exponential backoff
```

---

### 7. Troubleshooting Guide

**Purpose:** Help agents debug common issues quickly.

**Include:**
- Common error messages and their solutions
- Diagnostic commands
- Where to find logs
- Known issues and workarounds

**Example:**
```markdown
## Troubleshooting

### Quick Diagnostics

**Before debugging anything, run these checks:**

```bash
# 1. Check environment variables loaded
env | grep -E "(DATABASE_URL|REDIS_URL|SALESFORCE)"

# 2. Check services running
docker-compose ps

# 3. Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# 4. Check Redis connection
redis-cli ping

# 5. Check API health
curl http://localhost:8000/health
```

---

### Common Issues

#### Issue: "Database connection failed"

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
could not connect to server: Connection refused
```

**Causes & Solutions:**

1. **PostgreSQL not running:**
   ```bash
   docker-compose up -d postgres
   ```

2. **Wrong DATABASE_URL:**
   ```bash
   # Check current value
   echo $DATABASE_URL
   
   # Should be (for local dev):
   # postgresql://cdp:cdp@localhost:5432/cdp
   
   # Fix in .env file
   ```

3. **Database not initialized:**
   ```bash
   # Run migrations
   alembic upgrade head
   ```

4. **Port conflict (5432 already in use):**
   ```bash
   # Find what's using port 5432
   lsof -i :5432
   
   # Kill it or change docker-compose port
   ```

---

#### Issue: "Import error: No module named 'src'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
```

**Cause:** Package not installed in editable mode

**Solution:**
```bash
pip install -e .
```

**Verify:**
```bash
pip list | grep customer-data-platform
# Should show: customer-data-platform 0.1.0 /path/to/project
```

---

#### Issue: "Salesforce sync fails with 401 Unauthorized"

**Symptoms:**
```
salesforce.exceptions.AuthenticationFailed: 401 Unauthorized
```

**Causes & Solutions:**

1. **Token expired:**
   ```python
   # Token auto-refreshes, but might be broken
   # Delete cached token and re-authenticate
   rm -f .salesforce_token_cache
   ```

2. **Wrong credentials:**
   ```bash
   # Check environment variables
   echo $SALESFORCE_CLIENT_ID
   echo $SALESFORCE_CLIENT_SECRET
   
   # Should match Salesforce Connected App credentials
   ```

3. **IP restrictions:**
   - Check Salesforce Connected App settings
   - Your IP might not be whitelisted
   - Contact Salesforce admin to add your IP

---

#### Issue: "Tests failing with 'database locked'"

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Using SQLite for tests (NOT recommended)

**Solution:** Use PostgreSQL for tests
```bash
# Set test database URL
export DATABASE_URL="postgresql://test:test@localhost:5432/cdp_test"

# Create test database
createdb cdp_test

# Run tests
pytest
```

**Why?** We use PostgreSQL in production, so tests should too (avoids subtle bugs)

---

#### Issue: "Webhook not receiving events"

**Symptoms:**
- Stripe/Segment webhooks configured but no events received

**Diagnostic:**
```bash
# Check webhook endpoint is accessible
curl -X POST http://localhost:8000/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Should return 200 (even if signature verification fails)
```

**Common causes:**

1. **Local development (webhooks can't reach localhost):**
   ```bash
   # Use ngrok to expose local server
   ngrok http 8000
   
   # Configure webhook URL to ngrok URL
   # https://abcd1234.ngrok.io/webhooks/stripe
   ```

2. **Wrong webhook URL:**
   - Check Stripe/Segment dashboard
   - Should be: `https://yourdomain.com/webhooks/{provider}`

3. **Signature verification failing:**
   ```bash
   # Check webhook secret is correct
   echo $STRIPE_WEBHOOK_SECRET
   
   # Should match Stripe dashboard → Developers → Webhooks → Signing secret
   ```

4. **Firewall blocking:**
   - Check firewall rules
   - Ensure port 8000 is open (or whatever port you're using)

---

### Where to Find Logs

**Application logs:**
```bash
# Docker logs
docker-compose logs -f api

# Local development (logs to stdout)
# Just look at terminal where uvicorn is running
```

**Database logs:**
```bash
docker-compose logs -f postgres
```

**Background worker logs:**
```bash
# Celery worker logs
celery -A src.worker worker --loglevel=debug
```

**External API logs:**
- Salesforce: Salesforce dashboard → Setup → Event Monitoring
- Stripe: Stripe dashboard → Developers → Logs
- Segment: Segment dashboard → Debugger

---

### Known Issues

#### Issue: Slow customer profile queries

**Status:** Known performance issue (tracked in #234)

**Workaround:** Use caching
```python
from src.core.cache import cache

@cache(ttl=300)  # Cache for 5 minutes
def get_customer_profile(customer_id: str):
    return customer_service.get_customer(customer_id)
```

**Permanent fix:** Database index optimization (planned for Q2)

---

#### Issue: Salesforce sync occasionally skips records

**Status:** Known issue with Salesforce API pagination (tracked in #456)

**Impact:** ~0.1% of records might be skipped during sync

**Mitigation:** Daily full reconciliation catches missed records

**Workaround:** If you need immediate sync, run manual sync:
```bash
python scripts/manual_salesforce_sync.py --force-full-sync
```

---

### Getting Help

**Still stuck?**

1. **Check detailed docs:** `docs/` directory has deep-dive guides
2. **Search issues:** GitHub issues might have solution
3. **Ask team:** #engineering-help Slack channel
4. **Check logs:** Often the error message has the answer

**When asking for help, include:**
- What you were trying to do
- Exact error message (full stack trace)
- Output of quick diagnostics (see above)
- What you've tried already
```

---

### 8. Testing Strategy

**Purpose:** Explain how to test effectively in this codebase.

**Include:**
- Test organization and structure
- Testing tools and frameworks
- Test data management
- Mocking strategies
- CI/CD testing pipeline

**Example:**
```markdown
## Testing Strategy

### Test Pyramid

We follow the test pyramid principle:

```
        /\
       /  \
      / E2E\      ← Few (5-10) - Slow, full system
     /------\
    /  Intg  \    ← Some (50-100) - Medium speed, with database
   /----------\
  /    Unit    \  ← Many (500+) - Fast, isolated
 /--------------\
```

**Unit tests (70%):**
- Fast (entire suite runs in <30 seconds)
- No external dependencies (mock everything)
- Test business logic in isolation

**Integration tests (25%):**
- Medium speed (entire suite runs in <5 minutes)
- Real database, mocked external APIs
- Test components working together

**E2E tests (5%):**
- Slow (entire suite runs in <30 minutes)
- Real database, real external APIs (staging)
- Test critical user journeys end-to-end

---

### Test Organization

```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/                   # Test data
│   ├── customers.json
│   ├── events.json
│   └── salesforce_mock.json
├── helpers/                    # Test utilities
│   ├── auth.py                 # Test token generation
│   ├── factories.py            # Test data factories
│   └── assertions.py           # Custom assertions
├── unit/                       # Unit tests
│   ├── services/
│   │   ├── test_customer_service.py
│   │   └── test_segment_service.py
│   └── utils/
│       └── test_validators.py
├── integration/                # Integration tests
│   ├── repositories/
│   │   └── test_customer_repo.py
│   ├── api/
│   │   ├── test_customer_endpoints.py
│   │   └── test_auth_middleware.py
│   └── integrations/
│       └── test_salesforce_client.py
└── e2e/                        # End-to-end tests
    └── test_customer_journey.py
```

---

### Test Fixtures

**Shared fixtures:** `tests/conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine("postgresql://test:test@localhost:5432/cdp_test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()  # Rollback after each test
    session.close()

@pytest.fixture
def api_client():
    """Create test API client."""
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)
```

**Using fixtures:**
```python
def test_create_customer(db_session):
    # db_session is automatically injected
    repo = CustomerRepository(session=db_session)
    customer = repo.create(Customer(email="test@example.com"))
    assert customer.id is not None
```

---

### Test Data Management

**Pattern:** Factories for test data creation

**Factory file:** `tests/helpers/factories.py`

```python
from src.models.customer import Customer
from src.models.event import Event

class CustomerFactory:
    """Factory for creating test customers."""
    
    @staticmethod
    def create(
        email: str = "test@example.com",
        name: str = "Test User",
        **kwargs
    ) -> Customer:
        return Customer(email=email, name=name, **kwargs)
    
    @staticmethod
    def create_batch(count: int) -> list[Customer]:
        return [
            CustomerFactory.create(
                email=f"test{i}@example.com",
                name=f"Test User {i}"
            )
            for i in range(count)
        ]

class EventFactory:
    """Factory for creating test events."""
    
    @staticmethod
    def create(
        customer_id: str,
        event_type: str = "page_view",
        **kwargs
    ) -> Event:
        return Event(
            customer_id=customer_id,
            event_type=event_type,
            **kwargs
        )
```

**Usage:**
```python
from tests.helpers.factories import CustomerFactory

def test_customer_segmentation(db_session):
    # Create test data easily
    customers = CustomerFactory.create_batch(10)
    for customer in customers:
        db_session.add(customer)
    db_session.commit()
    
    # Test segmentation logic
    segment = segment_service.create_segment(criteria={...})
    assert len(segment.customers) > 0
```

---

### Mocking External APIs

**Pattern:** Use `pytest-mock` for mocking

**Unit test example (mock repository):**
```python
from unittest.mock import Mock
from src.services.customer_service import CustomerService

def test_get_customer_not_found():
    # Create mock repository
    mock_repo = Mock()
    mock_repo.find_by_id.return_value = None
    
    # Inject mock into service
    service = CustomerService(repository=mock_repo)
    
    # Test
    result = service.get_customer("nonexistent")
    assert result.is_err()
    
    # Verify mock was called
    mock_repo.find_by_id.assert_called_once_with("nonexistent")
```

**Integration test example (mock external API):**
```python
import pytest
from unittest.mock import patch
from src.integrations.salesforce.client import SalesforceClient

@pytest.mark.integration
@patch('src.integrations.salesforce.client.requests.get')
def test_salesforce_sync(mock_get, db_session):
    # Mock external API response
    mock_get.return_value.json.return_value = {
        "records": [
            {"Id": "123", "Email": "test@example.com", "Name": "Test"}
        ]
    }
    mock_get.return_value.status_code = 200
    
    # Test with mocked external API
    client = SalesforceClient()
    result = client.sync_customers()
    
    # Verify results
    assert len(result) == 1
    assert result[0].email == "test@example.com"
    
    # Verify API was called
    mock_get.assert_called_once()
```

---

### Running Tests

**All tests:**
```bash
pytest
```

**Specific test file:**
```bash
pytest tests/unit/services/test_customer_service.py
```

**Specific test function:**
```bash
pytest tests/unit/services/test_customer_service.py::test_get_customer_not_found
```

**By marker:**
```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Only E2E tests
pytest -m e2e

# Skip slow tests
pytest -m "not slow"
```

**With coverage:**
```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

**Parallel execution:**
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (faster)
pytest -n auto
```

---

### CI/CD Testing Pipeline

**GitHub Actions workflow:** `.github/workflows/test.yml`

**Pipeline stages:**

1. **Lint:**
   ```bash
   black --check src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

2. **Unit tests:**
   ```bash
   pytest -m unit --cov=src --cov-fail-under=80
   ```

3. **Integration tests:**
   ```bash
   # Start test database
   docker-compose -f docker-compose.test.yml up -d
   
   # Run integration tests
   pytest -m integration
   ```

4. **E2E tests (only on main branch):**
   ```bash
   # Deploy to staging
   ./scripts/deploy-staging.sh
   
   # Run E2E tests against staging
   pytest -m e2e --base-url=https://staging.api.yourcompany.com
   ```

**Test database in CI:**
- Uses PostgreSQL service container
- Database created fresh for each test run
- Automatically torn down after tests complete

**When tests fail:**
- Check GitHub Actions logs
- Artifacts include coverage reports and test results
- Slack notification sent to #engineering-failures
```

---

### 9. Deployment and Operations

**Purpose:** Help agents understand how code gets deployed and monitored.

**Include:**
- Deployment process
- Environment configuration (dev, staging, prod)
- Monitoring and observability
- Rollback procedures

**Example:**
```markdown
## Deployment

### Environments

We have three environments:

**Development (local):**
- Local Docker Compose setup
- Uses local PostgreSQL and Redis
- External APIs in mock mode
- URL: http://localhost:8000

**Staging:**
- Kubernetes cluster (staging namespace)
- Real database (isolated from production)
- Real external APIs (Salesforce/Stripe sandbox accounts)
- URL: https://staging.api.yourcompany.com
- Auto-deployed on merge to `develop` branch

**Production:**
- Kubernetes cluster (production namespace)
- Production database (with backups)
- Real external APIs (production credentials)
- URL: https://api.yourcompany.com
- Deployed via manual approval after staging validation

---

### Deployment Process

**Step 1: Code review and merge**
```bash
# Create feature branch
git checkout -b feature/add-customer-segments

# Make changes, commit, push
git push origin feature/add-customer-segments

# Create pull request on GitHub
# CI runs tests automatically
# Requires approval from 1+ reviewer

# After approval, merge to develop
```

**Step 2: Staging deployment (automatic)**
- Merge to `develop` triggers GitHub Actions
- Builds Docker image
- Pushes to container registry
- Deploys to staging Kubernetes cluster
- Runs E2E tests against staging
- Slack notification on completion

**Step 3: Production deployment (manual)**
```bash
# After staging validation, create production PR
git checkout main
git merge develop
git push origin main

# GitHub Actions workflow pauses for approval
# Engineering lead clicks "Approve deployment" in GitHub
# Deploys to production Kubernetes cluster
# Slack notification on completion
```

---

### Configuration per Environment

**Environment variables by environment:**

| Variable | Development | Staging | Production |
|----------|------------|---------|------------|
| `DATABASE_URL` | `postgresql://cdp:cdp@localhost:5432/cdp` | Kubernetes secret | Kubernetes secret |
| `REDIS_URL` | `redis://localhost:6379` | Kubernetes secret | Kubernetes secret |
| `SALESFORCE_CLIENT_ID` | Mock mode (no real value) | Sandbox account | Production account |
| `STRIPE_API_KEY` | Mock mode (no real value) | Test API key | Live API key |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` |
| `ENVIRONMENT` | `development` | `staging` | `production` |

**How to update secrets:**
```bash
# Staging
kubectl create secret generic cdp-secrets \
  --from-literal=database-url="..." \
  --namespace=staging \
  --dry-run=client -o yaml | kubectl apply -f -

# Production (requires admin access)
kubectl create secret generic cdp-secrets \
  --from-literal=database-url="..." \
  --namespace=production \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

### Monitoring

**Application metrics:**
- **Tool:** Prometheus + Grafana
- **Dashboard:** https://grafana.yourcompany.com/d/cdp-overview
- **Key metrics:**
  - Request rate (requests per second)
  - Error rate (5xx responses)
  - Latency (p50, p95, p99)
  - Database connection pool usage

**Logs:**
- **Tool:** ELK Stack (Elasticsearch + Logstash + Kibana)
- **Dashboard:** https://kibana.yourcompany.com
- **Query examples:**
  - All errors: `level:ERROR`
  - Customer operations: `customer_id:*`
  - Slow operations: `duration:>1000`

**Alerts:**
- **Tool:** PagerDuty + Slack
- **Conditions:**
  - Error rate > 5% for 5 minutes → Page on-call engineer
  - Latency p95 > 1s for 10 minutes → Slack alert to #engineering
  - Database connection pool > 80% → Slack alert to #engineering
  - External API failures > 10% → Slack alert to #engineering

---

### Rollback Procedure

**If deployment causes issues:**

**Option 1: Hotfix (for minor issues)**
```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/fix-critical-bug

# Fix issue, commit, push
git push origin hotfix/fix-critical-bug

# Create PR, get fast-track approval
# Merge and deploy (skips staging, goes straight to prod)
```

**Option 2: Rollback (for major issues)**
```bash
# Rollback to previous deployment
kubectl rollout undo deployment/cdp-api -n production

# Verify rollback
kubectl rollout status deployment/cdp-api -n production

# Check health
curl https://api.yourcompany.com/health
```

**Option 3: Database rollback (if migrations are involved)**
```bash
# SSH into production pod
kubectl exec -it deployment/cdp-api -n production -- /bin/bash

# Rollback migration
alembic downgrade -1

# Restart application
kubectl rollout restart deployment/cdp-api -n production
```

**After rollback:**
- Investigate root cause
- Fix issue in feature branch
- Test thoroughly in staging
- Deploy fix following normal process
```

---

### 10. Performance Considerations

**Purpose:** Document performance requirements and optimization strategies.

**Example:**
```markdown
## Performance

### Response Time Targets

| Endpoint Type | Target | Max Acceptable |
|--------------|--------|----------------|
| GET (single record) | < 100ms | < 500ms |
| GET (list with pagination) | < 200ms | < 1s |
| POST/PUT (simple) | < 200ms | < 1s |
| POST/PUT (complex) | < 1s | < 5s |
| Background jobs | N/A | < 5 minutes |

### Optimization Strategies

**Database:**
- Use indexes for frequently queried fields
- Use `select_related()` / `joinedload()` to avoid N+1 queries
- Use database connection pooling
- Cache frequently accessed data in Redis

**API:**
- Implement pagination (default page size: 100, max: 1000)
- Use async endpoints for I/O-bound operations
- Implement rate limiting (100 requests per minute per user)

**Background jobs:**
- Use Celery for async processing
- Batch operations when possible (e.g., bulk inserts)
```

---

## Maintenance and Updates

### When to Update Project AGENTS.md

**Always update when:**
- Adding new modules or services
- Changing architecture or patterns
- Adding external integrations
- Discovering new troubleshooting steps
- Changing development workflow

**Never duplicate:**
- Language standards (belongs in warehouse language context, e.g. `python.md`)
- Organizational policies (belongs in warehouse `global.md`)
- Generic patterns (promote to warehouse instead)

### Review Frequency

- **Monthly:** Review for accuracy and completeness
- **After incidents:** Add troubleshooting sections for issues encountered
- **During onboarding:** Ask new developers what was confusing or missing

---

## Template: Starting a New Project

When starting a new project, use this template:

```markdown
# Project: [Project Name]

## Purpose

[What this project does, who uses it, why it exists]

## Architecture

[High-level architecture overview]

**See:** `docs/architecture.md` for detailed diagrams

## Code Organization

[Directory structure with explanations]

### Key Modules

[List key modules with entry points and responsibilities]

## Development Workflow

### First-Time Setup

[Step-by-step setup instructions]

### Running Locally

[How to start the application]

### Running Tests

[How to run tests]

## Key Patterns

[Project-specific patterns that differ from organizational standards]

## External Integrations

[List of external dependencies with auth, rate limits, error handling]

## Troubleshooting

### Quick Diagnostics

[Commands to run before debugging]

### Common Issues

[List of known issues with solutions]

## Deployment

[Deployment process and environments]

## Related Documentation

- Architecture: `docs/architecture.md`
- API Documentation: `docs/api.md`
- Database Schema: `docs/schema.md`
```

---

## Summary

Project-level AGENTS.md is your **project's instruction manual for AI agents**. It should be:

1. **Specific:** Focus on THIS codebase, not generic patterns
2. **Actionable:** Provide commands, examples, and step-by-step guides
3. **Current:** Keep it updated as the project evolves
4. **Scannable:** Use clear headings and structure for quick navigation
5. **Complete:** Cover architecture, development, testing, deployment, troubleshooting

**Remember:** The goal is to reduce agent onboarding time and increase consistency. If an agent keeps asking the same questions or making the same mistakes, add that knowledge to AGENTS.md.

---

**Related Documentation:**
- [AGENTS.md Architecture Guide](./agents-md-architecture.md) - Three-tier context model
- [Agentic Warehouse Design](../agentic-warehouse-design.md) - Overall architecture
- [Warehouse Contribution Guide](../../guides/warehouse-contribution-guide.md) - How to contribute patterns back
