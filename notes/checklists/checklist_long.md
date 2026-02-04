# Intelligent Document Analyst: Complete Build Guide
## Three Projects, One System - Step-by-Step

> **The Goal:** Build a production-ready AI backend demonstrating system design mastery through progressive complexity.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Project 1: RESTful API Foundation](#project-1-restful-api-foundation)
- [Project 2: RAG System](#project-2-rag-system)
- [Project 3: Agentic AI Platform](#project-3-agentic-ai-platform)
- [The One Rule](#the-one-rule)

---

## Project Overview

### System Evolution

```
Phase 1: RESTful API
    ↓ (adds document processing)
Phase 2: RAG System
    ↓ (adds autonomous intelligence)
Phase 3: Agentic AI Platform
```

---

### Quick Reference: Complete Project Structure

#### All Phases at a Glance

- **Project 1**: RESTful API (Phases 1.1-1.7)

✅ Foundation, Authentication, Rate Limiting, Snowflake IDs, URL Shortener, Notifications, Production

- **Project 2**: RAG System (Phases 2.1-2.7)

✅ Document Upload, Text Extraction, Chunking, Vector Embeddings, RAG, Hybrid Search, Optimization

- **Project 3**: Agentic AI (Phases 3.1-3.8)

✅ Agents, Event Streaming, Triggers, Real-Time Chat, Consistent Hashing, Scaling, Observability, Deployment

---

### System Design Topics Covered

1. ✅ Rate Limiting (Token Bucket Algorithm)
2. ✅ Unique ID Generation (Snowflake)
3. ✅ URL Shortening (Base62)
4. ✅ Notification System (Push/Pull)
5. ✅ Document Processing Pipeline (Web Crawler pattern)
6. ✅ Object Storage (S3-compatible)
7. ✅ Vector Search (Semantic similarity)
8. ✅ Hybrid Search (Vector + Keyword + RRF)
9. ✅ RAG Architecture (Retrieval-Augmented Generation)
10. ✅ Agentic AI (LangGraph state machines)
11. ✅ Event Streaming (Kafka/Redpanda)
12. ✅ Real-Time Communication (WebSockets)
13. ✅ Consistent Hashing (Distributed systems)
14. ✅ Horizontal Scaling (Load balancing)
15. ✅ Observability (Metrics, monitoring, alerting)

---

### Complete Tech Stack / Technologies Used

| Category | Technology | Purpose | Used In |
|----------|-----------|---------|---------|
| **API Framework** | FastAPI | Async API framework | All |
| **Database** | PostgreSQL + SQLModel | Primary data store | All |
| **Caching** | Redis | Caching + rate limiting + blacklisting | All |
| **Container** | Docker + Docker Compose | Containerization | All |
| **CI/CD** | GitHub Actions | Deployment pipeline | All |
| **Auth** | JWT + OAuth2 | Authentication + Security | Project 1 |
| **File Storage** | MinIO (S3-compatible) | Document storage | Project 2 |
| **Vector DB** | Qdrant | Semantic search | Project 2 |
| **Embeddings** | Sentence Transformers | Vector generation | Project 2 |
| **Task Queue** | Celery | | Project 2  |
| **LLM** | Anthropic Claude Sonnet 4 | AI responses | Projects 2 & 3 |
| **Agent Framework** | LangGraph | Autonomous AI | Project 3 |
| **Event Stream** | Redpanda (Kafka-compatible) | Event streaming | Project 3 |
| **Monitoring** | Prometheus + Grafana | Observability | Project 3 |
| **Cloud** | AWS ECS | Production hosting | Project 3 |

---

### Final Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (nginx)                   │
└───────────────┬─────────────────┬─────────────────┬─────────┘
                │                 │                 │
       ┌────────▼────────┐ ┌─────▼──────┐ ┌───────▼────────┐
       │  FastAPI API 1  │ │  API 2     │ │  API 3         │
       │  (Stateless)    │ │            │ │                │
       └────────┬────────┘ └─────┬──────┘ └───────┬────────┘
                │                 │                 │
                └─────────────────┼─────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼─────┐    ┌─────────┐   │    ┌──────────┐   ┌────▼────┐
   │PostgreSQL│    │  Redis  │   │    │  Qdrant  │   │  MinIO  │
   │          │    │ (cache) │   │    │ (vector) │   │(storage)│
   └──────────┘    └─────────┘   │    └──────────┘   └─────────┘
                                  │
                         ┌────────▼────────┐
                         │    Redpanda     │
                         │ (Event Stream)  │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
            ┌───────▼──────┐ ┌───▼───────┐ ┌──▼──────────┐
            │ Celery Worker│ │  Triggers │ │  Analytics  │
            │  (RAG Tasks) │ │ (Agents)  │ │             │
            └──────────────┘ └───────────┘ └─────────────┘
                                  │
                         ┌────────▼────────┐
                         │  Prometheus +   │
                         │    Grafana      │
                         │ (Observability) │
                         └─────────────────┘
```


---

# PROJECT 1: RESTful API Foundation

## Overview

**What You're Building:** A secure, scalable API where users can register, authenticate, upload documents, and receive notifications.

**Architecture Pattern:** Layered (N-Tier) Architecture

**System Design Topics:**
- Rate Limiting (Token Bucket Algorithm)
- Unique ID Generation (Twitter Snowflake)
- URL Shortening (Base62 encoding)
- Notification System (Push/Pull patterns)

---

## Architecture: Layered (N-Tier)

```
┌─────────────────────────────────────┐
│     Presentation Layer              │
│  FastAPI Routes + Dependencies      │
│  /auth, /users, /documents          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Business Logic Layer           │
│  Route Handlers (inline for now)   │
│  Validation + Business Rules        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       Data Access Layer             │
│  SQLModel ORM + Repositories        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Database Layer              │
│  PostgreSQL (ACID, Transactions)    │
└─────────────────────────────────────┘
```

---

## Tech Stack: Project 1

### Core Technologies
```
FastAPI 0.115+         - Async API framework
PostgreSQL 16+         - Primary database
SQLModel              - ORM (SQLAlchemy + Pydantic)
Pydantic              - Data validation
Alembic               - Database migrations
Redis 7+              - Caching + Rate limiting
Python-JOSE           - JWT handling
Passlib               - Password hashing (bcrypt)
```

### Project Structure
```
intelligent-document-analyst/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # DB connection
│   ├── dependencies.py         # Auth dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py            # User model
│   │   ├── document.py        # Document model
│   │   └── notification.py    # Notification model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py            # Auth endpoints
│   │   ├── users.py           # User endpoints
│   │   ├── documents.py       # Document endpoints
│   │   └── notifications.py   # Notification endpoints
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limit.py      # Rate limiting
│   └── utils/
│       ├── __init__.py
│       ├── auth.py            # JWT utilities
│       ├── snowflake.py       # ID generation
│       └── url_shortener.py   # URL shortening
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── test_auth.py
│   ├── test_documents.py
│   └── test_rate_limit.py
├── alembic/
│   ├── versions/
│   └── env.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Phase 1.1: Foundation

### What You're Building
Basic CRUD API with database connectivity.

### Tasks
1. **Project Setup**
   - [ ] Create GitHub repository
   - [ ] Initialize FastAPI project structure
   - [ ] Set up Docker Compose (Postgres + Redis)
   - [ ] Create `.env.example` with config

2. **Database Models**
   - [ ] Create User model (id, email, hashed_password, created_at)
   - [ ] Create Document model (id, title, owner_id, created_at)
   - [ ] Set up Alembic migrations
   - [ ] Configure async database connection

3. **Basic Endpoints**
   - [ ] `GET /health` - Health check
   - [ ] `POST /auth/register` - User registration
   - [ ] `POST /documents` - Create document
   - [ ] `GET /documents` - List user documents
   - [ ] `GET /documents/{id}` - Get single document
   - [ ] `PUT /documents/{id}` - Update document
   - [ ] `DELETE /documents/{id}` - Delete document

4. **Testing**
   - [ ] Set up pytest with fixtures
   - [ ] Test each endpoint
   - [ ] Test validation errors
   - [ ] Achieve 70%+ test coverage

### Design Patterns

**1. Repository Pattern (Implicit via ORM)**
```python
# app/models/document.py
from sqlmodel import Field, SQLModel
from datetime import datetime

class Document(SQLModel, table=True):
    id: int = Field(primary_key=True)
    title: str = Field(index=True)
    content: str | None
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Usage in routes - ORM acts as repository
@router.get("/documents")
async def list_documents(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    statement = select(Document).where(Document.owner_id == current_user.id)
    result = await session.execute(statement)
    return result.scalars().all()
```

**Why:** Abstracts database operations, makes testing easier.

**2. Dependency Injection**
```python
# app/dependencies.py
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Usage
@router.post("/documents")
async def create_document(
    data: DocumentCreate,
    session: AsyncSession = Depends(get_session)  # Injected!
):
    document = Document(**data.dict())
    session.add(document)
    await session.commit()
    return document
```

**Why:** Loose coupling, easy to mock for tests, reusable code.

**3. Data Transfer Object (DTO)**
```python
# app/models/document.py
from pydantic import BaseModel

class DocumentCreate(BaseModel):
    title: str
    content: str | None

class DocumentResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True
```

**Why:** Separates API interface from database schema, validates input.

### Learning Outcomes

**Technical Skills:**
- ✅ Async Python (async/await, asyncio)
- ✅ FastAPI fundamentals (routing, dependencies, validation)
- ✅ PostgreSQL with async SQLModel
- ✅ Database migrations with Alembic
- ✅ RESTful API design principles
- ✅ Pydantic data validation

**System Design Concepts:**
- ✅ Layered architecture benefits and trade-offs
- ✅ Database schema design (normalization, indexes)
- ✅ API versioning strategies
- ✅ Error handling patterns

**Interview Questions You Can Answer:**
- "Explain the difference between sync and async in Python"
- "How do you structure a FastAPI application?"
- "What's the difference between SQLAlchemy and SQLModel?"
- "How do you handle database migrations in production?"

### Done When
- [ ] All endpoints return correct status codes
- [ ] Can register user and CRUD documents via Swagger UI
- [ ] Tests pass with 70%+ coverage
- [ ] Docker Compose runs everything successfully
- [ ] Alembic migrations work (upgrade/downgrade)

---

## Phase 1.2: Authentication & Security

### What You're Building
Secure authentication system with JWT tokens and proper password handling.

### Tasks
1. **Authentication System**
   - [ ] Implement password hashing with bcrypt
   - [ ] Create JWT token generation (access + refresh)
   - [ ] `POST /auth/login` - Login endpoint
   - [ ] `POST /auth/refresh` - Refresh token endpoint
   - [ ] `POST /auth/logout` - Logout (token blacklist)

2. **Authorization**
   - [ ] Create authentication dependency (`get_current_user`)
   - [ ] Protect all document endpoints
   - [ ] Implement ownership verification
   - [ ] Add role-based access (optional: admin role)

3. **Security Headers**
   - [ ] CORS configuration
   - [ ] HTTPS enforcement
   - [ ] Security headers middleware

4. **Testing**
   - [ ] Test login with valid/invalid credentials
   - [ ] Test protected endpoints without token (401)
   - [ ] Test accessing other user's documents (403)
   - [ ] Test expired tokens

### Design Patterns

**1. Strategy Pattern (Token Generation)**
```python
# app/utils/auth.py
from abc import ABC, abstractmethod
from jose import jwt

class TokenStrategy(ABC):
    @abstractmethod
    def create_token(self, data: dict) -> str:
        pass

class JWTStrategy(TokenStrategy):
    def create_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=30)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

class RefreshTokenStrategy(TokenStrategy):
    def create_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

# Usage
access_token = JWTStrategy().create_token({"sub": user.email})
refresh_token = RefreshTokenStrategy().create_token({"sub": user.email})
```

**Why:** Makes it easy to swap authentication strategies (e.g., OAuth later).

**2. Decorator Pattern (Auth Dependency)**
```python
# app/dependencies.py
from fastapi import Depends, HTTPException
from jose import jwt, JWTError

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)

    user = await session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise HTTPException(status_code=401)

    return user

# Protects endpoint
@router.get("/documents")
async def list_documents(current_user: User = Depends(get_current_user)):
    # Only authenticated users can access
    return {"documents": current_user.documents}
```

**Why:** Reusable authentication logic, declarative protection.

**3. Middleware Pattern (Security Headers)**
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

**Why:** Cross-cutting concerns handled centrally, applies to all endpoints.

### Learning Outcomes

**Technical Skills:**
- ✅ JWT authentication flow
- ✅ Password hashing and verification
- ✅ OAuth2 password flow
- ✅ Token refresh mechanisms
- ✅ Security best practices (CORS, headers)

**System Design Concepts:**
- ✅ Stateless authentication vs sessions
- ✅ Token expiration and refresh strategies
- ✅ Authentication vs Authorization
- ✅ Security header importance

**Interview Questions You Can Answer:**
- "Explain how JWT authentication works"
- "What's the difference between access and refresh tokens?"
- "How do you secure a REST API?"
- "Session-based vs token-based auth - trade-offs?"

### Done When
- [ ] Login returns JWT tokens
- [ ] Protected endpoints require valid token
- [ ] Cannot access other user's documents
- [ ] Token refresh works
- [ ] Security headers present in responses

---

## Phase 1.3: Rate Limiting (System Design)

### What You're Building
Rate limiting system to prevent API abuse using Token Bucket Algorithm.

### System Design: Rate Limiting

**Problem:** Users can abuse API by sending unlimited requests.

**Solution:** Token Bucket Algorithm
- Each user has a "bucket" with tokens
- Each request consumes 1 token
- Bucket refills at constant rate
- If bucket empty, request rejected (429)

**Architecture:**
```
Request → Middleware → Redis Check → Token Available?
                                        ├─ Yes → Process → Decrement Token
                                        └─ No  → 429 Error (Rate Limited)
```

### Tasks
1. **Redis Setup**
   - [ ] Add Redis to Docker Compose
   - [ ] Configure Redis connection
   - [ ] Test Redis connectivity

2. **Rate Limiter Implementation**
   - [ ] Implement Token Bucket algorithm
   - [ ] Create rate limit middleware
   - [ ] Different limits per user tier (free: 10/min, paid: 100/min)
   - [ ] Return rate limit headers (X-RateLimit-*)

3. **Testing**
   - [ ] Test rate limit enforcement
   - [ ] Test rate limit headers
   - [ ] Test rate limit reset
   - [ ] Test different user tiers

### Design Patterns

**1. Token Bucket Algorithm**
```python
# app/middleware/rate_limit.py
import redis.asyncio as redis
import time

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: int):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second

    async def consume(self, user_id: int, tokens: int = 1) -> tuple[bool, dict]:
        key = f"rate_limit:{user_id}"
        now = time.time()

        # Get current state
        pipe = redis_client.pipeline()
        pipe.hgetall(key)
        result = await pipe.execute()
        state = result[0]

        if not state:
            # First request - initialize bucket
            await redis_client.hset(key, mapping={
                "tokens": self.capacity - tokens,
                "last_refill": now
            })
            await redis_client.expire(key, 60)
            return True, {"remaining": self.capacity - tokens}

        # Calculate refill
        last_refill = float(state["last_refill"])
        current_tokens = float(state["tokens"])
        time_passed = now - last_refill
        refill_amount = time_passed * self.refill_rate

        # Refill tokens (up to capacity)
        current_tokens = min(self.capacity, current_tokens + refill_amount)

        if current_tokens >= tokens:
            # Allow request
            new_tokens = current_tokens - tokens
            await redis_client.hset(key, mapping={
                "tokens": new_tokens,
                "last_refill": now
            })
            return True, {"remaining": int(new_tokens)}
        else:
            # Deny request
            return False, {"remaining": 0, "retry_after": 60}

# Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    # Get user (if authenticated)
    token = request.headers.get("authorization")
    if not token:
        return await call_next(request)  # Don't rate limit unauthenticated

    user = await get_user_from_token(token)

    # Determine rate limit based on user tier
    if user.tier == "paid":
        bucket = TokenBucket(capacity=100, refill_rate=100/60)  # 100/min
    else:
        bucket = TokenBucket(capacity=10, refill_rate=10/60)    # 10/min

    # Check rate limit
    allowed, info = await bucket.consume(user.id)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={
                "X-RateLimit-Limit": "10" if user.tier == "free" else "100",
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(info["retry_after"])
            }
        )

    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    return response
```

**Why:** Smooth rate limiting, better UX than fixed window.

**2. Middleware Chain Pattern**
```python
# Multiple middleware execute in order
app.add_middleware(CORSMiddleware)        # 1st
app.add_middleware(RateLimitMiddleware)   # 2nd
app.add_middleware(LoggingMiddleware)     # 3rd
```

**Why:** Separation of concerns, composable behavior.

### Learning Outcomes

**Technical Skills:**
- ✅ Redis operations (GET, SET, EXPIRE, HSET)
- ✅ Rate limiting algorithms
- ✅ Middleware implementation
- ✅ HTTP headers for rate limiting

**System Design Concepts:**
- ✅ Token Bucket vs Fixed Window vs Sliding Window
- ✅ Distributed rate limiting (Redis)
- ✅ Rate limiting strategies (IP, user, endpoint)
- ✅ Handling rate limit errors gracefully

**Interview Questions You Can Answer:**
- "Design a rate limiting system"
- "Explain Token Bucket algorithm"
- "How do you implement rate limiting in a distributed system?"
- "What's the difference between rate limiting algorithms?"

### Done When
- [ ] Rate limiting enforces limits correctly
- [ ] Returns 429 when limit exceeded
- [ ] Rate limit headers present
- [ ] Can handle 1000 req/s without crashing
- [ ] Different tiers have different limits

---

## Phase 1.4: Unique ID Generation (System Design)

### What You're Building
Distributed unique ID generator using Twitter Snowflake algorithm.

### System Design: Snowflake IDs

**Problem:** Auto-increment IDs don't scale in distributed systems.

**Solution:** Snowflake IDs (64-bit)
```
Structure:
│ 41 bits: Timestamp │ 10 bits: Machine │ 12 bits: Sequence │
│   (milliseconds)   │   (datacenter    │   (per machine    │
│                    │    + worker)     │    per ms)        │
```

**Benefits:**
- ✅ Globally unique
- ✅ Time-ordered (sortable)
- ✅ No coordination needed
- ✅ Can generate 4096 IDs per machine per millisecond

### Tasks
1. **Snowflake Implementation**
   - [ ] Create SnowflakeID generator class
   - [ ] Thread-safe implementation
   - [ ] Handle clock skew
   - [ ] Configuration for datacenter/worker IDs

2. **Integration**
   - [ ] Replace auto-increment IDs with Snowflake
   - [ ] Update database models
   - [ ] Create migration
   - [ ] Update all ID references

3. **Testing**
   - [ ] Generate 10,000 IDs - all unique
   - [ ] IDs are sortable by time
   - [ ] Thread-safe (concurrent generation)
   - [ ] Handle clock backwards

### Design Patterns

**1. Singleton Pattern (ID Generator)**
```python
# app/utils/snowflake.py
import time
import threading

class SnowflakeID:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, datacenter_id: int, worker_id: int):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, datacenter_id: int, worker_id: int):
        if not hasattr(self, 'initialized'):
            self.datacenter_id = datacenter_id
            self.worker_id = worker_id
            self.sequence = 0
            self.last_timestamp = -1
            self.lock = threading.Lock()

            # Epoch (custom start time)
            self.epoch = 1288834974657  # Twitter's epoch

            # Bit lengths
            self.datacenter_bits = 5
            self.worker_bits = 5
            self.sequence_bits = 12

            # Max values
            self.max_datacenter = (1 << self.datacenter_bits) - 1
            self.max_worker = (1 << self.worker_bits) - 1
            self.max_sequence = (1 << self.sequence_bits) - 1

            self.initialized = True

    def generate(self) -> int:
        with self.lock:
            timestamp = self._current_timestamp()

            # Clock moved backwards - wait
            if timestamp < self.last_timestamp:
                raise Exception(f"Clock moved backwards by {self.last_timestamp - timestamp}ms")

            if timestamp == self.last_timestamp:
                # Same millisecond - increment sequence
                self.sequence = (self.sequence + 1) & self.max_sequence
                if self.sequence == 0:
                    # Sequence overflow - wait for next millisecond
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                # New millisecond - reset sequence
                self.sequence = 0

            self.last_timestamp = timestamp

            # Build ID
            return (
                ((timestamp - self.epoch) << 22) |
                (self.datacenter_id << 17) |
                (self.worker_id << 12) |
                self.sequence
            )

    def _current_timestamp(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp

# Initialize once
id_generator = SnowflakeID(datacenter_id=1, worker_id=1)

# Usage
new_id = id_generator.generate()
```

**Why:** Thread-safe singleton ensures consistent ID generation.

**2. Factory Pattern (ID Creation)**
```python
# app/models/base.py
from sqlmodel import Field, SQLModel

class BaseModel(SQLModel):
    id: int = Field(default_factory=lambda: id_generator.generate(), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# All models inherit
class Document(BaseModel, table=True):
    title: str
    content: str
```

**Why:** Centralized ID generation logic, DRY principle.

### Learning Outcomes

**Technical Skills:**
- ✅ Distributed ID generation
- ✅ Bit manipulation in Python
- ✅ Thread safety (locks, mutexes)
- ✅ Handling clock skew

**System Design Concepts:**
- ✅ Snowflake algorithm internals
- ✅ UUID vs Snowflake vs Auto-increment
- ✅ Distributed system IDs
- ✅ Time-based ordering in databases

**Interview Questions You Can Answer:**
- "Design a distributed unique ID generator"
- "Explain Twitter Snowflake algorithm"
- "What happens if the clock goes backward?"
- "UUID vs Snowflake - which and when?"

### Done When
- [ ] Can generate unique IDs
- [ ] IDs are sortable by creation time
- [ ] Thread-safe (tested with concurrent generation)
- [ ] All models use Snowflake IDs
- [ ] Database migration successful

---

## Phase 1.5: URL Shortener (System Design)

### What You're Building
URL shortening service for sharing documents.

### System Design: URL Shortener

**Problem:** Long document URLs are hard to share.

**Solution:** Base62 encoding
- Generate short code from ID
- Store mapping in database
- Redirect on access

**Example:**
```
Long URL:  https://api.example.com/documents/1234567890123456
Short URL: https://api.example.com/d/aBc123
```

### Tasks
1. **Base62 Encoding**
   - [ ] Implement Base62 encode/decode
   - [ ] Generate 7-character codes (3.5 trillion URLs)

2. **Short URL Model**
   - [ ] Create ShortURL model (short_code, document_id, created_at, clicks)
   - [ ] Add database index on short_code
   - [ ] Track click analytics

3. **Endpoints**
   - [ ] `POST /shorten` - Create short URL
   - [ ] `GET /{short_code}` - Redirect to document
   - [ ] `GET /shorten/{short_code}/stats` - View analytics

4. **Testing**
   - [ ] Test Base62 encoding/decoding
   - [ ] Test shortening and redirect
   - [ ] Test collision handling
   - [ ] Test analytics tracking

### Design Patterns

**1. Encoder Pattern (Base62)**
```python
# app/utils/url_shortener.py
import string

class Base62Encoder:
    ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
    BASE = len(ALPHABET)

    @classmethod
    def encode(cls, num: int) -> str:
        if num == 0:
            return cls.ALPHABET[0]

        result = []
        while num:
            result.append(cls.ALPHABET[num % cls.BASE])
            num //= cls.BASE

        return ''.join(reversed(result))

    @classmethod
    def decode(cls, s: str) -> int:
        num = 0
        for char in s:
            num = num * cls.BASE + cls.ALPHABET.index(char)
        return num

# Generate short code
def generate_short_code(document_id: int) -> str:
    encoded = Base62Encoder.encode(document_id)
    return encoded.zfill(7)  # Pad to 7 characters

# Usage
short_code = generate_short_code(123456)  # → "w7e"
```

**Why:** Compact representation, URL-safe characters.

**2. Redirect Pattern**
```python
# app/routes/shorten.py
from fastapi.responses import RedirectResponse

@router.get("/{short_code}")
async def redirect_short_url(
    short_code: str,
    session: AsyncSession = Depends(get_session)
):
    # Look up short URL
    statement = select(ShortURL).where(ShortURL.short_code == short_code)
    result = await session.execute(statement)
    short_url = result.scalar_one_or_none()

    if not short_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Increment click count
    short_url.clicks += 1
    await session.commit()

    # Redirect to original URL
    original_url = f"/documents/{short_url.document_id}"
    return RedirectResponse(url=original_url, status_code=301)
```

**Why:** 301 redirect (permanent) for SEO, analytics before redirect.

**3. Builder Pattern (Short URL Creation)**
```python
class ShortURLBuilder:
    def __init__(self):
        self._short_url = ShortURL()

    def for_document(self, document_id: int):
        self._short_url.document_id = document_id
        return self

    def with_code(self, code: str):
        self._short_url.short_code = code
        return self

    def with_custom_code(self, custom: str):
        # Validate custom code
        if len(custom) < 4 or len(custom) > 10:
            raise ValueError("Custom code must be 4-10 characters")
        self._short_url.short_code = custom
        return self

    async def build(self, session: AsyncSession) -> ShortURL:
        # Check for collision
        existing = await session.exec(
            select(ShortURL).where(ShortURL.short_code == self._short_url.short_code)
        ).first()

        if existing:
            # Handle collision - add random suffix
            import random
            suffix = ''.join(random.choices(Base62Encoder.ALPHABET, k=2))
            self._short_url.short_code += suffix

        return self._short_url

# Usage
short_url = await (
    ShortURLBuilder()
    .for_document(doc_id)
    .with_code(generate_short_code(doc_id))
    .build(session)
)
```

**Why:** Flexible creation, handles edge cases, testable.

### Learning Outcomes

**Technical Skills:**
- ✅ Base62 encoding/decoding
- ✅ HTTP redirects (301 vs 302)
- ✅ Collision handling strategies
- ✅ Analytics tracking

**System Design Concepts:**
- ✅ URL shortening architecture
- ✅ Hash collision resolution
- ✅ Base conversion algorithms
- ✅ Caching strategies for hot links

**Interview Questions You Can Answer:**
- "Design a URL shortening service (like bit.ly)"
- "How do you handle hash collisions?"
- "How do you scale a URL shortener?"
- "Base62 vs Base64 - which and why?"

### Done When
- [ ] Can shorten document URLs
- [ ] Redirects work correctly
- [ ] Short codes are 7 characters
- [ ] Handles collisions gracefully
- [ ] Analytics tracked (clicks)

---

## Phase 1.6: Notification System (System Design)

### What You're Building
Notification system for document events with multiple delivery channels.

### System Design: Notifications

**Problem:** Users need to know about important events.

**Solution:** Event-driven notifications
```
Event → Notification Service → [Email, Webhook, In-App]
```

**Push vs Pull:**
- **Push:** Server sends notification (webhooks, emails)
- **Pull:** Client polls for notifications (in-app)

### Tasks
1. **Notification Model**
   - [ ] Create Notification model (user_id, type, title, message, read_at)
   - [ ] Support multiple types (document_uploaded, query_completed)
   - [ ] Add database indexes

2. **Notification Endpoints**
   - [ ] `POST /notifications` - Create notification (internal)
   - [ ] `GET /notifications` - List user notifications
   - [ ] `GET /notifications/unread` - Unread count
   - [ ] `PATCH /notifications/{id}/read` - Mark as read
   - [ ] `DELETE /notifications/{id}` - Delete notification

3. **Delivery Channels**
   - [ ] In-app notifications (database)
   - [ ] Webhook delivery (HTTP POST)
   - [ ] Email delivery (optional: with background task)

4. **Testing**
   - [ ] Test notification creation
   - [ ] Test webhook delivery
   - [ ] Test marking as read
   - [ ] Test filtering unread

### Design Patterns

**1. Observer Pattern (Event Listeners)**
```python
# app/services/notification_service.py
from typing import Protocol, List

class NotificationChannel(Protocol):
    async def send(self, notification: Notification) -> bool:
        ...

class InAppChannel:
    async def send(self, notification: Notification) -> bool:
        # Already saved to database
        return True

class WebhookChannel:
    async def send(self, notification: Notification) -> bool:
        user = await get_user(notification.user_id)
        if not user.webhook_url:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    user.webhook_url,
                    json={
                        "type": notification.type,
                        "title": notification.title,
                        "message": notification.message,
                        "timestamp": notification.created_at.isoformat()
                    },
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return False

class EmailChannel:
    async def send(self, notification: Notification) -> bool:
        # Implement email sending
        pass

class NotificationService:
    def __init__(self):
        self.channels: List[NotificationChannel] = [
            InAppChannel(),
            WebhookChannel(),
            # EmailChannel(),
        ]

    async def notify(self, notification: Notification):
        # Send to all channels
        for channel in self.channels:
            try:
                await channel.send(notification)
            except Exception as e:
                logger.error(f"Channel {channel.__class__.__name__} failed: {e}")

notification_service = NotificationService()

# Usage
await notification_service.notify(Notification(
    user_id=user.id,
    type="document_uploaded",
    title="Document Processed",
    message=f"Your document '{doc.title}' has been processed"
))
```

**Why:** Easy to add new channels, decoupled from business logic.

**2. Background Task Pattern**
```python
# app/routes/documents.py
from fastapi import BackgroundTasks

async def send_notification_task(user_id: int, type: str, message: str):
    notification = Notification(
        user_id=user_id,
        type=type,
        message=message
    )
    session.add(notification)
    await session.commit()

    # Send via channels
    await notification_service.notify(notification)

@router.post("/documents/")
async def create_document(
    data: DocumentCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    # Create document
    document = Document(**data.dict(), owner_id=current_user.id)
    session.add(document)
    await session.commit()

    # Send notification in background
    bg_tasks.add_task(
        send_notification_task,
        current_user.id,
        "document_uploaded",
        f"Document '{data.title}' uploaded successfully"
    )

    return document
```

**Why:** Non-blocking, improves response time, retryable.

**3. Template Method Pattern (Notification Formatting)**
```python
class NotificationTemplate:
    def format(self, **kwargs) -> dict:
        return {
            "title": self.get_title(**kwargs),
            "message": self.get_message(**kwargs),
            "action": self.get_action(**kwargs)
        }

    def get_title(self, **kwargs) -> str:
        raise NotImplementedError

    def get_message(self, **kwargs) -> str:
        raise NotImplementedError

    def get_action(self, **kwargs) -> str:
        return None

class DocumentUploadedTemplate(NotificationTemplate):
    def get_title(self, document_title: str, **kwargs) -> str:
        return "Document Uploaded"

    def get_message(self, document_title: str, **kwargs) -> str:
        return f"Your document '{document_title}' has been uploaded successfully"

    def get_action(self, document_id: int, **kwargs) -> str:
        return f"/documents/{document_id}"

class QueryCompletedTemplate(NotificationTemplate):
    def get_title(self, **kwargs) -> str:
        return "Query Completed"

    def get_message(self, query: str, **kwargs) -> str:
        return f"Your query '{query}' has been processed"

    def get_action(self, query_id: int, **kwargs) -> str:
        return f"/queries/{query_id}"

# Usage
template = DocumentUploadedTemplate()
notification_data = template.format(
    document_title="My Report",
    document_id=123
)
```

**Why:** Consistent formatting, easy to add notification types.

### Learning Outcomes

**Technical Skills:**
- ✅ Background task processing
- ✅ Webhook implementation
- ✅ Event-driven architecture basics
- ✅ Push vs Pull notification patterns

**System Design Concepts:**
- ✅ Notification system architecture
- ✅ Push vs Pull trade-offs
- ✅ Webhook reliability (retries, timeouts)
- ✅ At-least-once delivery

**Interview Questions You Can Answer:**
- "Design a notification system"
- "Push vs Pull notifications - trade-offs?"
- "How do you ensure webhook delivery?"
- "How do you handle notification preferences?"

### Done When
- [ ] Notifications created on events
- [ ] In-app notifications work
- [ ] Webhook delivery works
- [ ] Can mark notifications as read
- [ ] Unread count accurate

---

## Phase 1.7: Testing & Production Hardening

### What You're Building
Comprehensive test suite and production-ready configurations.

### Tasks
1. **Testing Suite**
   - [ ] Unit tests for all routes
   - [ ] Integration tests for auth flow
   - [ ] Test database transactions
   - [ ] Test error cases (404, 422, 500, 429)
   - [ ] Test rate limiting edge cases
   - [ ] Mock external services
   - [ ] Achieve 80%+ coverage

2. **Logging & Monitoring**
   - [ ] Structured logging (JSON format)
   - [ ] Request/response logging middleware
   - [ ] Performance metrics (request duration)
   - [ ] Error tracking

3. **Docker & Deployment**
   - [ ] Production Dockerfile (multi-stage build)
   - [ ] Docker Compose for full stack
   - [ ] Environment variable management
   - [ ] Health check endpoint
   - [ ] Graceful shutdown

4. **Documentation**
   - [ ] API documentation (auto-generated Swagger)
   - [ ] README with setup instructions
   - [ ] Architecture diagram
   - [ ] Deployment guide

### Design Patterns

**1. Test Fixture Pattern**
```python
# tests/conftest.py
import pytest
from sqlmodel import create_engine, Session
from fastapi.testclient import TestClient

@pytest.fixture(scope="function")
async def db_session():
    # Create test database
    engine = create_engine("sqlite:///test.db")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # Cleanup
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def client(db_session):
    # Override dependencies
    app.dependency_overrides[get_session] = lambda: db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()

@pytest.fixture
async def authenticated_user(client, db_session):
    # Create user
    user = User(email="test@example.com", hashed_password="...")
    db_session.add(user)
    db_session.commit()

    # Login
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password"
    })

    token = response.json()["access_token"]
    return user, token

# Usage in tests
def test_create_document(client, authenticated_user):
    user, token = authenticated_user

    response = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test Doc", "description": "Test"}
    )

    assert response.status_code == 201
```

**Why:** Reusable test setup, isolated tests, easy mocking.

**2. Factory Pattern (Test Data)**
```python
# tests/factories.py
from faker import Faker
import factory

fake = Faker()

class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda _: fake.email())
    hashed_password = "hashed_password"
    is_active = True

class DocumentFactory(factory.Factory):
    class Meta:
        model = Document

    title = factory.LazyAttribute(lambda _: fake.sentence())
    content = factory.LazyAttribute(lambda _: fake.text())
    owner_id = factory.SubFactory(UserFactory)

# Usage
user = UserFactory.create()
document = DocumentFactory.create(owner_id=user.id)
```

**Why:** Consistent test data, easy to create complex objects.

**3. Middleware Chain Pattern (Logging)**
```python
# app/middleware/logging.py
import logging
import json
import time

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    logger.info("request_started", extra={
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host
    })

    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Log response
        logger.info("request_completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration * 1000
        })

        return response

    except Exception as e:
        duration = time.time() - start_time

        # Log error
        logger.error("request_failed", extra={
            "method": request.method,
            "path": request.url.path,
            "error": str(e),
            "duration_ms": duration * 1000
        })

        raise
```

**Why:** Centralized logging, structured logs for analysis.

### Learning Outcomes

**Technical Skills:**
- ✅ Comprehensive testing strategies
- ✅ Pytest fixtures and mocking
- ✅ Structured logging (JSON)
- ✅ Docker multi-stage builds
- ✅ Environment configuration

**System Design Concepts:**
- ✅ Testing pyramid (unit, integration, e2e)
- ✅ Logging best practices
- ✅ Health check patterns
- ✅ Graceful shutdown

**Interview Questions You Can Answer:**
- "How do you test a FastAPI application?"
- "What's your logging strategy?"
- "How do you dockerize a Python app?"
- "What are health checks and why are they important?"

### Done When
- [ ] 80%+ test coverage
- [ ] All tests pass
- [ ] Docker Compose runs entire stack
- [ ] Logs are structured (JSON)
- [ ] Health check endpoint works
- [ ] Can deploy to production

---

## Project 1: Complete! 🎉

### What You Built
- ✅ RESTful API with 15+ endpoints
- ✅ JWT authentication with refresh tokens
- ✅ Rate limiting (Token Bucket Algorithm)
- ✅ Snowflake ID generation
- ✅ URL shortening service
- ✅ Multi-channel notification system
- ✅ 80%+ test coverage
- ✅ Production-ready Docker setup

### Skills Gained
| Category | Skills |
|----------|--------|
| **Backend** | FastAPI, Async Python, PostgreSQL, SQLModel, Alembic |
| **System Design** | Rate Limiting, Distributed IDs, URL Shortening, Notifications |
| **Patterns** | Layered Architecture, Repository, Dependency Injection, Observer |
| **Production** | Testing, Logging, Docker, CI/CD |

### Architecture Mastered
**Layered (N-Tier) Architecture**
- Clear separation of concerns
- Testable components
- Scalable foundation

### Interview Readiness
You can now confidently answer:
- "Design a rate limiting system"
- "Implement distributed unique ID generation"
- "Build a URL shortener"
- "Design a notification system"
- "How do you structure a REST API?"
- "Async vs sync - when and why?"

---

# PROJECT 2: RAG System

## Overview

**What You're Building:** AI-powered document analysis system where users upload documents, and the system extracts text, generates embeddings, and enables semantic search with AI-generated answers.

**Architecture Pattern:** Pipes & Filters + Background Processing

**System Design Topics:**
- Document Processing Pipeline (Web Crawler pattern)
- Object Storage (S3-compatible)
- Search Systems (Vector + Hybrid)
- Background Task Processing

---

## Architecture: Pipes & Filters + Background Processing

```
Upload → Extract → Chunk → Embed → Store → Query
  │        │         │       │       │       │
MinIO   Celery    Celery  Celery  Qdrant  Claude

Each stage is a "filter" that transforms data
Celery queues connect the "pipes" between filters
```

**Key Characteristics:**
- ✅ Each stage independent
- ✅ Stages can be scaled independently
- ✅ Easy to add new processing steps
- ✅ Failure in one stage doesn't crash others

---

## Tech Stack: Project 2

### New Technologies (adds to Project 1)
```
MinIO                  - S3-compatible object storage
Qdrant 1.7+           - Vector database
Sentence Transformers  - Open-source embeddings
Celery 5+             - Distributed task queue
PyPDF2                - PDF text extraction
python-docx           - DOCX text extraction
tiktoken              - Token counting (OpenAI)
Anthropic SDK         - Claude API
```

### Project Structure (extends Project 1)
```
app/
├── tasks/                    # NEW
│   ├── __init__.py
│   ├── document_processing.py
│   ├── embedding.py
│   └── rag.py
├── services/                 # NEW
│   ├── __init__.py
│   ├── storage.py           # MinIO service
│   ├── vector_store.py      # Qdrant service
│   └── llm_service.py       # Claude service
├── models/
│   ├── chunk.py             # NEW - Chunk model
│   └── query.py             # NEW - Query history
└── routes/
    ├── upload.py            # NEW - File upload
    └── query.py             # NEW - RAG queries
```

---

## Phase 2.1: Document Upload & Storage

### What You're Building
File upload system with S3-compatible object storage.

### System Design: Object Storage

**Problem:** Storing files on local filesystem doesn't scale.

**Solution:** S3-compatible object storage (MinIO)
- Scalable and durable
- API-compatible with AWS S3
- Separated from application servers
- Easy to backup and replicate

**Architecture:**
```
Client → API → MinIO → Disk
           ↓
        Postgres (metadata only)
```

### Tasks
1. **MinIO Setup**
   - [ ] Add MinIO to Docker Compose
   - [ ] Create storage buckets
   - [ ] Configure access policies
   - [ ] Test connectivity

2. **File Upload**
   - [ ] `POST /documents/upload` - Multipart file upload
   - [ ] Support PDF, TXT, DOCX, MD
   - [ ] Validate file types and sizes
   - [ ] Generate unique filenames

3. **Document Model Updates**
   - [ ] Add file_path, file_size, mime_type fields
   - [ ] Add status field (uploading, processing, completed, failed)
   - [ ] Add error_message field
   - [ ] Create migration

4. **Download Endpoint**
   - [ ] `GET /documents/{id}/download` - Download file from MinIO
   - [ ] Set proper Content-Type headers
   - [ ] Verify ownership

5. **Testing**
   - [ ] Test file upload (PDF, DOCX, TXT)
   - [ ] Test file size limits
   - [ ] Test invalid file types
   - [ ] Test download

### Design Patterns

**1. Adapter Pattern (Storage Abstraction)**
```python
# app/services/storage.py
from abc import ABC, abstractmethod
from minio import Minio
from minio.error import S3Error

class StorageAdapter(ABC):
    @abstractmethod
    async def upload(self, bucket: str, path: str, data: bytes) -> bool:
        pass

    @abstractmethod
    async def download(self, bucket: str, path: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, bucket: str, path: str) -> bool:
        pass

class MinIOAdapter(StorageAdapter):
    def __init__(self, endpoint: str, access_key: str, secret_key: str):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
        self._ensure_bucket("documents")

    def _ensure_bucket(self, bucket: str):
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    async def upload(self, bucket: str, path: str, data: bytes) -> bool:
        try:
            self.client.put_object(
                bucket,
                path,
                io.BytesIO(data),
                length=len(data)
            )
            return True
        except S3Error as e:
            logger.error(f"Upload failed: {e}")
            return False

    async def download(self, bucket: str, path: str) -> bytes:
        response = self.client.get_object(bucket, path)
        return response.read()

    async def delete(self, bucket: str, path: str) -> bool:
        try:
            self.client.remove_object(bucket, path)
            return True
        except S3Error:
            return False

# Can easily swap implementations
storage = MinIOAdapter(
    endpoint="minio:9000",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key
)

# Alternative: LocalStorageAdapter for development
# storage = LocalStorageAdapter(base_path="/tmp/storage")
```

**Why:** Easy to swap storage backends (MinIO, S3, local), testable.

**2. Chain of Responsibility (File Validation)**
```python
# app/services/validators.py
from abc import ABC, abstractmethod

class FileValidator(ABC):
    def __init__(self):
        self.next_validator: FileValidator | None = None

    def set_next(self, validator: 'FileValidator'):
        self.next_validator = validator
        return validator

    async def validate(self, file: UploadFile) -> tuple[bool, str]:
        result, message = await self._validate(file)

        if not result:
            return False, message

        if self.next_validator:
            return await self.next_validator.validate(file)

        return True, "Valid"

    @abstractmethod
    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        pass

class FileSizeValidator(FileValidator):
    def __init__(self, max_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__()
        self.max_size = max_size

    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset

        if size > self.max_size:
            return False, f"File too large. Max: {self.max_size} bytes"
        return True, "Size OK"

class FileTypeValidator(FileValidator):
    def __init__(self, allowed_types: list[str]):
        super().__init__()
        self.allowed_types = allowed_types

    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        if file.content_type not in self.allowed_types:
            return False, f"Invalid file type. Allowed: {self.allowed_types}"
        return True, "Type OK"

class FileNameValidator(FileValidator):
    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        if not file.filename or len(file.filename) > 255:
            return False, "Invalid filename"
        return True, "Filename OK"

# Build validation chain
validator = FileSizeValidator(max_size=10*1024*1024)
validator.set_next(
    FileTypeValidator(["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"])
).set_next(
    FileNameValidator()
)

# Usage
@router.post("/documents/upload")
async def upload_document(file: UploadFile):
    # Validate
    valid, message = await validator.validate(file)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    # Process upload...
```

**Why:** Easy to add/remove validators, testable, reusable.

**3. Background Task Pattern (Async Processing)**
```python
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Validate
    valid, message = await validator.validate(file)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    # Generate unique path
    file_id = id_generator.generate()
    file_path = f"{current_user.id}/{file_id}_{file.filename}"

    # Read file content
    content = await file.read()

    # Upload to MinIO
    await storage.upload("documents", file_path, content)

    # Save metadata to database
    document = Document(
        id=file_id,
        title=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        owner_id=current_user.id,
        status="processing"
    )
    session.add(document)
    await session.commit()

    # Process in background (Celery task)
    from app.tasks.document_processing import process_document
    process_document.delay(file_id)

    return {
        "id": file_id,
        "status": "processing",
        "message": "Document uploaded. Processing started."
    }
```

**Why:** Non-blocking upload, immediate response, scalable processing.

### Learning Outcomes

**Technical Skills:**
- ✅ Object storage (S3 API)
- ✅ Multipart file uploads
- ✅ File validation
- ✅ MinIO client library

**System Design Concepts:**
- ✅ Object storage vs file storage
- ✅ File upload patterns
- ✅ Metadata vs content separation
- ✅ Async processing triggers

**Interview Questions You Can Answer:**
- "Design a file storage system"
- "How do you handle large file uploads?"
- "Local storage vs object storage - trade-offs?"
- "How do you validate uploaded files?"

### Done When
- [ ] Files upload to MinIO
- [ ] Metadata saved to Postgres
- [ ] Can download files
- [ ] File validation works
- [ ] Status tracking implemented

---

## Phase 2.2: Text Extraction Pipeline

### What You're Building
Background workers that extract text from various document formats.

### System Design: Document Processing Pipeline

**Problem:** Text extraction is slow and blocks API responses.

**Solution:** Background processing with Celery
```
Upload → Queue → Worker → Extract → Queue → Next Stage
```

**Architecture:**
```
FastAPI → Redis (Queue) → Celery Worker → MinIO
                              ↓
                          Postgres (status)
```

### Tasks
1. **Celery Setup**
   - [ ] Configure Celery with Redis broker
   - [ ] Create Celery app
   - [ ] Add worker to Docker Compose
   - [ ] Test task execution

2. **Text Extractors**
   - [ ] PDF extractor (PyPDF2)
   - [ ] DOCX extractor (python-docx)
   - [ ] Plain text extractor
   - [ ] Markdown extractor

3. **Processing Task**
   - [ ] Download file from MinIO
   - [ ] Extract text based on file type
   - [ ] Save extracted text to database
   - [ ] Update document status
   - [ ] Handle errors and retries

4. **Status Tracking**
   - [ ] `GET /documents/{id}/status` - Check processing status
   - [ ] Return progress percentage
   - [ ] Return error messages

5. **Testing**
   - [ ] Test extraction for each file type
   - [ ] Test error handling
   - [ ] Test retry logic
   - [ ] Test status updates

### Design Patterns

**1. Strategy Pattern (Text Extraction)**
```python
# app/tasks/extractors.py
from abc import ABC, abstractmethod
import PyPDF2
from docx import Document as DocxDocument

class TextExtractor(ABC):
    @abstractmethod
    def can_extract(self, mime_type: str) -> bool:
        pass

    @abstractmethod
    async def extract(self, content: bytes) -> str:
        pass

class PDFExtractor(TextExtractor):
    def can_extract(self, mime_type: str) -> bool:
        return mime_type == "application/pdf"

    async def extract(self, content: bytes) -> str:
        pdf = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        return text

class DOCXExtractor(TextExtractor):
    def can_extract(self, mime_type: str) -> bool:
        return mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    async def extract(self, content: bytes) -> str:
        doc = DocxDocument(io.BytesIO(content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

class PlainTextExtractor(TextExtractor):
    def can_extract(self, mime_type: str) -> bool:
        return mime_type in ["text/plain", "text/markdown"]

    async def extract(self, content: bytes) -> str:
        return content.decode('utf-8')

class ExtractionFactory:
    def __init__(self):
        self.extractors = [
            PDFExtractor(),
            DOCXExtractor(),
            PlainTextExtractor()
        ]

    def get_extractor(self, mime_type: str) -> TextExtractor:
        for extractor in self.extractors:
            if extractor.can_extract(mime_type):
                return extractor
        raise ValueError(f"No extractor for mime type: {mime_type}")

extraction_factory = ExtractionFactory()
```

**Why:** Easy to add new extractors, testable, follows Open/Closed Principle.

**2. Template Method Pattern (Processing Pipeline)**
```python
# app/tasks/document_processing.py
from celery import Task
from app.celery_app import celery_app

class ProcessingTask(Task):
    """Base task with error handling and logging"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        document_id = args[0]
        # Update document status
        with get_db() as session:
            document = session.get(Document, document_id)
            document.status = "failed"
            document.error_message = str(exc)
            session.commit()

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} completed successfully")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {task_id} retrying: {exc}")

@celery_app.task(base=ProcessingTask, bind=True, max_retries=3)
def process_document(self, document_id: int):
    try:
        # 1. Get document from database
        with get_db() as session:
            document = session.get(Document, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

        # 2. Download from MinIO
        content = await storage.download("documents", document.file_path)

        # 3. Extract text
        extractor = extraction_factory.get_extractor(document.mime_type)
        text = await extractor.extract(content)

        # 4. Save extracted text
        with get_db() as session:
            document = session.get(Document, document_id)
            document.content = text
            document.status = "completed"
            session.commit()

        # 5. Chain to next task: chunking
        from app.tasks.chunking import chunk_document
        chunk_document.delay(document_id)

        return {"document_id": document_id, "text_length": len(text)}

    except Exception as e:
        # Log error
        logger.error(f"Processing failed for {document_id}: {e}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

```

**Why:** Consistent error handling, retry logic, task chaining.

**3. Chain of Responsibility (Pipeline Stages)**
```python
# Task chaining - each task triggers the next
process_document.delay(doc_id)
    ↓
chunk_document.delay(doc_id)
    ↓
embed_chunks.delay(doc_id)
    ↓
update_search_index.delay(doc_id)
```

**Why:** Loose coupling, easy to add/remove stages, independent scaling.

### Learning Outcomes

**Technical Skills:**
- ✅ Celery task queue
- ✅ Background processing
- ✅ PDF/DOCX text extraction
- ✅ Task chaining and retry logic

**System Design Concepts:**
- ✅ Pipes and Filters architecture
- ✅ Worker pool patterns
- ✅ Task queue vs message queue
- ✅ Error handling in distributed systems

**Interview Questions You Can Answer:**
- "Design a document processing pipeline"
- "How do you handle background tasks at scale?"
- "Explain Celery architecture"
- "How do you retry failed tasks?"

### Done When
- [ ] Celery worker running
- [ ] Text extracted from all file types
- [ ] Text saved to database
- [ ] Status updates work
- [ ] Error handling and retries work

---

## Phase 2.3: Document Chunking

### What You're Building
Split documents into semantic chunks for better retrieval.

### System Design: Chunking Strategy

**Problem:** Documents are too long for context windows.

**Solution:** Chunk with overlap
```
Document (10,000 tokens)
    ↓
Chunk 1 (500 tokens) → Chunk 2 (500 tokens) → ... → Chunk N
         ↑ 50 overlap ↑
```

**Trade-offs:**
- **Chunk too small:** Loses context
- **Chunk too large:** Less precise retrieval
- **No overlap:** Misses cross-boundary concepts
- **Too much overlap:** Redundant storage/computation

### Tasks
1. **Chunk Model**
   - [ ] Create Chunk model (document_id, text, position, tokens, embedding_id)
   - [ ] Add indexes (document_id, position)
   - [ ] Create migration

2. **Chunking Algorithm**
   - [ ] Implement token-based chunking (tiktoken)
   - [ ] Chunk size: 500 tokens
   - [ ] Overlap: 50 tokens
   - [ ] Handle edge cases (very short/long documents)

3. **Chunking Task**
   - [ ] Celery task: chunk_document
   - [ ] Split text into chunks
   - [ ] Save chunks to database
   - [ ] Chain to embedding task

4. **Testing**
   - [ ] Test chunking algorithm
   - [ ] Test overlap calculation
   - [ ] Test edge cases (empty doc, single sentence)
   - [ ] Verify token counts

### Design Patterns

**1. Iterator Pattern (Chunk Generation)**
```python
# app/services/chunking.py
import tiktoken
from typing import Iterator

class DocumentChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def chunk(self, text: str) -> Iterator[tuple[str, int, int]]:
        """
        Yields: (chunk_text, start_position, token_count)
        """
        tokens = self.encoder.encode(text)
        position = 0

        while position < len(tokens):
            # Get chunk
            end = position + self.chunk_size
            chunk_tokens = tokens[position:end]

            # Decode chunk
            chunk_text = self.encoder.decode(chunk_tokens)
            token_count = len(chunk_tokens)

            yield chunk_text, position, token_count

            # Move position (with overlap)
            position = end - self.overlap

            # Prevent infinite loop on tiny documents
            if position <= 0:
                break

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

chunker = DocumentChunker(chunk_size=500, overlap=50)

# Usage
for chunk_text, position, tokens in chunker.chunk(document.content):
    print(f"Chunk at position {position}: {tokens} tokens")
```

**Why:** Memory-efficient (generator), flexible chunk sizes, testable.

**2. Builder Pattern (Chunk Creation)**
```python
class ChunkBuilder:
    def __init__(self):
        self._chunks = []

    def from_document(self, document: Document):
        self._document = document
        return self

    def with_chunker(self, chunker: DocumentChunker):
        self._chunker = chunker
        return self

    async def build(self) -> list[Chunk]:
        chunks = []

        for chunk_text, position, tokens in self._chunker.chunk(self._document.content):
            chunk = Chunk(
                document_id=self._document.id,
                text=chunk_text,
                position=position,
                tokens=tokens,
                created_at=datetime.utcnow()
            )
            chunks.append(chunk)

        return chunks

# Usage
chunks = await (
    ChunkBuilder()
    .from_document(document)
    .with_chunker(chunker)
    .build()
)
```

**Why:** Flexible chunk creation, easy to test, clear intent.

**3. Repository Pattern (Chunk Storage)**
```python
class ChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        self.session.add_all(chunks)
        await self.session.commit()
        return chunks

    async def get_by_document(self, document_id: int) -> list[Chunk]:
        statement = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.position)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_by_document(self, document_id: int):
        statement = delete(Chunk).where(Chunk.document_id == document_id)
        await self.session.execute(statement)
        await self.session.commit()

# Usage in task
@celery_app.task
def chunk_document(document_id: int):
    with get_db() as session:
        # Get document
        document = session.get(Document, document_id)

        # Generate chunks
        chunks = await (
            ChunkBuilder()
            .from_document(document)
            .with_chunker(chunker)
            .build()
        )

        # Save chunks
        repo = ChunkRepository(session)
        await repo.create_chunks(chunks)

        # Chain to embedding
        from app.tasks.embedding import embed_chunks
        embed_chunks.delay(document_id)
```

**Why:** Abstracts database operations, testable, reusable.

### Learning Outcomes

**Technical Skills:**
- ✅ Token-based text splitting
- ✅ tiktoken library
- ✅ Chunking strategies
- ✅ Generator patterns in Python

**System Design Concepts:**
- ✅ Chunking trade-offs (size, overlap)
- ✅ Context window management
- ✅ Text preprocessing pipelines

**Interview Questions You Can Answer:**
- "How do you chunk documents for RAG?"
- "What's the optimal chunk size and why?"
- "Why use overlapping chunks?"
- "How do you handle very long documents?"

### Done When
- [ ] Documents split into chunks
- [ ] Chunks saved with position and token count
- [ ] Chunking task chains to embedding
- [ ] Edge cases handled

---

## Phase 2.4: Vector Embeddings & Search

### What You're Building
Generate vector embeddings for chunks and implement semantic search using Qdrant.

### System Design: Vector Search

**Problem:** Keyword search misses semantically similar content.

**Solution:** Vector embeddings + similarity search

**Architecture:**
```
Text → Embedding Model → Vector (384 dimensions) → Qdrant HNSW Index → K-Nearest Neighbors → Top Results
```

### Tasks
1. **Qdrant Setup**
   - [ ] Add Qdrant to Docker Compose
   - [ ] Create collection with proper configuration
   - [ ] Configure HNSW index parameters
   - [ ] Test connectivity

2. **Embedding Generation**
   - [ ] Install Sentence Transformers
   - [ ] Choose embedding model (all-MiniLM-L6-v2)
   - [ ] Implement batch embedding
   - [ ] Optimize embedding performance

3. **Embedding Task**
   - [ ] Celery task: embed_chunks
   - [ ] Generate embeddings in batches
   - [ ] Store vectors in Qdrant
   - [ ] Store embedding metadata

4. **Search Endpoint**
   - [ ] `POST /documents/search` - Semantic search
   - [ ] Generate query embedding
   - [ ] Search in Qdrant
   - [ ] Return ranked results with scores

5. **Testing**
   - [ ] Test embedding generation
   - [ ] Test search accuracy
   - [ ] Test search performance (<100ms)
   - [ ] Test batch processing

### Design Patterns
- **Adapter Pattern (Vector Store):** Easy to swap vector databases, testable, consistent interface
- **Strategy Pattern (Embedding Models):** Can switch between free and paid embeddings, testable with mocks
- **Batch Processing Pattern:** Efficient batching, progress tracking, error recovery

### Learning Outcomes

**Technical Skills:**
- ✅ Vector embeddings (Sentence Transformers)
- ✅ Qdrant vector database
- ✅ HNSW index algorithm understanding
- ✅ Batch processing optimization
- ✅ Cosine similarity

**System Design Concepts:**
- ✅ Vector databases vs traditional databases
- ✅ Approximate nearest neighbor search
- ✅ Index types (HNSW, IVF)
- ✅ Embedding dimensions trade-offs
- ✅ Search relevance tuning

**Interview Questions You Can Answer:**
- "How do vector databases work?"
- "Explain semantic search vs keyword search"
- "What's HNSW and why use it?"
- "How do you choose embedding dimensions?"
- "Design a semantic search system"

### Done When
- [ ] Qdrant collection created
- [ ] Embeddings generated for all chunks
- [ ] Search returns relevant results
- [ ] Search time < 100ms for 1M vectors
- [ ] Batch processing optimized

---

## Phase 2.5: RAG Implementation

### What You're Building
Retrieval-Augmented Generation: Combine search with LLM to answer questions about documents.

### System Design: RAG Architecture

**Problem:** LLMs don't have access to your private documents.

**Solution:** RAG Pipeline
```
Question → Search (retrieve relevant chunks) → Build prompt → LLM (generate answer)
```

**Architecture:**
```
User Query → Embed Query → Search Qdrant → Top 5 Chunks → Build Prompt → Claude API → Stream Response → User
```

### Tasks
1. **Claude Integration**
   - [ ] Install Anthropic SDK
   - [ ] Configure API key
   - [ ] Test basic completion
   - [ ] Test streaming

2. **Prompt Engineering**
   - [ ] Create RAG system prompt
   - [ ] Build context window
   - [ ] Add citation instructions
   - [ ] Test prompt variations

3. **Query Endpoint**
   - [ ] `POST /documents/{id}/ask` - Ask about specific document
   - [ ] `POST /query` - Ask across all documents
   - [ ] Return answer with citations
   - [ ] Save query history

4. **Streaming Endpoint**
   - [ ] `GET /documents/{id}/ask/stream` - Streaming response
   - [ ] Server-Sent Events (SSE)
   - [ ] Stream tokens in real-time

5. **Query History**
   - [ ] Create Query model (user_id, query, answer, chunks_used, created_at)
   - [ ] `GET /queries` - List user's queries
   - [ ] `GET /queries/{id}` - Get specific query

6. **Testing**
   - [ ] Test answer quality
   - [ ] Test citations
   - [ ] Test streaming
   - [ ] Test edge cases (no results, ambiguous question)

### Design Patterns
- **Template Method Pattern (RAG Pipeline):** Flexible pipeline, easy to swap LLMs, testable steps
- **Strategy Pattern (Prompt Strategies):** Different question types need different prompts, easy to add new types
- **Streaming Pattern:** Better UX (immediate feedback), lower perceived latency

### Learning Outcomes

**Technical Skills:**
- ✅ RAG pipeline implementation
- ✅ Claude API integration
- ✅ Prompt engineering
- ✅ Server-Sent Events (SSE)
- ✅ Streaming responses

**System Design Concepts:**
- ✅ RAG architecture
- ✅ Context window management
- ✅ Prompt templates
- ✅ LLM cost optimization
- ✅ Hallucination reduction

**Interview Questions You Can Answer:**
- "Explain RAG architecture"
- "How do you reduce LLM hallucinations?"
- "Design a document Q&A system"
- "What's the difference between RAG and fine-tuning?"
- "How do you handle LLM streaming?"

### Done When
- [ ] Can ask questions about documents
- [ ] Answers include citations
- [ ] Streaming works smoothly
- [ ] Query history saved
- [ ] Answer quality is good (manual testing)

---

## Phase 2.6: Hybrid Search

### What You're Building
Combine vector search and keyword search for better retrieval accuracy.

### System Design: Hybrid Search

**Problem:** Vector search misses exact matches, keyword search misses semantics.

**Solution:** Hybrid search = Vector + Keyword + Re-ranking
```
Query → [Vector Search + Keyword Search] → Merge + Re-rank (RRF) → Best of both
```

### Tasks
1. **Postgres Full-Text Search**
   - [ ] Add tsvector column to chunks table
   - [ ] Create GIN index for full-text search
   - [ ] Create trigger to update tsvector
   - [ ] Test FTS queries

2. **Keyword Search Implementation**
   - [ ] Implement keyword search function
   - [ ] Support phrase search
   - [ ] Support boolean operators (AND, OR, NOT)
   - [ ] Rank results by relevance

3. **Reciprocal Rank Fusion (RRF)**
   - [ ] Implement RRF algorithm
   - [ ] Tune k parameter (typically 60)
   - [ ] Combine scores from both searches

4. **Hybrid Search Service**
   - [ ] Combine vector and keyword search
   - [ ] Apply RRF to merge results
   - [ ] Return deduplicated, ranked results

5. **Update Search Endpoint**
   - [ ] Add hybrid_search parameter
   - [ ] Default to hybrid for best results
   - [ ] Support vector-only and keyword-only modes

6. **Testing**
   - [ ] Test exact match queries
   - [ ] Test semantic queries
   - [ ] Test mixed queries
   - [ ] Compare accuracy vs vector-only

### Design Patterns
- **Composite Pattern (Search Strategies):** Flexible composition, easy to test each strategy, clear separation
- **Facade Pattern (Unified Search Interface):** Simple interface hides complexity, easy to use, backward compatible

### Learning Outcomes

**Technical Skills:**
- ✅ Postgres full-text search
- ✅ GIN indexes
- ✅ Reciprocal Rank Fusion (RRF)
- ✅ Hybrid search implementation
- ✅ Search quality evaluation

**System Design Concepts:**
- ✅ Hybrid search architecture
- ✅ Re-ranking algorithms
- ✅ Search quality metrics
- ✅ Index optimization
- ✅ Query performance tuning

**Interview Questions You Can Answer:**
- "Design a hybrid search system"
- "Explain Reciprocal Rank Fusion"
- "Vector vs keyword search - when to use each?"
- "How do you combine multiple ranking signals?"
- "Design a search system for technical documents"

### Done When
- [ ] Full-text search works
- [ ] Hybrid search combines both
- [ ] RRF merging implemented
- [ ] Better accuracy than vector-only
- [ ] Performance acceptable (<200ms)

---

## Phase 2.7: Production Optimization

### What You're Building
Optimize RAG system for production: caching, cost reduction, performance tuning.

### System Design: Caching & Optimization

**Problem:** RAG is expensive (LLM costs) and slow (multiple API calls).

**Solution:** Multi-layer caching
```
Query → Cache L1 (Redis - hot) → Cache L2 (Postgres - warm) → LLM (cold)
```

### Tasks
1. **Response Caching**
   - [ ] Implement Redis caching for RAG responses
   - [ ] Cache key: hash(query + document_id)
   - [ ] TTL: 1 hour
   - [ ] Cache invalidation on document update

2. **Embedding Caching**
   - [ ] Cache query embeddings (queries repeat)
   - [ ] TTL: 24 hours
   - [ ] Reduce embedding API calls

3. **Score Thresholds**
   - [ ] Filter low-relevance chunks (score < 0.7)
   - [ ] Reduce context size
   - [ ] Improve answer quality

4. **Query Classification**
   - [ ] Detect simple vs complex queries
   - [ ] Use cheaper models for simple queries
   - [ ] Route queries intelligently

5. **Connection Pooling**
   - [ ] Optimize Postgres connection pool
   - [ ] Optimize Redis connection pool
   - [ ] Tune pool sizes

6. **Performance Monitoring**
   - [ ] Track search latency
   - [ ] Track LLM latency
   - [ ] Track cache hit rates
   - [ ] Set up alerts

### Design Patterns
- **Cache-Aside Pattern:** Centralized caching logic, easy to test, consistent behavior
- **Decorator Pattern (Caching Decorator):** Declarative caching, reusable, easy to add to any function
- **Query Classification:** Reduces costs by 40-60%, maintains quality for complex queries

### Learning Outcomes

**Technical Skills:**
- ✅ Multi-layer caching strategies
- ✅ Cache invalidation patterns
- ✅ Query optimization
- ✅ Cost optimization techniques
- ✅ Connection pool tuning

**System Design Concepts:**
- ✅ Caching trade-offs (TTL, consistency)
- ✅ Cost vs quality trade-offs
- ✅ Performance optimization strategies
- ✅ Connection pooling
- ✅ Cache invalidation strategies

**Interview Questions You Can Answer:**
- "How do you optimize RAG system costs?"
- "Explain cache invalidation strategies"
- "How do you balance cost and quality?"
- "Design a caching layer for AI applications"
- "How do you prevent cache stampede?"

### Done When
- [ ] Response caching works (Redis)
- [ ] Cache hit rate > 30%
- [ ] LLM costs reduced by 40%+
- [ ] Response time improved by 50%+
- [ ] Cache invalidation works correctly

---

# Project 3: Agentic AI Platform

## Overview

**What You're Building:** Autonomous AI agents that monitor documents, detect trends, and take actions using tools and event-driven architecture.

**Architecture Pattern:** Event-Driven Microservices

**System Design Topics:**
- Event streaming (Kafka/Redpanda)
- Agentic AI (LangGraph)
- Real-time chat (WebSockets)
- Consistent hashing for distribution
- Observability (Prometheus + Grafana)


## Phase 3.1: LangGraph Agent Framework

### What You're Building
AI agents that can autonomously use tools to accomplish tasks.

### System Design: Agentic AI

**Problem:** Traditional RAG is reactive - only answers when asked.

**Solution:** Autonomous agents with tools
```
Agent decides: "I need to search" → Uses search tool → Analyzes result → Decides next action
```

**Architecture:**
```
User Request → Agent (LangGraph State Machine) → [Think → Act → Observe → Repeat or Answer]
```

### Tasks
1. **LangGraph Setup**
   - [ ] Install LangGraph
   - [ ] Understand state machines
   - [ ] Create basic agent graph
   - [ ] Test simple workflows

2. **Agent Tools**
   - [ ] `search_documents` - Search user's documents
   - [ ] `query_database` - Execute read-only SQL
   - [ ] `generate_report` - Create summary reports
   - [ ] `send_notification` - Send notifications
   - [ ] `web_search` - Search the web (optional)

3. **Agent State Machine**
   - [ ] Define agent state (messages, iterations, final_answer)
   - [ ] Create agent reasoning node
   - [ ] Create tool execution node
   - [ ] Define state transitions
   - [ ] Add max iterations limit

4. **Agent Endpoint**
   - [ ] `POST /agent/query` - Chat with agent
   - [ ] Save conversation history
   - [ ] Return agent reasoning steps
   - [ ] Handle errors gracefully

5. **Streaming Agent**
   - [ ] `GET /agent/query/stream` - Stream agent thinking
   - [ ] Show reasoning steps in real-time
   - [ ] Show tool calls
   - [ ] Better UX

6. **Testing**
   - [ ] Test single tool usage
   - [ ] Test multi-step reasoning
   - [ ] Test max iterations
   - [ ] Test error handling

### Design Patterns
- **State Machine Pattern (LangGraph):** Full control over agent behavior, debuggable, handles loops naturally
- **Command Pattern (Agent Tools):** Tools are independent, easy to add new ones, testable, clear interfaces

### Learning Outcomes

**Technical Skills:**
- ✅ LangGraph framework
- ✅ Agent state machines
- ✅ Tool calling with Claude
- ✅ Multi-step reasoning
- ✅ Agent streaming

**System Design Concepts:**
- ✅ Agentic AI architecture
- ✅ ReAct pattern (Reasoning + Acting)
- ✅ Tool abstraction
- ✅ Agent error handling
- ✅ Conversation management

**Interview Questions You Can Answer:**
- "Design an AI agent system"
- "Explain ReAct prompting"
- "How do you give LLMs tools?"
- "What's the difference between RAG and agents?"
- "How do you handle agent failures?"

### Done When
- [ ] Agent can use tools
- [ ] Multi-step reasoning works
- [ ] Streaming shows reasoning
- [ ] Conversation history saved
- [ ] Error handling robust

---

## Phase 3.2: Event Streaming (Redpanda)

### What You're Building
Event-driven architecture with Redpanda for real-time event processing.

### System Design: Event Streaming

**Problem:** Services are tightly coupled, hard to scale independently.

**Solution:** Event streaming with pub/sub
```
Service A → Publish Event → Redpanda → [Subscribe → Service B, Subscribe → Service C]
```

**Architecture:**
```
FastAPI (Producer) → Events → Redpanda (Event Stream) → Consumers (Triggers, Analytics, Notifications)
```

### Tasks
1. **Redpanda Setup**
   - [ ] Add Redpanda to Docker Compose
   - [ ] Create topics (events, triggers, analytics)
   - [ ] Configure retention and partitions
   - [ ] Test connectivity

2. **Event Schemas**
   - [ ] Define event types (Pydantic models)
   - [ ] document.uploaded
   - [ ] document.processed
   - [ ] query.completed
   - [ ] trend.detected
   - [ ] anomaly.detected

3. **Event Producer**
   - [ ] Create producer service
   - [ ] Publish events on actions
   - [ ] Add event metadata (timestamp, user_id)
   - [ ] Handle producer errors

4. **Event Consumer**
   - [ ] Create consumer service
   - [ ] Subscribe to topics
   - [ ] Process events
   - [ ] Handle consumer errors

5. **Integration**
   - [ ] Publish events from API endpoints
   - [ ] Publish events from Celery tasks
   - [ ] Consume events in separate service

6. **Testing**
   - [ ] Test event publishing
   - [ ] Test event consumption
   - [ ] Test event ordering
   - [ ] Test error handling

### Design Patterns
- **Event Sourcing Pattern:** Structured events, type safety, versioning support
- **Publisher Pattern:** Centralized publishing, consistent format, error handling
- **Subscriber Pattern:** Flexible routing, multiple handlers, fault tolerance

### Learning Outcomes

**Technical Skills:**
- ✅ Kafka/Redpanda basics
- ✅ Event-driven architecture
- ✅ Pub/sub patterns
- ✅ Message serialization
- ✅ Consumer groups

**System Design Concepts:**
- ✅ Event sourcing
- ✅ Event-driven architecture
- ✅ Message ordering guarantees
- ✅ Exactly-once vs at-least-once
- ✅ Partitioning strategies

**Interview Questions You Can Answer:**
- "Design an event-driven system"
- "Kafka vs RabbitMQ - when to use each?"
- "How do you ensure message ordering?"
- "Explain consumer groups"
- "How do you handle duplicate events?"

### Done When
- [ ] Redpanda running
- [ ] Events published from API
- [ ] Events consumed successfully
- [ ] Event ordering maintained
- [ ] Error handling robust

---

## Phase 3.3 Continuation: Intelligent Triggers

### Detection Strategy (continued)
```python
        self.counts = defaultdict(int)

    async def analyze(self, event: Event) -> bool:
        key = event.type
        self.counts[key] += 1

        # Check if threshold exceeded
        return self.counts[key] >= self.threshold

    async def take_action(self, event: Event):
        # Send alert
        pass

class AnomalyDetectionStrategy(DetectionStrategy):
    """Detect anomalies using statistical methods"""

    def __init__(self):
        self.baseline = {}  # metric -> average
        self.std_devs = {}  # metric -> standard deviation

    async def analyze(self, event: Event) -> bool:
        # Check if metric deviates significantly from baseline
        metric = event.data.get("metric")
        value = event.data.get("value")

        if metric in self.baseline:
            baseline = self.baseline[metric]
            std_dev = self.std_devs[metric]

            # Alert if > 3 standard deviations
            if abs(value - baseline) > 3 * std_dev:
                return True

        return False
```

### Consumer Service
```python
# app/events/consumer_service.py
class IntelligentTriggerService:
    """Service that runs intelligent triggers on events"""

    def __init__(self):
        self.consumer = EventConsumer(
            topics=["events"],
            group_id="intelligent-triggers",
            bootstrap_servers="redpanda:9092"
        )

        # Initialize detectors
        self.trend_detector = TrendDetector()
        self.anomaly_detector = AnomalyDetector()

        # Register handlers
        self.consumer.register_handler(
            EventType.DOCUMENT_UPLOADED,
            self.trend_detector.handle_document_uploaded
        )
        self.consumer.register_handler(
            EventType.QUERY_COMPLETED,
            self.anomaly_detector.handle_query_completed
        )

    async def run(self):
        """Run the service"""
        await self.consumer.start()
        logger.info("Intelligent trigger service started")

        try:
            await self.consumer.consume()
        finally:
            await self.consumer.stop()

# Run as separate service
if __name__ == "__main__":
    service = IntelligentTriggerService()
    asyncio.run(service.run())
```

### Learning Outcomes

**Technical Skills:**
- ✅ Pattern detection algorithms
- ✅ Time-series analysis
- ✅ Anomaly detection
- ✅ Event-driven triggers

**System Design Concepts:**
- ✅ Intelligent monitoring
- ✅ Threshold-based alerts
- ✅ Proactive vs reactive systems

**Interview Questions You Can Answer:**
- "Design an intelligent monitoring system"
- "How do you detect anomalies in time-series data?"
- "Design a trend detection system"

### Done When
- [ ] Trend detection works
- [ ] Anomaly detection works
- [ ] Notifications sent automatically
- [ ] Runs as separate service

---

## Phase 3.4: Real-Time Chat

### What You're Building
WebSocket-based real-time chat with AI agent.

### System Design: WebSocket Communication

**Problem:** HTTP is request/response, need bidirectional real-time.

**Solution:** WebSockets for persistent connections
```
Client ←→ WebSocket ←→ Server (continuous connection)
```

**Architecture:**
```
Client (Browser)
    ↓ WebSocket
FastAPI WebSocket Endpoint
    ↓
Connection Manager (tracks active connections)
    ↓
Agent (processes messages in real-time)
```

### Tasks
1. **WebSocket Manager**
   - [ ] Connection management (connect/disconnect)
   - [ ] Broadcast to user's connections
   - [ ] Handle connection errors
   - [ ] Track active users

2. **WebSocket Endpoint**
   - [ ] `/ws/chat/{conversation_id}` - WebSocket endpoint
   - [ ] Authenticate via token
   - [ ] Receive messages
   - [ ] Stream agent responses
   - [ ] Handle disconnections

3. **Message Persistence**
   - [ ] Save messages to database
   - [ ] Load conversation history
   - [ ] Pagination support

4. **Real-Time Features**
   - [ ] Typing indicators
   - [ ] Read receipts
   - [ ] Agent thinking indicator
   - [ ] Multi-device sync

5. **Testing**
   - [ ] Test WebSocket connection
   - [ ] Test message sending
   - [ ] Test agent responses
   - [ ] Test disconnection handling

### Design Patterns

**1. Observer Pattern (Connection Manager)**
```python
# app/websocket/manager.py
from fastapi import WebSocket
from typing import Dict, List
import asyncio

class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # user_id -> list of WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and register connection"""
        await websocket.accept()

        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)

        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove connection"""
        async with self.lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)

                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to all connections of a user"""
        connections = self.active_connections.get(user_id, [])

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                # Connection is probably closed, will be cleaned up

    async def broadcast(self, message: dict):
        """Broadcast to all connected users"""
        for user_id, connections in self.active_connections.items():
            await self.send_personal_message(message, user_id)

    def get_active_users(self) -> List[int]:
        """Get list of active user IDs"""
        return list(self.active_connections.keys())

    def get_connection_count(self, user_id: int) -> int:
        """Get number of connections for user"""
        return len(self.active_connections.get(user_id, []))

manager = ConnectionManager()
```

**Why:** Centralized connection management, multi-device support, broadcast capability.

**2. WebSocket Endpoint**
```python
# app/routes/websocket.py
from fastapi import WebSocket, WebSocketDisconnect, Depends
from jose import jwt

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str
):
    """
    WebSocket endpoint for real-time chat with agent.

    Query params:
        token: JWT authentication token

    Messages:
        Send: {"type": "message", "content": "..."}
        Receive: {"type": "message|thinking|tool|done", "content": "..."}
    """
    # Authenticate
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Verify conversation access
    with get_db() as session:
        conversation = session.get(Conversation, conversation_id)
        if not conversation or conversation.user_id != user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return

    # Connect
    await manager.connect(websocket, user_id)

    # Send conversation history
    with get_db() as session:
        conversation = session.get(Conversation, conversation_id)
        await websocket.send_json({
            "type": "history",
            "messages": conversation.messages or []
        })

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            if data["type"] == "message":
                message = data["content"]

                # Save user message
                with get_db() as session:
                    conversation = session.get(Conversation, conversation_id)
                    conversation.messages = conversation.messages or []
                    conversation.messages.append({
                        "role": "user",
                        "content": message,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    session.commit()

                # Echo message (confirmation)
                await manager.send_personal_message({
                    "type": "message",
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)

                # Send typing indicator
                await manager.send_personal_message({
                    "type": "thinking",
                    "message": "Agent is thinking..."
                }, user_id)

                # Stream agent response
                async for event in agent.graph.astream({
                    "messages": [{"role": "user", "content": message}],
                    "iterations": 0,
                    "user_id": user_id
                }):
                    if "agent" in event:
                        # Agent thinking
                        await manager.send_personal_message({
                            "type": "thinking",
                            "data": event["agent"]
                        }, user_id)

                    elif "tools" in event:
                        # Tool execution
                        await manager.send_personal_message({
                            "type": "tool",
                            "data": event["tools"]
                        }, user_id)

                # Get final answer
                result = event  # Last event has final state
                answer = result.get("final_answer", "No answer generated")

                # Save agent message
                with get_db() as session:
                    conversation = session.get(Conversation, conversation_id)
                    conversation.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    session.commit()

                # Send final answer
                await manager.send_personal_message({
                    "type": "message",
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)

                # Send done signal
                await manager.send_personal_message({
                    "type": "done"
                }, user_id)

            elif data["type"] == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} disconnected from conversation {conversation_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, user_id)
        await websocket.close(code=1011, reason="Internal error")
```

**Why:** Real-time bidirectional communication, streaming agent responses, multi-device support.

**3. Client Example (JavaScript)**
```javascript
// Example client-side code
class ChatClient {
    constructor(conversationId, token) {
        this.conversationId = conversationId;
        this.token = token;
        this.ws = null;
    }

    connect() {
        const wsUrl = `ws://localhost:8000/ws/chat/${this.conversationId}?token=${this.token}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('Connected to chat');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('Disconnected from chat');
            // Attempt reconnect after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(data) {
        switch(data.type) {
            case 'history':
                // Load conversation history
                this.displayHistory(data.messages);
                break;

            case 'message':
                // Display message
                this.displayMessage(data.role, data.content);
                break;

            case 'thinking':
                // Show thinking indicator
                this.showThinking();
                break;

            case 'tool':
                // Show tool usage
                this.showTool(data.data);
                break;

            case 'done':
                // Hide thinking indicator
                this.hideThinking();
                break;
        }
    }

    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'message',
                content: message
            }));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Usage
const chat = new ChatClient('conv-123', 'jwt-token');
chat.connect();
chat.sendMessage('Hello agent!');
```

### Learning Outcomes

**Technical Skills:**
- ✅ WebSocket implementation
- ✅ Connection management
- ✅ Real-time messaging
- ✅ Bidirectional communication

**System Design Concepts:**
- ✅ WebSocket vs HTTP polling
- ✅ Connection pooling
- ✅ Heartbeat/ping-pong
- ✅ Reconnection strategies

**Interview Questions You Can Answer:**
- "Design a real-time chat system"
- "WebSocket vs Server-Sent Events - when to use each?"
- "How do you handle WebSocket scaling?"
- "Design a notification system with WebSockets"

### Done When
- [ ] WebSocket connections work
- [ ] Messages sent/received in real-time
- [ ] Agent responses stream
- [ ] Multi-device support works
- [ ] Reconnection handles gracefully

---

## Phase 3.5: Consistent Hashing

### What You're Building
Distribute load across multiple servers using consistent hashing.

### System Design: Consistent Hashing

**Problem:** Load balancing with minimal disruption when adding/removing servers.

**Solution:** Consistent hashing with virtual nodes
```
hash(user_id) → position on ring → nearest server
```

**Architecture:**
```
User Request
    ↓
Load Balancer (consistent hash)
    ↓
Server 1, Server 2, or Server 3
(based on user_id hash)
```

**Why Consistent Hashing:**
- ✅ Only K/n keys move when adding node (K=total keys, n=nodes)
- ✅ No central coordination needed
- ✅ Even load distribution
- ✅ Supports heterogeneous nodes

### Tasks
1. **Hash Ring Implementation**
   - [ ] Implement consistent hash ring
   - [ ] Add/remove nodes
   - [ ] Virtual nodes (replicas)
   - [ ] Find node for key

2. **Shard Documents**
   - [ ] Assign documents to shards based on hash
   - [ ] Update database schema (add shard_id)
   - [ ] Migrate existing documents
   - [ ] Query routing based on shard

3. **Load Balancer**
   - [ ] Route requests based on user_id hash
   - [ ] Sticky sessions (same user → same server)
   - [ ] Health checks
   - [ ] Failover handling

4. **Testing**
   - [ ] Test even distribution
   - [ ] Test adding nodes (minimal movement)
   - [ ] Test removing nodes
   - [ ] Test load balancing

### Design Patterns

**1. Consistent Hash Ring (from Phase 1.4 reference)**
```python
# app/services/consistent_hash.py
import hashlib
import bisect
from typing import List, Optional

class ConsistentHashRing:
    """
    Consistent hashing for distributing load across nodes.

    Uses virtual nodes to improve distribution.
    """

    def __init__(self, nodes: List[str] = None, virtual_nodes: int = 150):
        """
        Args:
            nodes: List of server nodes
            virtual_nodes: Number of virtual nodes per physical node
        """
        self.virtual_nodes = virtual_nodes
        self.ring = {}  # hash -> node
        self.sorted_keys = []  # sorted hash values

        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key: str) -> int:
        """Hash function using MD5"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        """
        Add a node with virtual replicas.

        Virtual nodes improve distribution and handle
        heterogeneous node capacities.
        """
        for i in range(self.virtual_nodes):
            virtual_key = f"{node}:{i}"
            hash_value = self._hash(virtual_key)

            self.ring[hash_value] = node
            bisect.insort(self.sorted_keys, hash_value)

        logger.info(f"Added node {node} with {self.virtual_nodes} virtual nodes")

    def remove_node(self, node: str):
        """Remove a node and its virtual replicas"""
        removed_count = 0

        for i in range(self.virtual_nodes):
            virtual_key = f"{node}:{i}"
            hash_value = self._hash(virtual_key)

            if hash_value in self.ring:
                del self.ring[hash_value]
                self.sorted_keys.remove(hash_value)
                removed_count += 1

        logger.info(f"Removed node {node} ({removed_count} virtual nodes)")

    def get_node(self, key: str) -> Optional[str]:
        """
        Get the node responsible for a key.

        Finds the first node clockwise from the key's position.
        """
        if not self.ring:
            return None

        hash_value = self._hash(key)

        # Find first node clockwise
        idx = bisect.bisect(self.sorted_keys, hash_value)

        if idx == len(self.sorted_keys):
            # Wrap around to first node
            idx = 0

        return self.ring[self.sorted_keys[idx]]

    def get_nodes(self, key: str, count: int = 3) -> List[str]:
        """
        Get multiple nodes for replication.

        Returns up to 'count' distinct nodes starting from key position.
        """
        if not self.ring or count < 1:
            return []

        hash_value = self._hash(key)
        idx = bisect.bisect(self.sorted_keys, hash_value)

        nodes = []
        seen = set()

        while len(nodes) < count and len(seen) < len(self.ring):
            if idx >= len(self.sorted_keys):
                idx = 0

            node = self.ring[self.sorted_keys[idx]]
            if node not in seen:
                nodes.append(node)
                seen.add(node)

            idx += 1

        return nodes

    def get_distribution(self, keys: List[str]) -> dict:
        """
        Analyze distribution of keys across nodes.

        Useful for testing and monitoring.
        """
        distribution = {}

        for key in keys:
            node = self.get_node(key)
            distribution[node] = distribution.get(node, 0) + 1

        return distribution

# Initialize hash ring
hash_ring = ConsistentHashRing(
    nodes=["server1", "server2", "server3"],
    virtual_nodes=150
)
```

**Why:** Minimal key movement when scaling, load balancing, fault tolerance.

**2. Middleware for Request Routing**
```python
# app/middleware/routing.py
@app.middleware("http")
async def consistent_hash_routing(request: Request, call_next):
    """
    Route requests based on consistent hashing.

    This is a simulation - in production, you'd have
    a proper load balancer (nginx, HAProxy) doing this.
    """
    # Get user ID from token
    token = request.headers.get("authorization")
    if token:
        user_id = get_user_id_from_token(token)

        # Determine target server
        target_server = hash_ring.get_node(str(user_id))

        # Add header for monitoring
        request.state.target_server = target_server

        logger.info(f"Routing user {user_id} to {target_server}")

    response = await call_next(request)

    # Add server info to response headers
    if hasattr(request.state, 'target_server'):
        response.headers["X-Server"] = request.state.target_server

    return response
```

**3. Document Sharding**
```python
# app/services/sharding.py
class ShardingService:
    """Shard documents across multiple databases/servers"""

    def __init__(self, hash_ring: ConsistentHashRing):
        self.hash_ring = hash_ring

    def get_shard_for_document(self, document_id: int) -> str:
        """Determine which shard a document belongs to"""
        return self.hash_ring.get_node(str(document_id))

    def get_shard_for_user(self, user_id: int) -> str:
        """Determine which shard a user's documents belong to"""
        return self.hash_ring.get_node(str(user_id))

    async def create_document(self, document: Document):
        """Create document on appropriate shard"""
        shard = self.get_shard_for_user(document.owner_id)

        # Add shard info to document
        document.shard_id = shard

        # Save to database
        # In production, you'd route to the actual shard database
        with get_db() as session:
            session.add(document)
            session.commit()

        logger.info(f"Document {document.id} created on shard {shard}")

    async def get_document(self, document_id: int):
        """Retrieve document from appropriate shard"""
        shard = self.get_shard_for_document(document_id)

        # Query from shard
        with get_db() as session:
            document = session.get(Document, document_id)

            if document and document.shard_id != shard:
                # Document migrated or inconsistency
                logger.warning(f"Document {document_id} shard mismatch")

            return document

sharding_service = ShardingService(hash_ring)
```

**Why:** Horizontal scalability, distributed data, no single point of failure.

### Learning Outcomes

**Technical Skills:**
- ✅ Consistent hashing algorithm
- ✅ Virtual nodes implementation
- ✅ Sharding strategies
- ✅ Load distribution

**System Design Concepts:**
- ✅ Consistent hashing vs simple hashing
- ✅ Virtual nodes for better distribution
- ✅ Data partitioning strategies
- ✅ Replication for fault tolerance

**Interview Questions You Can Answer:**
- "Explain consistent hashing"
- "Design a distributed cache with consistent hashing"
- "How do you shard a database?"
- "What happens when you add a node to consistent hash ring?"
- "Why use virtual nodes?"

### Done When
- [ ] Hash ring implemented
- [ ] Even load distribution (tested with 10k keys)
- [ ] Adding node moves < 30% of keys
- [ ] Documents sharded correctly
- [ ] Request routing works

---

## Phase 3.6: Horizontal Scaling

### What You're Building
Scale API horizontally across multiple instances with shared state.

### System Design: Horizontal Scaling

**Problem:** Single server can't handle all traffic.

**Solution:** Multiple API instances with load balancer
```
                Load Balancer
                      │
        ┌─────────────┼─────────────┐
        │             │             │
    API Instance  API Instance  API Instance
        │             │             │
        └─────────────┼─────────────┘
                      │
            Shared Resources
      (Postgres, Redis, Qdrant, Redpanda)
```

**Key Requirements:**
- ✅ Stateless APIs (no local state)
- ✅ Shared cache (Redis)
- ✅ Shared database
- ✅ Session management
- ✅ WebSocket handling (sticky sessions)

### Tasks
1. **Stateless API**
   - [ ] Remove any local state
   - [ ] Use Redis for session storage
   - [ ] Use Redis for rate limiting
   - [ ] Ensure all APIs are idempotent

2. **Load Balancer**
   - [ ] Configure nginx as load balancer
   - [ ] Least connections algorithm
   - [ ] Health checks
   - [ ] Sticky sessions for WebSockets

3. **Docker Compose Scaling**
   - [ ] Update docker-compose.yml
   - [ ] Deploy multiple API replicas
   - [ ] Configure shared volumes
   - [ ] Test scaling

4. **Session Management**
   - [ ] Move sessions to Redis
   - [ ] JWT tokens (already stateless)
   - [ ] Shared rate limiting state

5. **Testing**
   - [ ] Load test with 1000 concurrent users
   - [ ] Test failover (kill one instance)
   - [ ] Test session persistence
   - [ ] Test WebSocket sticky sessions

### Design Patterns

**1. Stateless Architecture**
```python
# BAD: Local state (doesn't work with multiple instances)
request_counts = {}  # In-memory - different per instance

@app.get("/api")
def bad_endpoint(user_id: int):
    request_counts[user_id] = request_counts.get(user_id, 0) + 1
    return {"requests": request_counts[user_id]}

# GOOD: Shared state in Redis
@app.get("/api")
async def good_endpoint(user_id: int):
    key = f"request_count:{user_id}"
    count = await redis_client.incr(key)
    return {"requests": count}
```

**Why:** Consistent state across instances, no coordination needed.

**2. Nginx Load Balancer Configuration**
```nginx
# nginx.conf
upstream api_servers {
    least_conn;  # Route to server with fewest connections

    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}

# WebSocket upstream (sticky sessions)
upstream websocket_servers {
    ip_hash;  # Sticky sessions based on client IP

    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;

    # Regular HTTP endpoints
    location / {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Health check
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }

    # WebSocket endpoints
    location /ws/ {
        proxy_pass http://websocket_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;  # 24 hours
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://api_servers;
    }
}
```

**Why:** Load balancing, health checks, sticky sessions for WebSockets.

**3. Docker Compose for Scaling**
```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api
    networks:
      - app-network

  api:
    build: .
    deploy:
      replicas: 3  # Run 3 instances
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/docanalyst
      - REDIS_URL=redis://redis:6379
      - QDRANT_HOST=qdrant
      - REDPANDA_BOOTSTRAP_SERVERS=redpanda:9092
    depends_on:
      - db
      - redis
      - qdrant
      - redpanda
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: docanalyst
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - app-network

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - app-network

  redpanda:
    image: vectorized/redpanda:latest
    command:
      - redpanda start
      - --smp 1
      - --memory 1G
      - --overprovisioned
      - --kafka-addr PLAINTEXT://0.0.0.0:9092
    ports:
      - "9092:9092"
    volumes:
      - redpanda_data:/var/lib/redpanda/data
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  redpanda_data:

networks:
  app-network:
    driver: bridge
```

**Why:** Easy scaling, shared resources, production-ready setup.

**4. Graceful Shutdown**
```python
# app/main.py
import signal

shutdown_event = asyncio.Event()

def handle_shutdown(signum, frame):
    """Handle graceful shutdown"""
    logger.info("Received shutdown signal, starting graceful shutdown...")
    shutdown_event.set()

# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

@app.on_event("startup")
async def startup():
    """Startup tasks"""
    await event_producer.start()
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown():
    """Shutdown tasks"""
    logger.info("Shutting down gracefully...")

    # Close connections
    await event_producer.stop()
    await redis_client.close()

    # Wait for in-flight requests to complete
    await asyncio.sleep(5)

    logger.info("Shutdown complete")
```

**Why:** No dropped requests, clean resource cleanup.

### Learning Outcomes

**Technical Skills:**
- ✅ Horizontal scaling implementation
- ✅ Load balancing (nginx)
- ✅ Stateless architecture
- ✅ Docker Compose scaling
- ✅ Health checks

**System Design Concepts:**
- ✅ Horizontal vs vertical scaling
- ✅ Load balancing algorithms
- ✅ Sticky sessions
- ✅ Graceful shutdown
- ✅ High availability

**Interview Questions You Can Answer:**
- "How do you scale an API horizontally?"
- "Explain sticky sessions and when you need them"
- "Design a stateless API"
- "What's graceful shutdown and why is it important?"
- "Load balancing algorithms - which and when?"

### Done When
- [ ] 3 API instances running
- [ ] Load balanced across instances
- [ ] Can handle 1000 concurrent requests
- [ ] Failover works (kill one instance)
- [ ] No dropped WebSocket connections
- [ ] Graceful shutdown works

---

## Phase 3.7: Observability (Prometheus + Grafana)

### What You're Building
Full observability: metrics collection, visualization, and alerting.

### System Design: Observability

**Problem:** Can't improve what you can't measure.

**Solution:** Metrics + Visualization + Alerts
```
Application → Prometheus (collect metrics) → Grafana (visualize)
                    ↓
              Alert Manager (alerts)
```

**Key Metrics:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- System resources (CPU, memory)
- Business metrics (documents uploaded, queries completed)

### Tasks
1. **Prometheus Setup**
   - [ ] Add Prometheus to Docker Compose
   - [ ] Configure scrape targets
   - [ ] Set up retention policies
   - [ ] Test metric collection

2. **Application Instrumentation**
   - [ ] Add prometheus_client
   - [ ] Expose /metrics endpoint
   - [ ] Track request metrics
   - [ ] Track custom business metrics

3. **Grafana Setup**
   - [ ] Add Grafana to Docker Compose
   - [ ] Connect to Prometheus
   - [ ] Create dashboards
   - [ ] Set up alerts

4. **Dashboards**
   - [ ] API Performance dashboard
   - [ ] RAG Performance dashboard
   - [ ] Agent Performance dashboard
   - [ ] System Resources dashboard
   - [ ] Business Metrics dashboard

5. **Alerting**
   - [ ] High error rate alert (>5%)
   - [ ] Slow response time alert (p95 >1s)
   - [ ] High CPU/memory alert
   - [ ] No document uploads in 24h alert

6. **Testing**
   - [ ] Generate load and view metrics
   - [ ] Verify dashboards update
   - [ ] Test alert triggers
   - [ ] Test alert notifications

### Design Patterns

**1. Metrics Collection**
```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator

# Request metrics (automatically tracked)
instrumentator = Instrumentator()
instrumentator.instrument(app)
instrumentator.expose(app, endpoint="/metrics")

# Custom counters
documents_uploaded = Counter(
    'documents_uploaded_total',
    'Total number of documents uploaded',
    ['user_tier']
)

queries_completed = Counter(
    'queries_completed_total',
    'Total number of queries completed',
    ['complexity', 'status']
)

# Histograms (for timing)
rag_latency = Histogram(
    'rag_latency_seconds',
    'Time to complete RAG query',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

search_latency = Histogram(
    'search_latency_seconds',
    'Time to complete vector search',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

# Gauges (current state)
active_websocket_connections = Gauge(
    'active_websocket_connections',
    'Number of active WebSocket connections'
)

documents_being_processed = Gauge(
    'documents_being_processed',
    'Number of documents currently being processed'
)

# Info (static information)
app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '1.0.0',
    'environment': 'production'
})
```

**Why:** Standard metrics format, Prometheus integration, queryable.

**2. Instrumentation in Routes**
```python
# app/routes/documents.py
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    # Track upload
    documents_uploaded.labels(user_tier=current_user.tier).inc()

    # ... upload logic ...

    return document

# app/services/rag_service.py
async def answer(self, query: str, user_id: int):
    # Track query
    start_time = time.time()
    complexity = classifier.classify(query)

    try:
        # ... RAG logic ...

        # Track success
        queries_completed.labels(
            complexity=complexity,
            status="success"
        ).inc()

        # Track latency
        latency = time.time() - start_time
        rag_latency.observe(latency)

        return result

    except Exception as e:
        # Track error
        queries_completed.labels(
            complexity=complexity,
            status="error"
        ).inc()
        raise
```

**Why:** Tracks both technical and business metrics, debugging insights.

**3. Prometheus Configuration**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # API instances
  - job_name: 'api'
    static_configs:
      - targets:
        - 'api1:8000'
        - 'api2:8000'
        - 'api3:8000'
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Celery workers
  - job_name: 'celery'
    static_configs:
      - targets: ['celery-exporter:9808']

  # Postgres
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

# Alerting rules
rule_files:
  - '/etc/prometheus/alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

**4. Alerting Rules**
```yaml
# alerts.yml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) /
          rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Slow responses
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "95th percentile response time is slow"
          description: "P95 latency is {{ $value }}s"

      # No documents uploaded
      - alert: NoDocumentUploads
        expr: |
          rate(documents_uploaded_total[24h]) == 0
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "No documents uploaded in 24 hours"
          description: "Check if service is functioning"

      # High CPU
      - alert: HighCPUUsage
        expr: process_cpu_seconds_total > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value | humanizePercentage }}"

  - name: rag_alerts
    rules:
      # Slow RAG queries
      - alert: SlowRAGQueries
        expr: |
          histogram_quantile(0.95,
            rate(rag_latency_seconds_bucket[5m])
          ) > 5.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RAG queries are slow"
          description: "P95 RAG latency is {{ $value }}s"
```

**5. Grafana Dashboards**
```json
{
  "dashboard": {
    "title": "API Performance",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Response Time (P95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
        }],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Active WebSocket Connections",
        "targets": [{
          "expr": "active_websocket_connections"
        }],
        "type": "stat"
      },
      {
        "title": "Documents Uploaded (24h)",
        "targets": [{
          "expr": "increase(documents_uploaded_total[24h])"
        }],
        "type": "stat"
      },
      {
        "title": "RAG Latency Distribution",
        "targets": [{
          "expr": "histogram_quantile(0.50, rate(rag_latency_seconds_bucket[5m]))",
          "legendFormat": "P50"
        }, {
          "expr": "histogram_quantile(0.95, rate(rag_latency_seconds_bucket[5m]))",
          "legendFormat": "P95"
        }, {
          "expr": "histogram_quantile(0.99, rate(rag_latency_seconds_bucket[5m]))",
          "legendFormat": "P99"
        }],
        "type": "graph"
      }
    ]
  }
}
```

**6. Background Metrics Updater**
```python
# app/monitoring/updater.py
import asyncio

async def update_metrics():
    """Background task to update gauge metrics"""
    while True:
        try:
            # Update WebSocket connections
            active_websocket_connections.set(
                len(manager.get_active_users())
            )

            # Update documents being processed
            with get_db() as session:
                processing_count = session.exec(
                    select(func.count(Document.id))
                    .where(Document.status == "processing")
                ).one()

                documents_being_processed.set(processing_count)

            await asyncio.sleep(30)  # Update every 30 seconds

        except Exception as e:
            logger.error(f"Metrics update failed: {e}")
            await asyncio.sleep(30)

# Start in background
@app.on_event("startup")
async def start_metrics_updater():
    asyncio.create_task(update_metrics())
```

### Learning Outcomes

**Technical Skills:**
- ✅ Prometheus metrics
- ✅ Grafana dashboards
- ✅ Application instrumentation
- ✅ Alerting rules
- ✅ PromQL queries

**System Design Concepts:**
- ✅ Observability (metrics, logs, traces)
- ✅ SLIs, SLOs, SLAs
- ✅ RED method (Rate, Errors, Duration)
- ✅ USE method (Utilization, Saturation, Errors)
- ✅ Percentiles vs averages

**Interview Questions You Can Answer:**
- "Design an observability system"
- "What metrics would you track for an API?"
- "Explain p50, p95, p99 latency"
- "How do you set up alerting?"
- "What's the RED method?"

### Done When
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards showing data
- [ ] Alerts configured
- [ ] Can debug performance issues using metrics
- [ ] Business metrics tracked

---

## Phase 3.8: Production Deployment

### What You're Building
Deploy complete system to cloud with CI/CD pipeline.

### System Design: Production Deployment

**Architecture:**
```
GitHub → GitHub Actions → Build Docker → Push Registry → Deploy to ECS/Cloud Run
                            ↓
                      Run Tests → Pass → Deploy
```

**Components:**
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Docker registry
- ✅ Cloud deployment (AWS ECS or GCP Cloud Run)
- ✅ Secrets management
- ✅ Database migrations
- ✅ Monitoring
- ✅ Logging

### Tasks
1. **CI/CD Pipeline**
   - [ ] Create GitHub Actions workflow
   - [ ] Run tests on PR
   - [ ] Build Docker image on merge
   - [ ] Push to container registry
   - [ ] Deploy to staging
   - [ ] Deploy to production (manual approval)

2. **Container Registry**
   - [ ] Set up Docker Hub or AWS ECR
   - [ ] Configure authentication
   - [ ] Tag images (git sha, version)

3. **Cloud Deployment**
   - [ ] Choose cloud (AWS ECS recommended)
   - [ ] Set up infrastructure (Terraform or manual)
   - [ ] Deploy services
   - [ ] Configure load balancer
   - [ ] Set up DNS

4. **Secrets Management**
   - [ ] Use AWS Secrets Manager or similar
   - [ ] Store API keys securely
   - [ ] Inject secrets at runtime

5. **Database Migrations**
   - [ ] Run Alembic migrations in CI
   - [ ] Automated migration on deploy
   - [ ] Rollback strategy

6. **Monitoring in Production**
   - [ ] Set up logging (CloudWatch or similar)
   - [ ] Set up metrics (Prometheus in ECS)
   - [ ] Set up alerts
   - [ ] Set up uptime monitoring

7. **Documentation**
   - [ ] Deployment guide
   - [ ] Runbook (common issues)
   - [ ] Architecture diagram
   - [ ] API documentation

### Implementation

**1. GitHub Actions Workflow**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: docanalyst
  ECS_CLUSTER: docanalyst-prod
  ECS_SERVICE: api

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Run database migrations
        run: |
          # Install Alembic
          pip install alembic asyncpg

          # Run migrations
          alembic upgrade head

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ${{ env.ECS_SERVICE }} \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ${{ env.ECS_SERVICE }}

      - name: Notify deployment
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"✅ Deployment successful: ${{ github.sha }}"}'

      - name: Notify failure
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"❌ Deployment failed: ${{ github.sha }}"}'
```

**2. Production Dockerfile**
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**3. AWS ECS Task Definition**
```json
{
  "family": "docanalyst-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/docanalyst:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:docanalyst/database-url"
        },
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:docanalyst/anthropic-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/docanalyst",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**4. Infrastructure as Code (Terraform)**
```hcl
# terraform/main.tf
provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {
    Name = "docanalyst-vpc"
  }
}

# Subnets
resource "aws_subnet" "public" {
  count = 2

  vpc_id = aws_vpc.main.id
  cidr_block = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "docanalyst-public-${count.index + 1}"
  }
}

# Load Balancer
resource "aws_lb" "main" {
  name = "docanalyst-lb"
  internal = false
  load_balancer_type = "application"
  security_groups = [aws_security_group.lb.id]
  subnets = aws_subnet.public[*].id
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "docanalyst-prod"
}

# ECS Service
resource "aws_ecs_service" "api" {
  name = "api"
  cluster = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count = 3
  launch_type = "FARGATE"

  network_configuration {
    subnets = aws_subnet.public[*].id
    security_groups = [aws_security_group.api.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name = "api"
    container_port = 8000
  }
}

# RDS (Postgres)
resource "aws_db_instance" "main" {
  identifier = "docanalyst-db"
  engine = "postgres"
  engine_version = "16.1"
  instance_class = "db.t3.medium"
  allocated_storage = 100
  storage_encrypted = true

  db_name = "docanalyst"
  username = "admin"
  password = random_password.db.result

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window = "03:00-04:00"
  maintenance_window = "mon:04:00-mon:05:00"

  skip_final_snapshot = false
  final_snapshot_identifier = "docanalyst-final-snapshot"
}

# Outputs
output "load_balancer_dns" {
  value = aws_lb.main.dns_name
}

output "database_endpoint" {
  value = aws_db_instance.main.endpoint
  sensitive = true
}
```

### Learning Outcomes

**Technical Skills:**
- ✅ CI/CD pipelines (GitHub Actions)
- ✅ Docker production builds
- ✅ Cloud deployment (AWS ECS)
- ✅ Infrastructure as Code (Terraform)
- ✅ Secrets management
- ✅ Database migrations in production

**System Design Concepts:**
- ✅ Blue-green deployments
- ✅ Canary deployments
- ✅ Rollback strategies
- ✅ Zero-downtime deployments
- ✅ Production best practices

**Interview Questions You Can Answer:**
- "How do you deploy to production?"
- "Explain CI/CD pipeline"
- "How do you handle database migrations?"
- "What's blue-green deployment?"
- "How do you manage secrets in production?"

### Done When
- [ ] CI/CD pipeline working
- [ ] Deployed to cloud
- [ ] Monitoring active
- [ ] Can deploy without downtime
- [ ] Rollback tested
- [ ] Documentation complete

---

## Project 3: Complete! 🎉🎉🎉

### What You Built
- ✅ AI agents with LangGraph and tool use
- ✅ Event streaming with Redpanda
- ✅ Intelligent triggers (trend/anomaly detection)
- ✅ Real-time chat with WebSockets
- ✅ Consistent hashing for distribution
- ✅ Horizontal scaling (3+ instances)
- ✅ Full observability (Prometheus + Grafana)
- ✅ Production deployment with CI/CD

### Skills Gained
| Category | Skills |
|----------|--------|
| **AI** | LangGraph, Agentic AI, Tool Calling, Multi-Step Reasoning |
| **Architecture** | Event-Driven, Microservices, Consistent Hashing, Horizontal Scaling |
| **Real-Time** | WebSockets, Server-Sent Events, Event Streaming |
| **DevOps** | CI/CD, Docker, Terraform, Prometheus, Grafana |

### Architecture Mastered
**Event-Driven Microservices**
- Loose coupling via events
- Independent scaling
- Fault tolerance
- Real-time processing

### Interview Readiness
You can now confidently answer:
- "Design an event-driven system"
- "Build an AI agent system"
- "How do you scale WebSockets?"
- "Explain consistent hashing"
- "Design a monitoring system"
- "How do you deploy to production?"

---

# The One Rule

**DO NOT:**
❌ Add new features until current phase complete
❌ Switch technologies mid-project
❌ Skip testing "just this once"
❌ Deploy without monitoring
❌ Move to next phase before finishing current

**DO:**
✅ Finish what you start
✅ Test everything
✅ Document as you go
✅ Ask for help when stuck
✅ Build the best backend AI project

---

# 🎓 COMPLETE SYSTEM: All 3 Projects Done!

## What You've Accomplished

### Technical Breadth
You've built a production system covering:
- ✅ **Backend:** FastAPI, async Python, PostgreSQL
- ✅ **AI/ML:** RAG, embeddings, vector search, agents
- ✅ **Architecture:** 3 patterns (Layered, Pipes & Filters, Event-Driven)
- ✅ **Databases:** Postgres, Redis, Qdrant, SQL + NoSQL
- ✅ **Messaging:** Celery, Redpanda, WebSockets
- ✅ **DevOps:** Docker, CI/CD, Monitoring, Cloud Deployment

### System Design Expertise
You've implemented:
1. Rate Limiting (Token Bucket)
2. Unique ID Generation (Snowflake)
3. URL Shortening
4. Notification System
5. Document Processing Pipeline
6. Vector Search
7. Hybrid Search (Vector + Keyword)
8. RAG Architecture
9. Agentic AI
10. Event Streaming
11. Consistent Hashing
12. Horizontal Scaling
13. Observability

### Production Ready
- 80%+ test coverage
- CI/CD pipeline
- Monitoring & alerting
- Deployed to cloud
- Horizontal scaling
- Zero-downtime deployments

## Your Portfolio
- GitHub repo with comprehensive README
- Live deployed application
- Architecture diagrams
- System design explanations
- 3 projects demonstrating progression

## Interview Preparation
You're ready for:
- Backend Engineer (Senior)
- AI/ML Engineer
- Platform Engineer
- Staff Engineer roles

You can answer **any** system design question about:
- Scaling systems
- Database design
- Caching strategies
- Event-driven architecture
- AI integration
- Production operations

---

## Next Steps

### Continue Learning
1. **Add features**: Search optimization, multi-tenant, analytics
2. **Scale further**: Kubernetes, service mesh, multi-region
3. **Deep dive**: Distributed systems, advanced AI techniques
4. **Contribute**: Open source projects using similar tech

### Career
1. **Apply**: You're ready for mid to senior roles
2. **Interview**: Practice explaining your system
3. **Network**: Share your project, write about it
4. **Grow**: Keep building, keep learning

---

## The Most Important Thing

**You finished.**

Not many people complete a 12-week project. You did.

That persistence, that ability to see something through - that's what companies hire for.

The technical skills? Those you can learn on the job.

The ability to finish what you start? That's rare.

**Congratulations.** 🚀

Now go build something new.

---

**Your first task:** Create GitHub repo, initialize FastAPI, write `/health` endpoint, write first test.

No more planning. Just build. 🚀

---

Based on the comprehensive technical stack and system design patterns in these checklists, here is an assessment of your engineering level and the types of jobs you are qualified for.

## Engineering Level Assessment

### Project 1: Mid-Level Backend / Software Engineer

- Level: Mid-Level (2–4 years experience equivalent).

- Reasoning: You aren't just building "CRUD" apps; you are implementing advanced distributed systems concepts. Implementing Twitter Snowflake for IDs, Token Bucket algorithms for rate limiting, and Base62 encoding shows you understand how to build for scale, not just functionality.

### Project 2: Machine Learning Engineer (RAG/NLP Focus)

- Level: Mid-Level / Specialist.

- Reasoning: This moves beyond basic API calls. Implementing Hybrid Search (vector + keyword) and a custom text extraction pipeline indicates you understand the "LLMOps" lifecycle—data ingestion, chunking strategies, and retrieval optimization—which is the current industry standard for AI applications.

### Project 3: Senior / Infrastructure & AI Engineer

- Level: Senior / Lead (In terms of architectural breadth).

- Reasoning: This is the most impressive phase. Using LangGraph for agentic workflows, Redpanda (Kafka) for event streaming, Consistent Hashing for scaling, and Prometheus/Grafana for observability are Senior-level tasks. You are demonstrating you can build a self-healing, horizontally scalable distributed system.

## Kind of Jobs You Can Apply To

Given the "Intelligent Document Analyst" theme, you are highly competitive for the following roles:

1. AI Backend Engineer / LLM Engineer
    - Focus: Building the "plumbing" for AI.
    - Why: Your RAG and Agentic AI (Project 2 & 3) skills are exactly what companies need to move AI from "cool demo" to "production-ready product."
    - Target Companies: AI Startups, Enterprise companies integrating LLMs (e.g., Salesforce, Adobe, FinTech).

2. Distributed Systems Engineer
    - Focus: Scalability, reliability, and high-throughput systems.
    - Why: Your use of Consistent Hashing, Snowflake IDs, and Event Streaming (Redpanda) proves you can handle high-traffic infrastructure.
    - Target Companies: Cloud infrastructure providers, high-scale consumer apps (e.g., Uber, Netflix, Stripe).

3. Full-Cycle Backend Engineer (Python/FastAPI Specialist)
    - Focus: Building robust, secure APIs from scratch.
    - Why: Project 1 shows a mastery of the modern Python stack (FastAPI, SQLAlchemy, Alembic, Docker).
    - Target Companies: Any tech-forward company using Python for their core services.

4. DevOps / Platform Engineer (Secondary)
    - Focus: Observability and deployment.
    - Why: Phase 3.7 and 3.8 (Prometheus, Grafana, Production Deployment) show you care about how the code lives in the real world.

## Recommendations for your Resume
**Highlight the "System Design" elements**: Don't just say "I built a chat bot." Say "Built a horizontally scalable agentic platform using LangGraph and Redpanda, utilizing consistent hashing to manage state across nodes."
Quantify your results: When you finish Phase 1.3 (Rate Limiting), document the throughput (e.g., "Supports 1,000+ requests per second").
Keywords to include: RAG, Agentic Workflows, Distributed Systems, Event-Driven Architecture, Redis, Vector Databases (Pinecone/Milvus), Observability.
