# Architecture Diagrams - ASCII Art Style
# Intelligent Document Analyst

---

## Project 1: RESTful API Foundation

### Phase 1.1: Foundation - Basic CRUD API

```
┌─────────────────┐
│  Client/Browser │
└────────┬────────┘
         │ HTTP REST (GET, POST, PUT, DELETE)
         │
    ┌────▼────────────┐
    │   FastAPI       │
    │   Application   │
    │                 │
    │  Endpoints:     │
    │  • /health      │
    │  • /auth/       │
    │    register     │
    │  • /documents   │
    └────────┬────────┘
             │ SQL Queries
             │
        ┌────▼────────┐         ┌──────────┐
        │ PostgreSQL  │◄────────│ Alembic  │
        │             │         │Migration │
        │  Tables:    │         └──────────┘
        │  • users    │
        │  • documents│
        └─────────────┘
```

**Key Components:**
- FastAPI with async support
- PostgreSQL for data persistence
- Alembic for schema migrations
- Basic CRUD operations

---

### Phase 1.2: Authentication & Security

```
┌──────────────┐
│    Client    │
└──────┬───────┘
       │ HTTP + JWT Token
       │
┌──────▼────────────────────────────────┐
│      Security Middleware              │
│  ┌─────────────────────────────────┐  │
│  │  1. CORS Check                  │  │
│  │  2. Rate Limit Check            │  │
│  │  3. JWT Validation              │  │
│  │  4. Security Headers            │  │
│  └─────────────────────────────────┘  │
└──────┬────────────────────────────────┘
       │
┌──────▼──────────┐
│  FastAPI        │
│  Endpoints      │
│                 │
│  Auth:          │
│  • /login  ───► Generate JWT (access + refresh)
│  • /refresh ──► New access token
│  • /logout ───► Blacklist token
│                 │
│  Protected:     │
│  • /documents/* │
└────┬──────┬─────┘
     │      │
     │      └────────────┐
     │                   │
┌────▼─────────┐   ┌─────▼──────────┐
│ PostgreSQL   │   │  Redis         │
│              │   │                │
│ • users      │   │ • token_       │
│ • documents  │   │   blacklist    │
└──────────────┘   └────────────────┘
```

**Security Features:**
- JWT tokens (access: 15min, refresh: 7 days)
- bcrypt password hashing
- Token blacklist in Redis
- CORS & security headers
- Role-based access control

---

### Phase 1.3: Rate Limiting

```
┌──────────────┐
│   Client     │
└──────┬───────┘
       │ Request
       │
┌──────▼─────────────────────────────────┐
│    Rate Limit Middleware               │
│                                        │
│  1. Extract user_id from JWT          │
│  2. Check token bucket in Redis       │
│  3. Token Bucket Algorithm:           │
│     ┌─────────────────────────┐       │
│     │ tokens = min(           │       │
│     │   capacity,             │       │
│     │   current + refill_rate │       │
│     │ )                       │       │
│     └─────────────────────────┘       │
│  4. Consume 1 token                   │
└──────┬─────────────────────────────────┘
       │
       ├─── Tokens Available ──►┌────────────┐
       │                        │  Process   │
       │                        │  Request   │
       │                        └────────────┘
       │
       └─── No Tokens ────────►┌─────────────────────┐
                               │  429 Too Many       │
                               │  Requests           │
                               │                     │
                               │  Headers:           │
                               │  X-RateLimit-Limit  │
                               │  X-RateLimit-       │
                               │    Remaining        │
                               │  X-RateLimit-Reset  │
                               └─────────────────────┘

┌────────────────┐
│  Redis         │
│                │
│  Key: rate:    │
│    {user_id}   │
│  Value:        │
│  {             │
│    tokens: 8,  │
│    last_refill │
│  }             │
└────────────────┘
```

**Rate Limits:**
- Free: 10 requests/min
- Paid: 100 requests/min
- Refill: Continuous (Token Bucket)

---

### Phase 1.4: Unique ID Generation

```
┌─────────────────────────────────────────────────────┐
│          Snowflake ID Generator                     │
│                                                     │
│  64-bit ID Structure:                              │
│  ┌──────────┬────────┬────────┬──────────┐        │
│  │Timestamp │Datactr │Worker  │ Sequence │        │
│  │ 41 bits  │ 5 bits │ 5 bits │ 12 bits  │        │
│  └──────────┴────────┴────────┴──────────┘        │
│                                                     │
│  Example: 1234567890123456789                      │
│  ────────────────────────────────────────          │
│  • Unique across distributed systems               │
│  • Sortable by creation time                       │
│  • Thread-safe                                     │
│  • 4096 IDs per millisecond per worker             │
└───────────────┬─────────────────────────────────────┘
                │
        ┌───────▼────────┐
        │  API Request   │
        │  (Create Doc)  │
        └───────┬────────┘
                │
        ┌───────▼──────────────┐
        │  Generate ID         │
        │  → 1234567890123456  │
        └───────┬──────────────┘
                │
        ┌───────▼────────┐
        │  PostgreSQL    │
        │                │
        │  documents:    │
        │  id: bigint    │
        └────────────────┘
```

**Properties:**
- 4096 IDs/ms per worker
- 1024 workers across 32 datacenters
- Handles clock skew
- Thread-safe generation

---

### Phase 1.5: URL Shortener

```
┌──────────────────┐
│   Long URL       │
│  /documents/     │
│  1234567890123   │
└────────┬─────────┘
         │ POST /shorten
         │
    ┌────▼─────────────┐
    │  API Handler     │
    └────┬─────────────┘
         │
    ┌────▼───────────────────────────┐
    │  Base62 Encoding               │
    │                                │
    │  Input:  1234567890123 (ID)    │
    │  Charset: 0-9, a-z, A-Z (62)   │
    │  Output: aBc123X (7 chars)     │
    │                                │
    │  3.5 trillion possible codes   │
    └────┬───────────────────────────┘
         │
    ┌────▼────────────┐
    │  PostgreSQL     │
    │                 │
    │  short_urls:    │
    │  ┌───────────┐  │
    │  │short_code │  │ ← Index for fast lookup
    │  │document_id│  │
    │  │created_at │  │
    │  │clicks     │  │
    │  └───────────┘  │
    └─────────────────┘

User Access Flow:
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │ GET /{short_code}
       │
  ┌────▼──────────────┐
  │  Lookup Handler   │
  └────┬──────────────┘
       │ Query: WHERE short_code = ?
       │
  ┌────▼────────────┐
  │  PostgreSQL     │
  │  Find document  │
  └────┬────────────┘
       │
  ┌────▼──────────────────┐
  │  Increment clicks     │
  │  Redirect 301         │
  │  → /documents/{id}    │
  └───────────────────────┘
```

**Analytics:**
- Click tracking
- Timestamp logging
- Source tracking (optional)

---

### Phase 1.6: Notification System

```
                    ┌─────────────────────┐
                    │   Event Triggers    │
                    │                     │
                    │ • document_uploaded │
                    │ • query_completed   │
                    │ • processing_failed │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Notification Service │
                    └──┬────────┬────────┬─┘
                       │        │        │
         ┌─────────────┘        │        └────────────┐
         │                      │                     │
    ┌────▼─────────┐   ┌────────▼──────┐   ┌─────────▼───────┐
    │   In-App     │   │   Webhook     │   │     Email       │
    │   Channel    │   │   Channel     │   │    Channel      │
    └────┬─────────┘   └────────┬──────┘   └─────────┬───────┘
         │                      │                     │
         │                      │                     │
    ┌────▼──────────┐   ┌───────▼──────────┐   ┌─────▼──────────┐
    │ PostgreSQL    │   │  HTTP POST       │   │ Background     │
    │               │   │  to webhook URL  │   │ Task Queue     │
    │ notifications │   │                  │   │                │
    │ ┌───────────┐ │   │ POST /webhook    │   │ ┌────────────┐ │
    │ │user_id    │ │   │ {                │   │ │Send Email  │ │
    │ │type       │ │   │   event: "...",  │   │ │via SMTP    │ │
    │ │title      │ │   │   data: {...}    │   │ └────────────┘ │
    │ │message    │ │   │ }                │   └────────────────┘
    │ │read_at    │ │   └──────────────────┘
    │ │created_at │ │
    │ └───────────┘ │
    └───────────────┘

User Retrieval:
┌─────────────┐
│    User     │
└──────┬──────┘
       │ GET /notifications
       │
  ┌────▼──────────────────┐
  │  API Handler          │
  │                       │
  │  Filters:             │
  │  • Unread only        │
  │  • By type            │
  │  • Pagination         │
  └────┬──────────────────┘
       │
  ┌────▼──────────┐
  │  PostgreSQL   │
  │  Query:       │
  │  WHERE user_id│
  │    = ?        │
  │  AND read_at  │
  │    IS NULL    │
  └───────────────┘
```

**Features:**
- Multiple delivery channels
- Unread count tracking
- Mark as read
- Delete notifications

---

### Phase 1.7: Production Ready - Complete Project 1

```
┌──────────────────────────────────────────────────────────────┐
│                    Internet / Clients                        │
└────────────────────────────┬─────────────────────────────────┘
                             │
                ┌────────────▼─────────────┐
                │   Load Balancer (nginx)  │
                │   • SSL Termination      │
                │   • Health Checks        │
                │   • Sticky Sessions      │
                └───┬──────────────┬───────┘
                    │              │
       ┌────────────┴──┐      ┌────┴───────────┐
       │               │      │                │
  ┌────▼────────┐ ┌───▼───────┐ ┌─────────────▼──┐
  │ FastAPI #1  │ │FastAPI #2 │ │  FastAPI #3    │
  │             │ │           │ │                │
  │ Middleware: │ │           │ │                │
  │ • Security  │ │           │ │                │
  │ • CORS      │ │           │ │                │
  │ • Rate Lim  │ │           │ │                │
  │ • JWT Auth  │ │           │ │                │
  └─────┬───────┘ └─────┬─────┘ └────────┬───────┘
        │               │                 │
        └───────────────┼─────────────────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
   ┌────▼─────┐   ┌─────▼──────┐   ┌────▼──────┐
   │PostgreSQL│   │   Redis    │   │  Logging  │
   │          │   │            │   │           │
   │Tables:   │   │• Rate      │   │• JSON     │
   │• users   │   │  limits    │   │  format   │
   │• docs    │   │• Token     │   │• Request  │
   │• short_  │   │  blacklist │   │  tracking │
   │  urls    │   │• Cache     │   │• Errors   │
   │• notifs  │   │            │   │           │
   └──────────┘   └────────────┘   └───────────┘

Features Implemented:
┌─────────────────────────────────────────────────────┐
│ ✓ RESTful API (15+ endpoints)                      │
│ ✓ JWT Authentication + Refresh Tokens              │
│ ✓ Token Bucket Rate Limiting                       │
│ ✓ Snowflake ID Generation                          │
│ ✓ URL Shortener with Analytics                     │
│ ✓ Multi-channel Notifications                      │
│ ✓ 80%+ Test Coverage                               │
│ ✓ Docker Compose Setup                             │
│ ✓ Horizontal Scaling Ready                         │
└─────────────────────────────────────────────────────┘
```

---

## Project 2: RAG System

### Phase 2.1: Document Upload & Storage

```
┌────────────┐
│   Client   │
└──────┬─────┘
       │ POST /documents/upload
       │ (multipart/form-data)
       │
  ┌────▼──────────────────────┐
  │  FastAPI Upload Handler   │
  │                           │
  │  1. Validate file         │
  │     • Type: PDF/DOCX/TXT  │
  │     • Size: < 50MB        │
  │  2. Generate unique name  │
  │  3. Store file            │
  └────┬──────────────────────┘
       │
       ├─────────────────┬──────────────────┐
       │                 │                  │
  ┌────▼───────┐    ┌────▼────────┐   ┌────▼──────────┐
  │  MinIO S3  │    │ PostgreSQL  │   │ Set Status    │
  │            │    │             │   │ = "uploading" │
  │ Store file │    │ documents:  │   └───────────────┘
  │ in bucket  │    │ ┌─────────┐ │
  │            │    │ │id       │ │
  │ Path:      │    │ │title    │ │
  │ /docs/     │    │ │owner_id │ │
  │ {uuid}.pdf │    │ │file_path│ │
  │            │    │ │file_size│ │
  │            │    │ │mime_type│ │
  │            │    │ │status   │ │ ← "uploading"
  │            │    │ │error_msg│ │   "processing"
  └────────────┘    │ └─────────┘ │   "completed"
                    └─────────────┘   "failed"

Download Flow:
┌────────────┐
│   Client   │
└──────┬─────┘
       │ GET /documents/{id}/download
       │
  ┌────▼────────────────┐
  │  Check Ownership    │
  │  (JWT validation)   │
  └────┬────────────────┘
       │
       ├─── Authorized ──►┌──────────────┐
       │                  │ Fetch from   │
       │                  │ MinIO        │
       │                  └──────┬───────┘
       │                         │
       │                  ┌──────▼──────────┐
       │                  │ Stream to Client│
       │                  │ Content-Type set│
       │                  └─────────────────┘
       │
       └─── Forbidden ───►┌──────────────┐
                         │ 403 Error    │
                         └──────────────┘
```

**Supported Formats:**
- PDF, DOCX, TXT, Markdown
- Max size: 50MB

---

### Phase 2.2: Text Extraction Pipeline

```
                  ┌──────────────────┐
                  │  Document Ready  │
                  │  (status: ready) │
                  └────────┬─────────┘
                           │
                  ┌────────▼──────────┐
                  │ Document Router   │
                  │ (by MIME type)    │
                  └────┬──────┬───┬───┘
                       │      │   │
        ┌──────────────┘      │   └──────────────┐
        │                     │                  │
   ┌────▼────┐         ┌──────▼─────┐     ┌─────▼────┐
   │  PDF    │         │   DOCX     │     │ TXT/MD   │
   │ PyPDF2  │         │python-docx │     │  Plain   │
   │Extractor│         │ Extractor  │     │  Reader  │
   └────┬────┘         └──────┬─────┘     └─────┬────┘
        │                     │                  │
        └──────────────┬──────┴──────────────────┘
                       │ Raw Text
                       │
              ┌────────▼─────────┐
              │   Text Cleaner   │
              │                  │
              │ • Remove \n\n\n  │
              │ • Fix whitespace │
              │ • Strip special  │
              │   characters     │
              └────────┬─────────┘
                       │ Cleaned Text
                       │
              ┌────────▼──────────┐
              │   Text Chunker    │
              │                   │
              │ • Split: 500 tok  │
              │ • Overlap: 100    │
              │ • Generate IDs    │
              └────────┬──────────┘
                       │
              ┌────────▼──────────┐
              │   PostgreSQL      │
              │                   │
              │   chunks:         │
              │   ┌────────────┐  │
              │   │id          │  │
              │   │document_id │  │
              │   │text        │  │
              │   │chunk_index │  │
              │   │token_count │  │
              │   └────────────┘  │
              └───────────────────┘

Pipeline Result:
┌─────────────────────────────────────────┐
│ Document: "Annual Report 2024.pdf"      │
│ Size: 5 MB                              │
│ → 150 chunks created                    │
│ → Average: 450 tokens/chunk             │
│ → Status: "processing" → "completed"    │
└─────────────────────────────────────────┘
```

---

### Phase 2.3: Vector Embeddings & Search

```
┌─────────────────────────────────────────────────────┐
│              Embedding Generation                   │
└─────────────────────────────────────────────────────┘

┌───────────────┐
│  Chunks Table │
└───────┬───────┘
        │ For each chunk
        │
   ┌────▼─────────────┐
   │ Embedding Worker │
   └────┬─────────────┘
        │ API Call
        │
   ┌────▼──────────────────────────┐
   │      OpenAI API               │
   │  text-embedding-3-small       │
   │                               │
   │  Input: "The company revenue  │
   │          increased by 25%..." │
   │  Output: [0.123, -0.456, ...] │
   │          (1536 dimensions)    │
   └────┬──────────────────────────┘
        │ Vector
        │
   ┌────▼──────────────┐
   │  PostgreSQL       │
   │  + pgvector ext   │
   │                   │
   │  chunks:          │
   │  ┌──────────────┐ │
   │  │id            │ │
   │  │text          │ │
   │  │embedding     │ │ ← vector(1536)
   │  └──────────────┘ │
   │                   │
   │  Index: HNSW     │ ← Fast similarity search
   └───────────────────┘

┌─────────────────────────────────────────────────────┐
│              Vector Search                          │
└─────────────────────────────────────────────────────┘

┌──────────────────┐
│  User Query:     │
│  "What was the   │
│   revenue growth?"
└────────┬─────────┘
         │
    ┌────▼─────────────┐
    │ Embed Query      │
    │ (same model)     │
    └────┬─────────────┘
         │ Query Vector [0.111, -0.222, ...]
         │
    ┌────▼─────────────────────────────────┐
    │  PostgreSQL Vector Search            │
    │                                      │
    │  SELECT text, embedding <=> $1 AS    │
    │    distance                          │
    │  FROM chunks                         │
    │  ORDER BY distance                   │
    │  LIMIT 5;                            │
    │                                      │
    │  Uses: Cosine Similarity             │
    │  Index: HNSW for speed               │
    └────┬─────────────────────────────────┘
         │ Top 5 Most Similar Chunks
         │
    ┌────▼────────────────┐
    │  Results:           │
    │  1. "Revenue grew   │
    │      25% YoY..."    │
    │     (similarity:    │
    │      0.89)          │
    │  2. "Q4 showed..."  │
    │     (similarity:    │
    │      0.85)          │
    │  ...                │
    └─────────────────────┘
```

**Vector Search Performance:**
- HNSW index: ~100ms for 1M vectors
- Cosine similarity metric
- Top-K retrieval

---

### Phase 2.4: RAG Query System

```
┌───────────────────────────────────────────────────────────┐
│                  RAG Pipeline (3 Steps)                   │
└───────────────────────────────────────────────────────────┘

┌────────────┐
│   User:    │
│ "What was  │
│  the main  │
│  finding?" │
└──────┬─────┘
       │
       │
┏━━━━━━▼━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 1: RETRIEVE                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
       │
  ┌────▼──────────────┐
  │ Vector Search     │
  │ (pgvector)        │
  └────┬──────────────┘
       │ Top 5 Chunks
       │
  ┌────▼────────────────────────────┐
  │ Retrieved Context:              │
  │ • "The study found that..."     │
  │ • "Main conclusion: X leads..." │
  │ • "Results show significant..." │
  │ • "Key finding: improvement..." │
  │ • "Data indicates that..."      │
  └────┬────────────────────────────┘
       │
┏━━━━━━▼━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 2: AUGMENT                                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
       │
  ┌────▼──────────────────────────────────┐
  │ Construct Prompt:                     │
  │                                       │
  │ """                                   │
  │ Context from documents:               │
  │ [Retrieved chunks here]               │
  │                                       │
  │ User Question: What was the main      │
  │ finding?                              │
  │                                       │
  │ Instructions: Answer based on the     │
  │ context. Cite sources. If unsure,     │
  │ say so.                               │
  │ """                                   │
  └────┬──────────────────────────────────┘
       │
┏━━━━━━▼━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  STEP 3: GENERATE                                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
       │
  ┌────▼───────────────┐
  │  OpenAI GPT-4      │
  │  (LLM)             │
  └────┬───────────────┘
       │ Generated Answer
       │
  ┌────▼────────────────────────────────────┐
  │ Post-Processing:                        │
  │ • Add source citations                  │
  │ • Calculate confidence score            │
  │ • Format response                       │
  └────┬────────────────────────────────────┘
       │
  ┌────▼────────────────────────────────────┐
  │ Response:                               │
  │                                         │
  │ Answer: "The main finding was that X    │
  │ significantly improved Y by 30%."       │
  │                                         │
  │ Sources:                                │
  │ • Document: "Research Report"           │
  │   Chunk #12, #34                        │
  │                                         │
  │ Confidence: 0.92                        │
  └─────────────────────────────────────────┘
```

---

### Phase 2.5: Background Processing with Workers

```
┌──────────────┐
│  API Upload  │
│  Complete    │
└──────┬───────┘
       │ Enqueue Task
       │
  ┌────▼──────────────────────┐
  │    Redis Queue (RQ)       │
  │                           │
  │  Queue: "document_tasks"  │
  │  ┌─────────────────────┐  │
  │  │ task_id: uuid       │  │
  │  │ document_id: 123    │  │
  │  │ status: pending     │  │
  │  │ priority: normal    │  │
  │  └─────────────────────┘  │
  └───┬────────────┬──────┬───┘
      │            │      │
      │            │      │
┌─────▼──────┐ ┌──▼──────┐ ┌──▼────────┐
│ Worker 1   │ │Worker 2 │ │ Worker 3  │
│            │ │         │ │           │
│ Pick task  │ │         │ │           │
└─────┬──────┘ └─────────┘ └───────────┘
      │
      │ Execute Pipeline:
      │
 ┌────▼─────────────────────────────┐
 │  1. Fetch file from MinIO        │
 └────┬─────────────────────────────┘
      │
 ┌────▼─────────────────────────────┐
 │  2. Extract text (by file type)  │
 └────┬─────────────────────────────┘
      │
 ┌────▼─────────────────────────────┐
 │  3. Chunk text (500 tokens)      │
 └────┬─────────────────────────────┘
      │
 ┌────▼─────────────────────────────┐
 │  4. Generate embeddings (OpenAI) │
 └────┬─────────────────────────────┘
      │
 ┌────▼─────────────────────────────┐
 │  5. Store in PostgreSQL          │
 └────┬─────────────────────────────┘
      │
 ┌────▼─────────────────────────────┐
 │  6. Update status: "completed"   │
 └──────────────────────────────────┘

Error Handling:
┌────────────────────────────────┐
│  If task fails:                │
│  • Retry 3 times               │
│  • Exponential backoff         │
│  • Set status: "failed"        │
│  • Store error_message         │
│  • Send notification to user   │
└────────────────────────────────┘

Status Tracking:
┌──────────────────────────────────┐
│  PostgreSQL documents table:     │
│  ┌──────────────────────────┐    │
│  │ id: 123                  │    │
│  │ status: "processing"     │    │
│  │ progress: 45%            │    │
│  │ current_step:            │    │
│  │   "generating_embeddings"│    │
│  └──────────────────────────┘    │
└──────────────────────────────────┘
```

---

### Phase 2.6: Multi-Layer Caching Strategy

```
┌──────────────────────────────────────────────────────────┐
│                   Caching Architecture                   │
└──────────────────────────────────────────────────────────┘

Request Flow:

┌──────────────┐
│  User Query  │
└──────┬───────┘
       │ "What is the revenue?"
       │
  ┌────▼─────────────────────────────┐
  │  LAYER 1: Query Result Cache    │
  │  Redis Key: query:{hash}         │
  │  TTL: 5 minutes                  │
  └────┬─────────────────────────────┘
       │
       ├─── Cache HIT ──────►┌─────────────┐
       │                     │ Return      │
       │                     │ Cached      │
       │                     │ Result      │
       │                     └─────────────┘
       │
       └─── Cache MISS ──┐
                         │
       ┌─────────────────▼──────────────┐
       │  LAYER 2: Embedding Cache      │
       │  Redis Key: embed:{text_hash}  │
       │  TTL: 1 hour                   │
       └────┬───────────────────────────┘
            │
            ├─── Cache HIT ──►┌──────────────┐
            │                 │ Skip OpenAI  │
            │                 │ API call     │
            │                 └──────────────┘
            │
            └─── Cache MISS ──┐
                              │
       ┌──────────────────────▼─────────┐
       │  Generate Embedding (OpenAI)   │
       │  Store in Layer 2 cache        │
       └────┬───────────────────────────┘
            │
       ┌────▼────────────────────────────┐
       │  LAYER 3: Document Cache        │
       │  Redis Key: doc:{id}            │
       │  TTL: 15 minutes                │
       └────┬────────────────────────────┘
            │
            ├─── Cache HIT ──►┌──────────────┐
            │                 │ Return       │
            │                 │ Document     │
            │                 └──────────────┘
            │
            └─── Cache MISS ──┐
                              │
       ┌──────────────────────▼─────────┐
       │  Query PostgreSQL              │
       │  Store in Layer 3 cache        │
       └────┬───────────────────────────┘
            │
       ┌────▼──────────────────┐
       │  Perform RAG          │
       │  Generate Answer      │
       └────┬──────────────────┘
            │
       ┌────▼──────────────────┐
       │  Store in Layer 1     │
       │  Return to User       │
       └───────────────────────┘

Cache Statistics:
┌────────────────────────────────┐
│  Cache Hit Rates:              │
│  • Layer 1 (Queries): 60%      │
│  • Layer 2 (Embeddings): 80%   │
│  • Layer 3 (Documents): 70%    │
│                                │
│  Result: 70% faster responses  │
│  90% reduction in OpenAI calls │
└────────────────────────────────┘
```

**Eviction Policy:** LRU (Least Recently Used)
**Memory Limit:** 2GB per layer

---

### Phase 2.7: Complete Project 2 Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        Clients                             │
└────────────────────────┬───────────────────────────────────┘
                         │
            ┌────────────▼─────────────┐
            │  Load Balancer (nginx)   │
            └───┬──────────────┬───────┘
                │              │
       ┌────────┴──┐      ┌────┴───────┐
       │           │      │            │
  ┌────▼────┐  ┌──▼──────┐  ┌─────────▼──┐
  │ API #1  │  │ API #2  │  │  API #3    │
  │         │  │         │  │            │
  │ Routes: │  │         │  │            │
  │ • Upload│  │         │  │            │
  │ • Query │  │         │  │            │
  │ • RAG   │  │         │  │            │
  └────┬────┘  └────┬────┘  └──────┬─────┘
       │            │              │
       └────────────┼──────────────┘
                    │
    ┌───────────────┼────────────────┬──────────────┐
    │               │                │              │
┌───▼───────┐  ┌────▼─────┐  ┌──────▼──────┐  ┌───▼─────┐
│PostgreSQL │  │  Redis   │  │   MinIO S3  │  │ OpenAI  │
│+ pgvector │  │          │  │             │  │   API   │
│           │  │ Caches:  │  │  Raw Files  │  │         │
│ Tables:   │  │ • Query  │  │  Storage    │  │ • GPT-4 │
│ • docs    │  │   5m TTL │  │             │  │ • Embed │
│ • chunks  │  │ • Embed  │  │ Buckets:    │  │   API   │
│ • users   │  │   1h TTL │  │ /documents  │  │         │
│           │  │ • Doc    │  │ /temp       │  └─────────┘
│ Vectors:  │  │  15m TTL │  └─────────────┘
│ • 1536d   │  │          │
│ • HNSW    │  │ Queue:   │
│   index   │  │ • Tasks  │
└───────────┘  └────┬─────┘
                    │
          ┌─────────┴─────────┬─────────────┐
          │                   │             │
     ┌────▼─────┐      ┌──────▼────┐  ┌────▼─────┐
     │Worker 1  │      │ Worker 2  │  │Worker 3  │
     │          │      │           │  │          │
     │Pipeline: │      │           │  │          │
     │1. Extract│      │           │  │          │
     │2. Chunk  │      │           │  │          │
     │3. Embed  │      │           │  │          │
     │4. Store  │      │           │  │          │
     └──────────┘      └───────────┘  └──────────┘

┌─────────────────────────────────────────────────────┐
│              RAG System Complete                    │
│                                                     │
│ ✓ Document upload & storage (MinIO)                │
│ ✓ Text extraction pipeline (PDF/DOCX/TXT)          │
│ ✓ Vector embeddings (OpenAI, 1536d)                │
│ ✓ Semantic search (pgvector, HNSW)                 │
│ ✓ RAG query system (GPT-4)                         │
│ ✓ Background processing (Redis Queue, 3 workers)   │
│ ✓ Multi-layer caching (Query/Embed/Doc)            │
│ ✓ 80%+ test coverage                               │
└─────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────┐
│                    Client Request                    │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              Query Classifier                        │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐           │
│  │ Simple  │  │ Moderate │  │ Complex │           │
│  └─────────┘  └──────────┘  └─────────┘           │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              Cache Service (L1 - Redis)             │
│                                                      │
│  ┌────────────────┐                                │
│  │  Cache Check   │                                │
│  └────────┬───────┘                                │
│           │                                         │
│    ┌──────┴──────┐                                │
│    │             │                                 │
│  HIT ✅        MISS ❌                             │
│    │             │                                 │
│    │             ▼                                 │
│    │   ┌─────────────────┐                        │
│    │   │  Embedding      │                        │
│    │   │  Cache (L2)     │                        │
│    │   └────────┬────────┘                        │
│    │            │                                  │
│    │      ┌─────┴──────┐                          │
│    │      │            │                          │
│    │    HIT ✅       MISS ❌                       │
│    │      │            │                          │
│    │      │            ▼                          │
│    │      │   ┌─────────────────┐                │
│    │      │   │ Vector Search   │                │
│    │      │   │  (Qdrant)       │                │
│    │      │   └────────┬────────┘                │
│    │      │            │                          │
│    │      │            ▼                          │
│    │      │   ┌─────────────────┐                │
│    │      │   │  Score Filter   │                │
│    │      │   │  (min_score)    │                │
│    │      │   └────────┬────────┘                │
│    │      │            │                          │
│    │      │            ▼                          │
│    │      │   ┌─────────────────┐                │
│    │      │   │  LLM Generate   │                │
│    │      │   │  (Smart Model)  │                │
│    │      │   └────────┬────────┘                │
│    │      │            │                          │
│    │      │            ▼                          │
│    │      │   ┌─────────────────┐                │
│    │      │   │  Cache Response │                │
│    │      │   └────────┬────────┘                │
│    │      │            │                          │
│    └──────┴────────────┘                          │
│           │                                        │
│           ▼                                        │
│  ┌─────────────────┐                              │
│  │  Track Metrics  │                              │
│  └─────────────────┘                              │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                  Response to Client                  │
└─────────────────────────────────────────────────────┘
```

---

## Project 3: Agentic AI Platform

### Phase 3.1: AI Agents with LangGraph

```
┌─────────────────────────────────────────────────────────┐
│              LangGraph Agent Architecture               │
└─────────────────────────────────────────────────────────┘

┌──────────────┐
│  User Query  │
│ "Find docs   │
│  about AI    │
│  and         │
│  summarize"  │
└──────┬───────┘
       │
  ┌────▼────────────────┐
  │ Agent Orchestrator  │
  └────┬────────────────┘
       │
  ┌────▼─────────────────────────────────────────────┐
  │         LangGraph State Machine                  │
  │                                                  │
  │   ┌──────────┐                                  │
  │   │  START   │                                  │
  │   └────┬─────┘                                  │
  │        │                                        │
  │   ┌────▼────────┐                              │
  │   │  PLANNING   │                              │
  │   │             │                              │
  │   │ • Analyze   │                              │
  │   │   query     │                              │
  │   │ • Select    │                              │
  │   │   tools     │                              │
  │   └────┬────────┘                              │
  │        │                                        │
  │   ┌────▼────────┐     ┌──────────────┐        │
  │   │ EXECUTION   │────►│  Tool Call   │        │
  │   │             │     └───┬──────────┘        │
  │   │ • Run tools │         │                   │
  │   │ • Gather    │    ┌────▼──────────────┐   │
  │   │   results   │    │ Available Tools:  │   │
  │   └────┬────────┘    │                   │   │
  │        │             │ • search_docs     │   │
  │   ┌────▼────────┐    │ • summarize_doc   │   │
  │   │ REASONING   │    │ • extract_entities│   │
  │   │             │    │ • compare_docs    │   │
  │   │ • OpenAI    │    │ • query_database  │   │
  │   │   GPT-4     │    └───────────────────┘   │
  │   │ • Evaluate  │                            │
  │   │   results   │                            │
  │   └────┬────────┘                            │
  │        │                                      │
  │   ┌────▼────────┐                            │
  │   │  DECISION   │                            │
  │   │             │                            │
  │   │ Need more   │                            │
  │   │ info? ──────┼───Yes──► Back to EXECUTION│
  │   │             │                            │
  │   │ Complete? ──┼───Yes──► RESPONSE          │
  │   └─────────────┘                            │
  │                                               │
  │   ┌─────────────┐                            │
  │   │  RESPONSE   │                            │
  │   │             │                            │
  │   │ • Format    │                            │
  │   │ • Add       │                            │
  │   │   sources   │                            │
  │   └────┬────────┘                            │
  │        │                                      │
  │   ┌────▼─────┐                               │
  │   │   END    │                               │
  │   └──────────┘                               │
  └──────────────────────────────────────────────┘
       │
  ┌────▼───────────────┐
  │ Conversation       │
  │ Memory             │
  │ (PostgreSQL)       │
  │                    │
  │ • Chat history     │
  │ • Agent state      │
  │ • Tool results     │
  └────────────────────┘

Example Execution:
┌──────────────────────────────────────────────────┐
│ Turn 1:                                          │
│  User: "Find docs about AI and summarize"       │
│  Agent: [search_docs("AI")] → 5 results         │
│         [summarize_doc(doc_1)] → summary_1      │
│         [summarize_doc(doc_2)] → summary_2      │
│  Response: "Found 5 documents. Here are         │
│             summaries of the top 2..."          │
│                                                  │
│ Turn 2:                                          │
│  User: "Compare the first two"                  │
│  Agent: [compare_docs(doc_1, doc_2)]            │
│  Response: "Doc 1 focuses on... while Doc 2..." │
└──────────────────────────────────────────────────┘
```

---

### Phase 3.2: Event Streaming with Redpanda

```
┌──────────────────────────────────────────────────────────┐
│              Event-Driven Architecture                   │
└──────────────────────────────────────────────────────────┘

Publishers:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ API Service │     │   Workers   │     │   Agents    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                    │
       │ document.uploaded │ document.processed │ agent.action
       │                   │                    │
       └───────────────────┴────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Redpanda Cluster      │
              │   (Kafka-compatible)    │
              │                         │
              │   Topics:               │
              │   ┌──────────────────┐  │
              │   │ documents        │  │ ← Partitioned by doc_id
              │   │ • uploaded       │  │
              │   │ • processed      │  │
              │   │ • deleted        │  │
              │   └──────────────────┘  │
              │   ┌──────────────────┐  │
              │   │ queries          │  │ ← Partitioned by user_id
              │   │ • started        │  │
              │   │ • completed      │  │
              │   │ • failed         │  │
              │   └──────────────────┘  │
              │   ┌──────────────────┐  │
              │   │ agents           │  │ ← Partitioned by session_id
              │   │ • tool_called    │  │
              │   │ • response_gen   │  │
              │   └──────────────────┘  │
              └────────┬────────────────┘
                       │
       ┌───────────────┼───────────────┬──────────────┐
       │               │               │              │
  ┌────▼────────┐ ┌───▼──────────┐ ┌──▼─────────┐ ┌─▼──────────┐
  │  Indexer    │ │  Notifier    │ │ Analytics  │ │  Triggers  │
  │  Consumer   │ │  Consumer    │ │  Consumer  │ │  Consumer  │
  │             │ │              │ │            │ │            │
  │ Updates     │ │ Sends user   │ │ Tracks     │ │ Detects    │
  │ search      │ │ notifications│ │ metrics    │ │ patterns   │
  │ index       │ │              │ │            │ │            │
  └─────────────┘ └──────────────┘ └────────────┘ └────────────┘

Event Schema Example:
┌──────────────────────────────────────────────────┐
│ Event: document.uploaded                         │
│ {                                                │
│   "event_id": "evt_123456789",                   │
│   "event_type": "document.uploaded",             │
│   "timestamp": "2024-01-23T10:30:00Z",           │
│   "data": {                                      │
│     "document_id": "doc_987654321",              │
│     "user_id": "user_12345",                     │
│     "filename": "report.pdf",                    │
│     "size_bytes": 5242880,                       │
│     "mime_type": "application/pdf"               │
│   },                                             │
│   "metadata": {                                  │
│     "source": "api",                             │
│     "version": "1.0"                             │
│   }                                              │
│ }                                                │
└──────────────────────────────────────────────────┘

Benefits:
┌────────────────────────────────────┐
│ ✓ Loose coupling between services │
│ ✓ Scalable (horizontal)           │
│ ✓ Event replay capability         │
│ ✓ Exactly-once delivery           │
│ ✓ Ordered within partition        │
└────────────────────────────────────┘
```

---

### Phase 3.3: Intelligent Triggers

```
┌──────────────────────────────────────────────────────────┐
│           Intelligent Trigger System                     │
└──────────────────────────────────────────────────────────┘

┌────────────────┐
│  Event Stream  │
│  (Redpanda)    │
└────────┬───────┘
         │ Consume events
         │
    ┌────▼─────────────────┐
    │  Trigger Service     │
    │  (Event Processor)   │
    └────┬─────────────┬───┘
         │             │
    ┌────▼───────┐ ┌──▼──────────┐
    │   Trend    │ │  Anomaly    │
    │  Detector  │ │  Detector   │
    └────┬───────┘ └──┬──────────┘
         │            │
         │            │

┌────────▼────────────────────────────────────────────┐
│          TREND DETECTION                            │
│                                                     │
│  Track: Topic mentions over time                   │
│  ┌────────────────────────────────────────┐        │
│  │ Time Window: 7 days                    │        │
│  │ Topic: "AI Safety"                     │        │
│  │                                         │        │
│  │ Day 1: 2 mentions                       │        │
│  │ Day 2: 3 mentions                       │        │
│  │ Day 3: 5 mentions ◄── Threshold (5+)   │        │
│  │ Day 4: 7 mentions                       │        │
│  │                                         │        │
│  │ Trigger: trend.detected                │        │
│  └────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
         │
         │
┌────────▼────────────────────────────────────────────┐
│          ANOMALY DETECTION                          │
│                                                     │
│  1. Slow Queries:                                  │
│     ┌──────────────────────────────┐              │
│     │ Query duration: 7.2s         │              │
│     │ Threshold: 5s                │              │
│     │ → Trigger: anomaly.detected  │              │
│     └──────────────────────────────┘              │
│                                                     │
│  2. Failed Uploads:                                │
│     ┌──────────────────────────────┐              │
│     │ Upload failed 3 times        │              │
│     │ → Trigger: anomaly.detected  │              │
│     └──────────────────────────────┘              │
│                                                     │
│  3. Inactive Users:                                │
│     ┌──────────────────────────────┐              │
│     │ No activity for 30 days      │              │
│     │ → Trigger: engagement.needed │              │
│     └──────────────────────────────┘              │
└─────────────────────────────────────────────────────┘
         │
         │ Publish trigger events
         │
    ┌────▼──────────────┐
    │  Action Service   │
    └────┬──────────────┘
         │
    ┌────┴──────┬──────────┬───────────┐
    │           │          │           │
┌───▼─────┐ ┌──▼─────┐ ┌──▼──────┐ ┌──▼──────┐
│Webhook  │ │ Email  │ │ In-App  │ │  Slack  │
│Delivery │ │Service │ │ Notif   │ │  Alert  │
└─────────┘ └────────┘ └─────────┘ └─────────┘

Example Notifications:
┌──────────────────────────────────────────────────┐
│ Trend Detected:                                  │
│ "AI Safety" is trending (7 mentions this week)   │
│ Would you like to create a summary report?       │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ Anomaly Alert:                                   │
│ Query performance degraded (avg 6.5s)            │
│ Affected queries: 23 in last hour                │
│ Action: Database optimization recommended        │
└──────────────────────────────────────────────────┘
```

---

### Phase 3.4: Real-Time Chat with WebSockets

```
┌──────────────────────────────────────────────────────────┐
│              WebSocket Chat Architecture                 │
└──────────────────────────────────────────────────────────┘

Connection Flow:

┌─────────────┐
│ Web Client  │
└──────┬──────┘
       │ ws://api.example.com/ws/chat/{conversation_id}
       │ Headers: Authorization: Bearer {jwt_token}
       │
  ┌────▼────────────────┐
  │ WebSocket Server    │
  │                     │
  │ 1. Validate JWT     │
  │ 2. Check permission │
  │ 3. Establish conn   │
  └────┬────────────────┘
       │
  ┌────▼──────────────────────┐
  │  Connection Manager       │
  │                           │
  │  Active Connections:      │
  │  ┌─────────────────────┐  │
  │  │ user_123:           │  │
  │  │  • conn_1 (browser) │  │
  │  │  • conn_2 (mobile)  │  │
  │  │  • conn_3 (desktop) │  │
  │  └─────────────────────┘  │
  └────┬──────────────────────┘
       │ Store in Redis
       │
  ┌────▼──────────┐
  │  Redis        │
  │               │
  │  Key: ws:     │
  │    user_123   │
  │  Value: [     │
  │    conn_1,    │
  │    conn_2,    │
  │    conn_3     │
  │  ]            │
  └───────────────┘

Message Flow:

┌─────────────┐
│   Client    │
│  Device 1   │
└──────┬──────┘
       │ Send: "What is the revenue?"
       │
  ┌────▼──────────────────┐
  │ Message Handler       │
  │                       │
  │ 1. Validate message   │
  │ 2. Save to DB         │
  └────┬──────────────────┘
       │
  ┌────▼──────────────────┐
  │  PostgreSQL           │
  │                       │
  │  messages:            │
  │  ┌────────────────┐   │
  │  │conversation_id │   │
  │  │user_id         │   │
  │  │content         │   │
  │  │role: "user"    │   │
  │  │timestamp       │   │
  │  └────────────────┘   │
  └────┬──────────────────┘
       │
  ┌────▼──────────────────┐
  │  Route to Agent       │
  └────┬──────────────────┘
       │
  ┌────▼──────────────────┐
  │  AI Agent Service     │
  │  (LangGraph)          │
  └────┬──────────────────┘
       │
  ┌────▼──────────────────┐
  │  OpenAI API           │
  │  (GPT-4 Streaming)    │
  └────┬──────────────────┘
       │ Stream tokens: "The revenue..."
       │
  ┌────▼──────────────────────────────────┐
  │  Broadcast to All User Connections    │
  └────┬────────────────┬─────────────────┘
       │                │
  ┌────▼────────┐  ┌────▼────────┐  ┌─────▼──────┐
  │  Device 1   │  │  Device 2   │  │  Device 3  │
  │  (Browser)  │  │  (Mobile)   │  │  (Desktop) │
  │             │  │             │  │            │
  │  Displays   │  │  Displays   │  │  Displays  │
  │  streaming  │  │  streaming  │  │  streaming │
  │  response   │  │  response   │  │  response  │
  └─────────────┘  └─────────────┘  └────────────┘

Features:

┌────────────────────────────────────────────┐
│ ✓ Multi-device sync                        │
│ ✓ Streaming responses (token by token)    │
│ ✓ Typing indicators                        │
│ ✓ Read receipts                            │
│ ✓ Conversation history                     │
│ ✓ Reconnection handling                    │
│ ✓ Presence tracking (online/offline)      │
└────────────────────────────────────────────┘

Connection States:
┌──────────────────────────────────────┐
│ • connecting → connected             │
│ • connected → disconnected           │
│ • disconnected → reconnecting        │
│ • reconnecting → connected           │
└──────────────────────────────────────┘
```

---

### Phase 3.5: Consistent Hashing

```
┌──────────────────────────────────────────────────────────┐
│            Consistent Hash Ring                          │
└──────────────────────────────────────────────────────────┘

Hash Ring (0-359):

              0/360
                │
        315 ────┼──── 45
                │
    270 ────────┼────────90
                │
        225 ────┼──── 135
                │
              180

Physical Nodes:
┌──────────────────────────────────────────────────┐
│ • Node 1: Hash(node1) % 360 = 120               │
│ • Node 2: Hash(node2) % 360 = 240               │
│ • Node 3: Hash(node3) % 360 = 0                 │
└──────────────────────────────────────────────────┘

Virtual Nodes (Replicas):
┌──────────────────────────────────────────────────┐
│ Each physical node → 150 virtual nodes           │
│ • node1_replica_0 → position 10                  │
│ • node1_replica_1 → position 25                  │
│ • node1_replica_2 → position 47                  │
│ • ... (147 more)                                 │
│                                                  │
│ Total ring positions: 450 (3 × 150)             │
└──────────────────────────────────────────────────┘

Request Routing:

┌──────────────┐
│   Request    │
│  user_id:    │
│   "user_456" │
└──────┬───────┘
       │
  ┌────▼──────────────────┐
  │  Hash Function        │
  │                       │
  │  hash("user_456")     │
  │    % 360 = 175        │
  └────┬──────────────────┘
       │
  ┌────▼──────────────────────────┐
  │  Find Next Node Clockwise     │
  │                               │
  │  Position 175:                │
  │  → Next: 180 (Node 2 replica) │
  │  → Route to Node 2            │
  └────┬──────────────────────────┘
       │
  ┌────▼──────────┐
  │  API Node 2   │
  │               │
  │  Handle       │
  │  request      │
  └───────────────┘

Data Sharding:

┌────────────────────────────────────────────────┐
│  PostgreSQL Sharding                           │
│                                                │
│  documents table:                              │
│  ┌──────────────────────────────────────┐     │
│  │ id          │ user_id  │ shard_id    │     │
│  │ 123         │ user_456 │ shard_2     │     │
│  │ 124         │ user_789 │ shard_1     │     │
│  └──────────────────────────────────────┘     │
│                                                │
│  Query routing:                                │
│  1. Hash user_id → determine shard            │
│  2. Query only that shard                     │
│  3. Faster queries, better distribution       │
└────────────────────────────────────────────────┘

Adding New Node:

Before (3 nodes):
┌────────────────────────────────────────┐
│ Node 1: 33% load                       │
│ Node 2: 33% load                       │
│ Node 3: 33% load                       │
└────────────────────────────────────────┘

After (4 nodes):
┌────────────────────────────────────────┐
│ Node 1: 25% load  (↓ 8%)              │
│ Node 2: 25% load  (↓ 8%)              │
│ Node 3: 25% load  (↓ 8%)              │
│ Node 4: 25% load  (new)                │
│                                        │
│ Keys moved: ~25% (only to Node 4)      │
│ Keys NOT moved: ~75%                   │
└────────────────────────────────────────┘

Benefits:
┌─────────────────────────────────────┐
│ ✓ Even load distribution            │
│ ✓ Minimal rebalancing (<30% keys)   │
│ ✓ Sticky sessions (same user → same │
│   server)                            │
│ ✓ Horizontal scaling                │
└─────────────────────────────────────┘
```

---

### Phase 3.6: Horizontal Scaling

```
┌──────────────────────────────────────────────────────────┐
│              Horizontally Scaled Architecture            │
└──────────────────────────────────────────────────────────┘

┌─────────────────────────────┐
│  Internet / Clients (1000+) │
└─────────────┬───────────────┘
              │
     ┌────────▼─────────┐
     │  Nginx LB        │
     │                  │
     │  Algorithm:      │
     │  • Least Conn    │
     │  • Health Check  │
     │  • Sticky (WS)   │
     └────┬──────┬──────┘
          │      │
    ┌─────┴──┬───┴──┬──────┐
    │        │      │      │
┌───▼───┐ ┌──▼──┐ ┌▼───┐ ┌▼───────┐
│API #1 │ │API 2│ │#3  │ │  #N    │
│       │ │     │ │    │ │  (Auto │
│20 conn│ │25 c │ │22 c│ │  Scale)│
└───┬───┘ └──┬──┘ └┬───┘ └┬───────┘
    │        │     │      │
    └────────┴─────┴──────┘
             │
    ┌────────┴────────────────────┐
    │                             │
┌───▼──────────┐         ┌────────▼──────┐
│   Shared     │         │   Shared      │
│   State      │         │   Data        │
│              │         │               │
│ ┌──────────┐ │         │ ┌───────────┐ │
│ │  Redis   │ │         │ │PostgreSQL │ │
│ │          │ │         │ │  (Master) │ │
│ │Sessions: │ │         │ │           │ │
│ │ user_123 │ │         │ │ ┌───────┐ │ │
│ │  ↳ data  │ │         │ │ │Replica│ │ │
│ │          │ │         │ │ │ (RO)  │ │ │
│ │Rate      │ │         │ │ └───────┘ │ │
│ │Limits:   │ │         │ └───────────┘ │
│ │ api_key  │ │         │               │
│ │  ↳ tokens│ │         │               │
│ │          │ │         │               │
│ │Cache:    │ │         │               │
│ │ query_x  │ │         │               │
│ │  ↳ result│ │         │               │
│ └──────────┘ │         │               │
└──────────────┘         └───────────────┘

Stateless API Design:

┌────────────────────────────────────────────┐
│  No Local State                            │
│  ┌──────────────────────────────────────┐  │
│  │ ✓ JWT tokens (no server sessions)   │  │
│  │ ✓ Redis for rate limits             │  │
│  │ ✓ Redis for cache                   │  │
│  │ ✓ Database for persistent data      │  │
│  │ ✓ Idempotent operations             │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘

Health Checks:

┌──────────────────────────────────────┐
│  Nginx Health Check                  │
│                                      │
│  Every 5 seconds:                    │
│  GET /health                         │
│                                      │
│  Expected: 200 OK                    │
│  If fail × 3: Remove from pool       │
│  If success after removal: Re-add    │
└──────────────────────────────────────┘

Graceful Shutdown:

┌────────────────────────────────────────┐
│  1. Receive SIGTERM                    │
│  2. Stop accepting new requests        │
│  3. Finish processing active requests  │
│  4. Close connections (max 30s)        │
│  5. Exit                               │
└────────────────────────────────────────┘

WebSocket Sticky Sessions:

┌─────────────────────────────────────────┐
│  User connects:                         │
│  1. Hash user_id                        │
│  2. Route to specific instance          │
│  3. All messages → same instance        │
│  4. Maintains connection state          │
└─────────────────────────────────────────┘

Load Test Results:
┌──────────────────────────────────────┐
│ • 1000 concurrent users: ✓           │
│ • Avg response time: 85ms            │
│ • p95 response time: 200ms           │
│ • Error rate: 0.01%                  │
│ • CPU per instance: 45%              │
│ • Can kill 1 instance: ✓ (failover)  │
└──────────────────────────────────────┘
```

---

### Phase 3.7: Observability - Prometheus + Grafana

```
┌──────────────────────────────────────────────────────────┐
│              Observability Stack                         │
└──────────────────────────────────────────────────────────┘

Application Layer:
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  API #1     │  │  API #2     │  │  Workers    │
│             │  │             │  │             │
│ /metrics    │  │ /metrics    │  │ /metrics    │
│  endpoint   │  │  endpoint   │  │  endpoint   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       │  Expose metrics (Prometheus format)
       │                │                │
       └────────────────┴────────────────┘
                        │
              ┌─────────▼─────────┐
              │   Prometheus      │
              │   Server          │
              │                   │
              │   Scrape every    │
              │   15 seconds      │
              │                   │
              │   Store:          │
              │   • Time series   │
              │   • 15 day        │
              │     retention     │
              └────────┬──────────┘
                       │
                       │ Query API
                       │
              ┌────────▼──────────┐
              │    Grafana        │
              │    Dashboard      │
              └───────────────────┘

Metrics Exposed:

┌──────────────────────────────────────────────────────┐
│  API Metrics:                                        │
│  • http_requests_total{method, path, status}         │
│  • http_request_duration_seconds{path}               │
│  • http_requests_in_progress{path}                   │
│                                                      │
│  Business Metrics:                                   │
│  • documents_uploaded_total                          │
│  • queries_completed_total                           │
│  • rag_responses_generated_total                     │
│  • agent_tool_calls_total{tool}                      │
│                                                      │
│  System Metrics:                                     │
│  • process_cpu_percent                               │
│  • process_memory_bytes                              │
│  • process_open_fds                                  │
│                                                      │
│  Queue Metrics:                                      │
│  • queue_depth{queue_name}                           │
│  • queue_processing_duration_seconds                 │
│  • queue_failed_jobs_total                           │
└──────────────────────────────────────────────────────┘

Grafana Dashboards:

┌──────────────────────────────────────────────────────┐
│  Dashboard 1: API Performance                        │
│  ┌────────────────────────────────────────────────┐  │
│  │ Request Rate:         2,500 req/min          │  │
│  │ Error Rate:           0.05%                   │  │
│  │ Response Time (p95):  180ms                   │  │
│  │ Response Time (p99):  450ms                   │  │
│  │                                               │  │
│  │ [Graph: Requests over time]                   │  │
│  │ [Graph: Error rate over time]                 │  │
│  │ [Graph: Response time percentiles]            │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Dashboard 2: RAG Performance                        │
│  ┌────────────────────────────────────────────────┐  │
│  │ Embeddings Generated: 12,450 today            │  │
│  │ Vector Searches:      5,230 today             │  │
│  │ RAG Queries:          1,850 today             │  │
│  │ Avg Generation Time:  2.3s                    │  │
│  │                                               │  │
│  │ [Graph: Search latency]                       │  │
│  │ [Graph: Cache hit rate]                       │  │
│  │ [Graph: OpenAI API latency]                   │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Dashboard 3: System Resources                       │
│  ┌────────────────────────────────────────────────┐  │
│  │ CPU Usage:     45% (avg across 3 instances)   │  │
│  │ Memory Usage:  62% (4.8GB / 8GB)              │  │
│  │ Open FDs:      250 / 1024                     │  │
│  │ Queue Depth:   23 pending jobs                │  │
│  │                                               │  │
│  │ [Graph: CPU per instance]                     │  │
│  │ [Graph: Memory per instance]                  │  │
│  │ [Graph: Queue depth over time]                │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘

Alert Rules:

┌──────────────────────────────────────────────────────┐
│  Alert: HighErrorRate                                │
│  Condition: error_rate > 5% for 5 minutes            │
│  Severity: critical                                  │
│  Action: Send to PagerDuty + Slack                   │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Alert: SlowResponseTime                             │
│  Condition: p95_latency > 1s for 10 minutes          │
│  Severity: warning                                   │
│  Action: Send to Slack                               │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Alert: HighCPUUsage                                 │
│  Condition: cpu_percent > 80% for 15 minutes         │
│  Severity: warning                                   │
│  Action: Auto-scale + Send to Slack                  │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Alert: NoDocumentUploads                            │
│  Condition: uploads_total increase = 0 for 24h       │
│  Severity: info                                      │
│  Action: Send email to ops team                      │
└──────────────────────────────────────────────────────┘
```

---

### Phase 3.8: Complete Production Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       PRODUCTION SYSTEM                          │
│            Intelligent Document Analyst Platform                 │
└──────────────────────────────────────────────────────────────────┘

                        Internet
                           │
                    ┌──────▼──────┐
                    │   Route 53  │  DNS
                    │     DNS     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ CloudFront  │  CDN
                    │     CDN     │  (Static Assets)
                    └──────┬──────┘
                           │
                           │
┌────────────────────────EDGE LAYER───────────────────────────┐
│                   ┌─────▼────────┐                          │
│                   │ Nginx LB     │                          │
│                   │ • SSL Term   │                          │
│                   │ • Rate Limit │                          │
│                   │ • Health Chk │                          │
│                   └───┬──────────┘                          │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌────────────────────API LAYER (Auto-Scaling)─────────────────┐
│         ┌───────────┴──────────┬────────────┐              │
│         │                      │            │              │
│    ┌────▼────┐  ┌─────────┐ ┌─▼────────┐ ┌─▼──────┐      │
│    │ API #1  │  │  API #2 │ │  API #3  │ │ API #N │      │
│    │         │  │         │ │          │ │  (ECS) │      │
│    │ FastAPI │  │ FastAPI │ │ FastAPI  │ │        │      │
│    └────┬────┘  └────┬────┘ └────┬─────┘ └────┬───┘      │
└─────────┼────────────┼──────────┼──────────────┼──────────┘
          │            │          │              │
          └────────────┴──────────┴──────────────┘
                       │
┌──────────────────AGENT LAYER────────────────────────────────┐
│              ┌─────▼──────┬──────────┐                      │
│              │            │          │                      │
│         ┌────▼────┐  ┌────▼────┐ ┌──▼─────┐               │
│         │Agent #1 │  │Agent #2 │ │Agent #N│               │
│         │         │  │         │ │  (ECS) │               │
│         │LangGraph│  │LangGraph│ │        │               │
│         └────┬────┘  └────┬────┘ └────┬───┘               │
└──────────────┼────────────┼──────────┼─────────────────────┘
               │            │          │
               └────────────┴──────────┘
                            │
┌──────────────────WORKER LAYER───────────────────────────────┐
│              ┌─────────────┴──────────┬──────────┐          │
│              │                        │          │          │
│         ┌────▼────┐  ┌────────┐  ┌───▼─────┐ ┌─▼──────┐   │
│         │Worker #1│  │Worker 2│  │Worker 3 │ │Worker N│   │
│         │         │  │        │  │         │ │  (ECS) │   │
│         │RAG Tasks│  │Extract │  │Embedding│ │        │   │
│         └────┬────┘  └───┬────┘  └────┬────┘ └────┬───┘   │
└──────────────┼───────────┼────────────┼───────────┼────────┘
               │           │            │           │
               └───────────┴────────────┴───────────┘
                            │
┌─────────────────EVENT STREAMING─────────────────────────────┐
│                    ┌─────▼──────┐                           │
│                    │  Redpanda  │                           │
│                    │  Cluster   │                           │
│                    │  3 Brokers │                           │
│                    └─────┬──────┘                           │
│                          │                                  │
│                    ┌─────▼──────┐                           │
│                    │  Triggers  │                           │
│                    │  Service   │                           │
│                    └────────────┘                           │
└──────────────────────────────────────────────────────────────┘
                            │
┌──────────────────DATA LAYER─────────────────────────────────┐
│     ┌─────────┬─────────────┬────────────┬─────────────┐   │
│     │         │             │            │             │   │
│ ┌───▼────┐ ┌─▼────────┐ ┌──▼─────┐  ┌───▼────────┐ ┌─▼───┐│
│ │RDS PG  │ │ElastiCache│ │  S3    │  │  Backup   │ │Logs ││
│ │+pgvector│ │  Redis   │ │ MinIO  │  │  S3       │ │ CW  ││
│ │        │ │          │ │        │  │           │ │     ││
│ │Multi-AZ│ │Cluster   │ │Raw Docs│  │Daily Snap │ │JSON ││
│ │Read Rep│ │Sharded   │ │        │  │           │ │     ││
│ └────────┘ └──────────┘ └────────┘  └───────────┘ └─────┘│
└──────────────────────────────────────────────────────────────┘
                            │
┌─────────────────EXTERNAL SERVICES───────────────────────────┐
│                     ┌──────▼──────┐                         │
│                     │  OpenAI API │                         │
│                     │  GPT-4 +    │                         │
│                     │  Embeddings │                         │
│                     └─────────────┘                         │
└──────────────────────────────────────────────────────────────┘
                            │
┌─────────────────OBSERVABILITY───────────────────────────────┐
│      ┌──────────────────┴──────────────┬─────────────┐     │
│      │                                 │             │     │
│ ┌────▼────────┐  ┌──────────────┐  ┌──▼─────────┐ ┌──▼───┐│
│ │ Prometheus  │  │   Grafana    │  │CloudWatch │ │X-Ray ││
│ │             │  │              │  │  Logs     │ │Trace ││
│ │ Metrics     │  │ 5 Dashboards │  │  Alarms   │ │      ││
│ │ Collector   │  │ 12 Alerts    │  │           │ │      ││
│ └─────────────┘  └──────────────┘  └───────────┘ └──────┘│
└──────────────────────────────────────────────────────────────┘
                            │
┌──────────────────CI/CD PIPELINE─────────────────────────────┐
│   ┌────────┐    ┌────────┐    ┌───────┐    ┌──────────┐   │
│   │ GitHub │───►│ Actions│───►│  ECR  │───►│   ECS    │   │
│   │  Repo  │    │  CI/CD │    │Docker │    │  Deploy  │   │
│   │        │    │        │    │Registry    │          │   │
│   │ • Test │    │ • Build│    │ • Tag  │    │• Rolling │   │
│   │ • Lint │    │ • Push │    │        │    │• Blue/Grn│   │
│   └────────┘    └────────┘    └───────┘    └──────────┘   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────SYSTEM STATS───────────────────────────────┐
│ • API Instances:        3-10 (auto-scaling)                 │
│ • Requests/sec:         1,000+                              │
│ • Avg Response:         85ms                                │
│ • P95 Response:         200ms                               │
│ • Uptime:               99.9%                               │
│ • Documents Stored:     100,000+                            │
│ • Vector Embeddings:    5M+                                 │
│ • Daily Queries:        50,000+                             │
│ • Agent Conversations:  10,000+                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────FEATURES COMPLETE──────────────────────────┐
│ ✓ RESTful API with 15+ endpoints                            │
│ ✓ JWT authentication + refresh tokens                       │
│ ✓ Rate limiting (Token Bucket)                              │
│ ✓ Snowflake ID generation                                   │
│ ✓ URL shortener with analytics                              │
│ ✓ Multi-channel notifications                               │
│ ✓ Document upload & storage (S3)                            │
│ ✓ RAG system (embeddings + vector search)                   │
│ ✓ Background processing (Redis Queue)                       │
│ ✓ Multi-layer caching                                       │
│ ✓ AI Agents (LangGraph + tool use)                          │
│ ✓ Event streaming (Redpanda)                                │
│ ✓ Intelligent triggers                                      │
│ ✓ Real-time chat (WebSockets)                               │
│ ✓ Consistent hashing                                        │
│ ✓ Horizontal scaling (3+ instances)                         │
│ ✓ Observability (Prometheus + Grafana)                      │
│ ✓ CI/CD pipeline (GitHub Actions → ECS)                     │
│ ✓ 80%+ test coverage                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Summary

**15 System Design Patterns Implemented:**
1. Layered Architecture (N-Tier)
2. Pipes & Filters (Text Processing)
3. Event-Driven (Redpanda Streaming)
4. Token Bucket (Rate Limiting)
5. Snowflake (Distributed IDs)
6. Base62 (URL Shortening)
7. RAG (Retrieval Augmented Generation)
8. Vector Search (Semantic Similarity)
9. Multi-Layer Cache (Performance)
10. Background Jobs (Async Processing)
11. AI Agents (LangGraph State Machines)
12. Pub/Sub (Event Streaming)
13. Consistent Hashing (Load Distribution)
14. Horizontal Scaling (Multiple Instances)
15. Observability (Metrics & Monitoring)

**Tech Stack:**
- Backend: FastAPI, Python async
- Databases: PostgreSQL + pgvector, Redis
- Storage: MinIO S3
- AI: OpenAI GPT-4, Embeddings, LangGraph
- Events: Redpanda (Kafka)
- Infra: Docker, nginx, Prometheus, Grafana
- Cloud: AWS ECS, RDS, ElastiCache, S3
- CI/CD: GitHub Actions

**Architecture Style:** ASCII Box-Drawing Diagrams
