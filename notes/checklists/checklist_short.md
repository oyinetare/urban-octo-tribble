# Intelligent Document Analyst - Simple Checklist Progress Tracker for All 3 Projects

---

## 📋 Table of Contents

- [Project 1: RESTful API Foundation](#project-1-restful-api-foundation)
    - [1.1: Foundation](#phase-11-foundation)
    - [1.2: Authentication & Security](#phase-12-authentication--security)
    - [1.3: Rate Limiting](#phase-13-rate-limiting)
    - [1.4: Unique ID Generation](#phase-14-unique-id-generation)
    - [1.5: URL Shortener](#phase-15-url-shortener)
    - [1.6: Notifications](#phase-16-notification-system)
    - [1.7: Idempotency, URI Versioning, Pagination, Filtering & Sorting](#phase-17-idempotency-uri-versioning-pagination-filtering--sorting)
    - [1.8: Testing & Production Hardening](#phase-18-testing--production-hardening)
- [Project 2: RAG System](#project-2-rag-system)
    - [2.1: Document Upload & Storage](#phase-21-document-upload--storage)
    - [2.2: Text Extraction Pipeline](#phase-22-text-extraction-pipeline)
    - [2.3: Document Chunking](#phase-23-document-chunking)
    - [2.4: Vector Embeddings & Search](#phase-24-vector-embeddings--search)
    - [2.5: RAG Implementation](#phase-25-rag-implementation)
    - [2.6: Hybrid Search](#phase-26-hybrid-search)
    - [2.7: Production Optimization](#phase-27-production-optimization)
- [Project 3: Agentic AI Platform](#project-3-agentic-ai-platform)
    - [3.1: LangGraph Agent Framework](#phase-31-langgraph-agent-framework)
    - [3.2: Event Streaming (Redpanda)](#phase-32-event-streaming-redpanda)
    - [3.3: Intelligent Triggers](#phase-33-intelligent-triggers)
    - [3.4: Real-Time Chat](#phase-34-real-time-chat)
    - [3.5: Consistent Hashing](#phase-35-consistent-hashing)
    - [3.6: Horizontal Scaling](#phase-36-horizontal-scaling)
    - [3.7: Observability (Prometheus + Grafana)](#phase-37-observability-prometheus--grafana)
    - [3.8: Production Deployment](#phase-38-production-deployment)

---

# PROJECT 1: RESTful API Foundation

**Goal:** Build a secure, scalable REST API with authentication, rate limiting, and notifications.

**Architecture:** Layered (N-Tier)

---

## Phase 1.1: Foundation

**What:** Basic CRUD API with database connectivity

### Tasks
- [x] Create GitHub repository
- [x] Initialize FastAPI project structure
- [x] Set up Docker Compose (Postgres + Redis)
- [x] Create `.env.example` with config
- [x] Create User model (id, email, hashed_password, created_at)
- [x] Create Document model (id, title, owner_id, created_at)
- [x] Set up Alembic migrations
- [x] Configure async database connection
- [x] `GET /health` - Health check
- [x] `POST /auth/register` - User registration
- [x] `POST /documents` - Create document
- [x] `GET /documents` - List user documents
- [x] `GET /documents/{id}` - Get single document
- [x] `PUT /documents/{id}` - Update document
- [x] `DELETE /documents/{id}` - Delete document
- [x] Set up pytest with fixtures
- [x] Test each endpoint
- [x] Test validation errors
- [x] Achieve 70%+ test coverage

### Done When
- [x] All endpoints return correct status codes
- [x] Can register user and CRUD documents via Swagger UI
- [x] Tests pass with 70%+ coverage
- [x] Docker Compose runs everything successfully
- [x] Alembic migrations work (upgrade/downgrade)

### Interview Questions You Can Answer
- "Explain the difference between sync and async in Python"
- "How do you structure a FastAPI application?"
- "What's the difference between SQLAlchemy and SQLModel?"
- "How do you handle database migrations in production?"

---

## Phase 1.2: Authentication & Security

**What:** JWT authentication with secure password handling

### Tasks
- [x] Implement password hashing with pwdlib
- [x] Create JWT token generation (access + refresh)
- [x] `POST /auth/login` - Login endpoint
- [x] `POST /auth/refresh` - Refresh token endpoint
- [x] `POST /auth/logout` - Logout (token blacklist)
- [x] Create authentication dependency (`get_current_user`)
- [x] Protect all document endpoints
- [x] Implement ownership verification
- [x] Add role-based access (optional: admin role)
- [x] CORS configuration
- [x] HTTPS enforcement
- [x] Security headers middleware
- [x] Test login with valid/invalid credentials
- [x] Test protected endpoints without token (401)
- [x] Test accessing other user's documents (403)
- [x] Test expired tokens

### Done When
- [x] Login returns JWT tokens
- [x] Protected endpoints require valid token
- [x] Cannot access other user's documents
- [x] Token refresh works
- [x] Security headers present in responses

### Interview Questions You Can Answer
- "Explain how JWT authentication works"
- "What's the difference between access and refresh tokens?"
- "How do you secure a REST API?"
- "Session-based vs token-based auth - trade-offs?"

---

## Phase 1.3: Rate Limiting

**What:** Token Bucket rate limiting to prevent API abuse

### Tasks
- [x] Add Redis to Docker Compose
- [x] Configure Redis connection
- [x] Test Redis connectivity
- [x] Implement Token Bucket algorithm
- [x] Create rate limit middleware
- [x] Different limits per user tier (free: 10/min, paid: 100/min)
- [x] Return rate limit headers (X-RateLimit-*)
- [ ] Test rate limit enforcement
- [ ] Test rate limit headers
- [ ] Test rate limit reset
- [ ] Test different user tiers

### Done When
- [x] Rate limiting enforces limits correctly
- [x] Returns 429 when limit exceeded
- [x] Rate limit headers present
- [ ] Can handle 1000 req/s without crashing
- [x] Different tiers have different limits

### Interview Questions You Can Answer
- "Design a rate limiting system"
- "Explain Token Bucket algorithm"
- "How do you implement rate limiting in a distributed system?"
- "What's the difference between rate limiting algorithms?"

---

## Phase 1.4: Unique ID Generation

**What:** Twitter Snowflake algorithm for distributed IDs

### Tasks
- [x] Create SnowflakeID generator class
- [x] Thread-safe implementation
- [x] Handle clock skew
- [x] Configuration for datacenter/worker IDs
- [x] Replace auto-increment IDs with Snowflake
- [x] Update database models
- [x] Create migration
- [x] Update all ID references
- [ ] Generate 10,000 IDs - all unique
- [x] IDs are sortable by time
- [x] Thread-safe (concurrent generation)
- [x] Handle clock backwards

### Done When
- [x] Can generate unique IDs
- [ ] IDs are sortable by creation time
- [ ] Thread-safe (tested with concurrent generation)
- [x] All models use Snowflake IDs
- [x] Database migration successful

### Interview Questions You Can Answer
- "Design a distributed unique ID generator"
- "Explain Twitter Snowflake algorithm"
- "What happens if the clock goes backward?"
- "UUID vs Snowflake - which and when?"

---

## Phase 1.5: URL Shortener

**What:** Base62 URL shortening for document sharing

### Tasks
- [x] Implement Base62 encode/decode
- [x] Generate 11-character codes (3.5 trillion URLs)
- [x] Create ShortURL model (short_code, document_id, created_at, clicks)
- [x] Add database index on short_code
- [x] Track click analytics
- [x] `POST /share{document_id}` - Create short URL
- [x] `GET /{short_code}` - Redirect to document
- [x] `GET /documents/{short_code}/stats` - View analytics
- [x] Test Base62 encoding/decoding
- [x] Test shortening and redirect
- [x] Test collision handling
- [ ] Test analytics tracking

### Done When
- [x] Can shorten document URLs
- [x] Redirects work correctly
- [x] Short codes are 11 characters - 11 is the mathematical minimum for Snowflake IDs in Base62
- [x] Handles collisions gracefully
- [x] Analytics tracked (clicks)

### Interview Questions You Can Answer
- "Design a URL shortening service (like bit.ly)"
- "How do you handle hash collisions?"
- "How do you scale a URL shortener?"
- "Base62 vs Base64 - which and why?"

---

## Phase 1.6: Notification System

**What:** Multi-channel notifications (in-app, webhook, email)

### Tasks
- [ ] Create Notification model (user_id, type, title, message, read_at)
- [ ] Support multiple types (document_uploaded, query_completed)
- [ ] Add database indexes
- [ ] `POST /notifications` - Create notification (internal)
- [ ] `GET /notifications` - List user notifications
- [ ] `GET /notifications/unread` - Unread count
- [ ] `PATCH /notifications/{id}/read` - Mark as read
- [ ] `DELETE /notifications/{id}` - Delete notification
- [ ] In-app notifications (database)
- [ ] Webhook delivery (HTTP POST)
- [ ] Email delivery (optional: with background task)
- [ ] Test notification creation
- [ ] Test webhook delivery
- [ ] Test marking as read
- [ ] Test filtering unread

### Done When
- [ ] Notifications created on events
- [ ] In-app notifications work
- [ ] Webhook delivery works
- [ ] Can mark notifications as read
- [ ] Unread count accurate

### Interview Questions You Can Answer
- "Design a notification system"
- "Push vs Pull notifications - trade-offs?"
- "How do you ensure webhook delivery?"
- "How do you handle notification preferences?"

---

## Phase 1.7: Idempotency, URI Versioning, Pagination, Filtering & Sorting

### Tasks
- [x] Create schemas for pagination and document filtering
- [x] Create pagination_params Dependency
- [x] Add IdempotencyMiddelware
- [x] Add Versioning middleware
- [x] Add get/set idepotent repsonse to redis
- [x] Add idempotency, filtering and sorting to document route (DELETE, PUT is idempotent by design, GET Supports idempotency via Idempotency-Key header)
- [x] Test

### Done When
- [ ] For any collection endpoints
- [ ] Consistent query parameter naming
- [ ] Idempotency keys for POST requests
- [ ] Ensure PUT/DELETE are idempotent by design

---

## Phase 1.8: Testing & Production Hardening

**What:** Comprehensive tests and production configuration

### Tasks
- [x] Unit tests for all routes
- [x] Integration tests for auth flow
- [x] Test database transactions
- [ ] Test error cases (404, 422, 500, 429)
- [x] Test rate limiting edge cases
- [ ] Mock external services
- [x] Achieve 80%+ coverage
- [x] Structured logging (JSON format)
- [ ] Request/response logging middleware
- [ ] Performance metrics (request duration)
- [ ] Error tracking
- [x] Production Dockerfile (multi-stage build)
- [x] Docker Compose for full stack
- [ ] Environment variable management
- [x] Health check endpoint
- [ ] Graceful shutdown
- [x] API documentation (auto-generated Swagger)
- [ ] README with setup instructions
- [ ] Architecture diagram
- [ ] Deployment guide

### Done When
- [ ] 80%+ test coverage
- [ ] All tests pass
- [ ] Docker Compose runs entire stack
- [ ] Logs are structured (JSON)
- [ ] Health check endpoint works
- [ ] Can deploy to production

### Interview Questions You Can Answer
- "How do you test a FastAPI application?"
- "What's your logging strategy?"
- "How do you dockerize a Python app?"
- "What are health checks and why are they important?"

---

## ✅ Project 1 Complete!

**You've built:**
- RESTful API with 15+ endpoints
- JWT authentication with refresh tokens
- Rate limiting (Token Bucket)
- Snowflake ID generation
- URL shortening service
- Multi-channel notifications
- 80%+ test coverage
- Production-ready Docker setup

---

# PROJECT 2: RAG System

**Goal:** AI-powered document analysis with semantic search and RAG

**Architecture:** Pipes & Filters + Background Processing

---

## Phase 2.1: Document Upload & Storage

**What:** File upload with MinIO (S3-compatible storage)

### Tasks
- [x] Add MinIO to Docker Compose
- [x] Create storage buckets
- [ ] Configure access policies
- [x] Test connectivity
- [x] `POST /documents/upload` - Multipart file upload
- [x] Support PDF, TXT, DOCX, MD
- [x] Validate file types and sizes
- [x] Generate unique filenames
- [x] Add file_path, file_size, mime_type fields to Document model
- [x] Add status field (uploading, processing, completed, failed)
- [x] Add error_message field
- [x] Create migration
- [x] `GET /documents/{id}/download` - Download file from MinIO
- [ ] Set proper Content-Type headers
- [x] Verify ownership
- [x] Test file upload (PDF, DOCX, TXT)
- [x] Test file size limits
- [x] Test invalid file types
- [x] Test download

### Done When
- [x] Files upload to MinIO
- [x] Metadata saved to Postgres
- [ ] Can download files
- [x] File validation works
- [ ] Status tracking implemented

### Interview Questions You Can Answer
- "Design a file storage system"
- "How do you handle large file uploads?"
- "Local storage vs object storage - trade-offs?"
- "How do you validate uploaded files?"

---

## Phase 2.2: Text Extraction Pipeline

**What:** Background workers extract text from documents

### Tasks
- [x] Configure Celery with Redis broker
- [x] Create Celery app
- [x] Add worker to Docker Compose
- [x] Test task execution
- [x] PDF extractor (PyPDF2)
- [x] DOCX extractor (python-docx)
- [x] Plain text extractor
- [x] Markdown extractor
- [x] Download file from MinIO
- [x] Extract text based on file type
- [x] Save extracted text to database
- [x] Update document status
- [x] Handle errors and retries
- [x] `GET /documents/{id}/status` - Check processing status
- [x] Return progress percentage
- [x] Return error messages
- [x] Test extraction for each file type
- [x] Test error handling
- [x] Test retry logic
- [x] Test status updates

### Done When
- [x] Celery worker running
- [x] Text extracted from all file types
- [x] Text saved to database
- [x] Status updates work
- [x] Error handling and retries work

### Interview Questions You Can Answer
- "Design a document processing pipeline"
- "How do you handle background tasks at scale?"
- "Explain Celery architecture"
- "How do you retry failed tasks?"

---

## Phase 2.3: Document Chunking

**What:** Split documents into 500-token chunks with 50-token overlap

### Tasks
- [x] Create Chunk model (document_id, text, position, tokens, embedding_id)
- [x] Add indexes (document_id, position)
- [x] Create migration
- [x] Implement token-based chunking (tiktoken)
- [x] Chunk size: 500 tokens
- [x] Overlap: 50 tokens
- [x] Handle edge cases (very short/long documents)
- [x] Celery task: chunk_document
- [x] Split text into chunks
- [x] Save chunks to database
- [x] Chain to embedding task
- [x] Test chunking algorithm
- [x] Test overlap calculation
- [x] Test edge cases (empty doc, single sentence)
- [x] Verify token counts

### Done When
- [x] Documents split into chunks
- [x] Chunks saved with position and token count
- [x] Chunking task chains to embedding
- [x] Edge cases handled
- [x] Cleanup logic & Transaction safety

### Interview Questions You Can Answer
- "How do you chunk documents for RAG?"
- "What's the optimal chunk size and why?"
- "Why use overlapping chunks?"
- "How do you handle very long documents?"

---

## Phase 2.4: Vector Embeddings & Search

**What:** Generate embeddings and implement semantic search with Qdrant

### Tasks
- [x] Add Qdrant to Docker Compose
- [x] Create collection with proper configuration
- [x] Configure HNSW index parameters
- [x] Test connectivity
- [x] Install Sentence Transformers
- [x] Choose embedding model (all-MiniLM-L6-v2)
- [x] Implement batch embedding
- [x] Optimize embedding performance
- [x] Celery task: embed_chunks
- [x] Generate embeddings in batches
- [x] Store vectors in Qdrant
- [x] Store embedding metadata
- [x] `POST /documents/search` - Semantic search
- [x] Generate query embedding
- [x] Search in Qdrant
- [x] Return ranked results with scores
- [ ] Test embedding generation
- [ ] Test search accuracy
- [ ] Test search performance (<100ms)
- [ ] Test batch processing

### Done When
- [ ] Qdrant collection created
- [ ] Embeddings generated for all chunks
- [ ] Search returns relevant results
- [ ] Search time < 100ms for 1M vectors
- [ ] Batch processing optimized

### Interview Questions You Can Answer
- "How do vector databases work?"
- "Explain semantic search vs keyword search"
- "What's HNSW and why use it?"
- "How do you choose embedding dimensions?"
- "Design a semantic search system"

---

## Phase 2.5: RAG Implementation

**What:** Combine search with Claude or Ollama for document Q&A

### Tasks
- [x] Install Anthropic SDK or Ollama
- [x] Configure API key
- [x] Test basic completion
- [x] Test streaming
- [x] Create RAG system prompt
- [x] Build context window
- [x] Add citation instructions
- [x] Test prompt variations
- [x] `POST /query/{document_id}/ask` - Ask about specific document
- [x] `POST /query` - Ask across all documents
- [x] Return answer with citations
- [x] Save query history
- [x] `GET /query/{id}/ask/stream` - Streaming response
- [x] Server-Sent Events (SSE)
- [x] Stream tokens in real-time
- [x] Create Query model (user_id, query, answer, chunks_used, created_at)
- [x] `GET /query/history` - List user's queries
- [x] `GET /query/{id}` - Get specific query
- [ ] Test answer quality
- [ ] Test citations
- [ ] Test streaming
- [ ] Test edge cases (no results, ambiguous question)

### Done When
- [x] Can ask questions about documents
- [x] Answers include citations
- [x] Streaming works smoothly
- [x] Query history saved
- [x] Answer quality is good (manual testing)

### Interview Questions You Can Answer
- "Explain RAG architecture"
- "How do you reduce LLM hallucinations?"
- "Design a document Q&A system"
- "What's the difference between RAG and fine-tuning?"
- "How do you handle LLM streaming?"

---

## Phase 2.6: Hybrid Search

**What:** Combine vector + keyword search with RRF re-ranking

### Tasks
- [x] Add tsvector column to chunks table
- [x] Create GIN index for full-text search
- [x] Create trigger to update tsvector
- [x] Test FTS queries
- [x] Implement keyword search function
- [x] Support phrase search
- [x] Support boolean operators (AND, OR, NOT)
- [x] Rank results by relevance
- [x] Implement RRF algorithm
- [x] Tune k parameter (typically 60)
- [x] Combine scores from both searches
- [x] Combine vector and keyword search
- [x] Apply RRF to merge results
- [x] Return deduplicated, ranked results
- [x] Add hybrid_search parameter
- [x] Default to hybrid for best results
- [x] Support vector-only and keyword-only modes
- [ ] Test exact match queries
- [ ] Test semantic queries
- [ ] Test mixed queries
- [ ] Compare accuracy vs vector-only

### Done When
- [ ] Full-text search works
- [ ] Hybrid search combines both
- [ ] RRF merging implemented
- [ ] Better accuracy than vector-only
- [ ] Performance acceptable (<200ms)

### Interview Questions You Can Answer
- "Design a hybrid search system"
- "Explain Reciprocal Rank Fusion"
- "Vector vs keyword search - when to use each?"
- "How do you combine multiple ranking signals?"
- "Design a search system for technical documents"

---

## Phase 2.7: Production Optimization

**What:** Caching, cost reduction, and performance tuning

### Tasks
- [x] Implement Redis caching for RAG responses
- [x] Cache key: hash(query + document_id)
- [x] TTL: 1 hour
- [x] Cache invalidation on document update
- [x] Cache query embeddings (queries repeat)
- [x] TTL: 24 hours
- [x] Reduce embedding API calls
- [x] Filter low-relevance chunks (score < 0.7)
- [x] Reduce context size
- [x] Improve answer quality
- [x] Detect simple vs complex queries
- [x] Use cheaper models for simple queries
- [x] Route queries intelligently
- [x] Optimize Postgres connection pool
- [x] Optimize Redis connection pool
- [x] Tune pool sizes
- [x] Track search latency
- [x] Track LLM latency
- [x] Track cache hit rates
- [x] Set up alerts

### Done When
- [x] Response caching works (Redis)
- [x] Cache hit rate > 30%
- [x] LLM costs reduced by 40%+
- [x] Response time improved by 50%+
- [x] Cache invalidation works correctly

### Interview Questions You Can Answer
- "How do you optimize RAG system costs?"
- "Explain cache invalidation strategies"
- "How do you balance cost and quality?"
- "Design a caching layer for AI applications"
- "How do you prevent cache stampede?"

---

## ✅ Project 2 Complete!

**You've built:**
- Document upload with MinIO
- Text extraction pipeline (PDF, DOCX, TXT)
- Token-based chunking with overlap
- Vector embeddings with Sentence Transformers
- Semantic search with Qdrant
- RAG with Claude Sonnet 4 & Ollama llama3.2
- Streaming responses (SSE)
- Hybrid search (vector + keyword)
- Multi-layer caching

---

# PROJECT 3: Agentic AI Platform

**Goal:** Autonomous AI agents with event-driven architecture and production deployment

**Architecture:** Event-Driven Microservices

---

## Phase 3.1: LangGraph Agent Framework

**What:** AI agents with tools for autonomous multi-step reasoning

### Tasks
- [ ] Install LangGraph
- [ ] Understand state machines
- [ ] Create basic agent graph
- [ ] Test simple workflows
- [ ] `search_documents` - Search user's documents
- [ ] `query_database` - Execute read-only SQL
- [ ] `generate_report` - Create summary reports
- [ ] `send_notification` - Send notifications
- [ ] `web_search` - Search the web (optional)
- [ ] Define agent state (messages, iterations, final_answer)
- [ ] Create agent reasoning node
- [ ] Create tool execution node
- [ ] Define state transitions
- [ ] Add max iterations limit
- [ ] `POST /agent/query` - Chat with agent
- [ ] Save conversation history
- [ ] Return agent reasoning steps
- [ ] Handle errors gracefully
- [ ] Add agent
Add more tools:
    Web search (using Tavily or similar)
    Document comparison
    Statistical analysis
Improve prompts:
    Add system prompts
    Fine-tune tool descriptions
    Add few-shot examples
Add memory:
    Store conversation context
    Add user preferences
    Implement long-term memory
- [ ] `GET /agent/query/stream` - Stream agent thinking
- [ ] Show reasoning steps in real-time
- [ ] Show tool calls
- [ ] Test single tool usage
- [ ] Test multi-step reasoning
- [ ] Test max iterations
- [ ] Test error handling

### Done When
- [ ] Agent can use tools
- [ ] Multi-step reasoning works
- [ ] Streaming shows reasoning
- [ ] Conversation history saved
- [ ] Error handling robust

### Interview Questions You Can Answer
- "Design an AI agent system"
- "Explain ReAct prompting"
- "How do you give LLMs tools?"
- "What's the difference between RAG and agents?"
- "How do you handle agent failures?"

---

## Phase 3.2: Event Streaming (Redpanda)

**What:** Event-driven architecture with pub/sub messaging

### Tasks
- [ ] Add Redpanda to Docker Compose
- [ ] Create topics (events, triggers, analytics)
- [ ] Configure retention and partitions
- [ ] Test connectivity
- [ ] Define event types (Pydantic models)
- [ ] document.uploaded
- [ ] document.processed
- [ ] query.completed
- [ ] trend.detected
- [ ] anomaly.detected
- [ ] Create producer service
- [ ] Publish events on actions
- [ ] Add event metadata (timestamp, user_id)
- [ ] Handle producer errors
- [ ] Create consumer service
- [ ] Subscribe to topics
- [ ] Process events
- [ ] Handle consumer errors
- [ ] Publish events from API endpoints
- [ ] Publish events from Celery tasks
- [ ] Consume events in separate service
- [ ] Test event publishing
- [ ] Test event consumption
- [ ] Test event ordering
- [ ] Test error handling

### Done When
- [ ] Redpanda running
- [ ] Events published from API
- [ ] Events consumed successfully
- [ ] Event ordering maintained
- [ ] Error handling robust

### Interview Questions You Can Answer
- "Design an event-driven system"
- "Kafka vs RabbitMQ - when to use each?"
- "How do you ensure message ordering?"
- "Explain consumer groups"
- "How do you handle duplicate events?"

---

## Phase 3.3: Intelligent Triggers

**What:** Pattern detection (trends, anomalies) with automated actions

### Tasks
- [ ] Consume document events
- [ ] Track topic mentions over time
- [ ] Detect trending topics (threshold: 5 mentions/week)
- [ ] Publish trend.detected event
- [ ] Send notification
- [ ] Monitor system metrics
- [ ] Detect slow queries (> 5s)
- [ ] Detect failed uploads
- [ ] Publish anomaly.detected event
- [ ] Send alert
- [ ] Track user activity
- [ ] Generate weekly summaries
- [ ] Detect inactive users
- [ ] Send engagement notifications
- [ ] Consume trend/anomaly events
- [ ] Send via webhook
- [ ] Send via email (optional)
- [ ] Store in notification table
- [ ] Test trend detection
- [ ] Test anomaly detection
- [ ] Test notification delivery
- [ ] Test edge cases

### Done When
- [ ] Trend detection works
- [ ] Anomaly detection works
- [ ] Notifications sent automatically
- [ ] Runs as separate service

### Interview Questions You Can Answer
- "Design an intelligent monitoring system"
- "How do you detect anomalies in time-series data?"
- "Design a trend detection system"

---

## Phase 3.4: Real-Time Chat

**What:** WebSocket chat with streaming agent responses

### Tasks
- [ ] Connection management (connect/disconnect)
- [ ] Broadcast to user's connections
- [ ] Handle connection errors
- [ ] Track active users
- [ ] `/ws/chat/{conversation_id}` - WebSocket endpoint
- [ ] Authenticate via token
- [ ] Receive messages
- [ ] Stream agent responses
- [ ] Handle disconnections
- [ ] Save messages to database
- [ ] Load conversation history
- [ ] Pagination support
- [ ] Typing indicators
- [ ] Read receipts
- [ ] Agent thinking indicator
- [ ] Multi-device sync
- [ ] Test WebSocket connection
- [ ] Test message sending
- [ ] Test agent responses
- [ ] Test disconnection handling

### Done When
- [ ] WebSocket connections work
- [ ] Messages sent/received in real-time
- [ ] Agent responses stream
- [ ] Multi-device support works
- [ ] Reconnection handles gracefully

### Interview Questions You Can Answer
- "Design a real-time chat system"
- "WebSocket vs Server-Sent Events - when to use each?"
- "How do you handle WebSocket scaling?"
- "Design a notification system with WebSockets"

---

## Phase 3.5: Consistent Hashing

**What:** Distribute load using consistent hash ring with virtual nodes

### Tasks
- [ ] Implement consistent hash ring
- [ ] Add/remove nodes
- [ ] Virtual nodes (replicas)
- [ ] Find node for key
- [ ] Assign documents to shards based on hash
- [ ] Update database schema (add shard_id)
- [ ] Migrate existing documents
- [ ] Query routing based on shard
- [ ] Route requests based on user_id hash
- [ ] Sticky sessions (same user → same server)
- [ ] Health checks
- [ ] Failover handling
- [ ] Test even distribution
- [ ] Test adding nodes (minimal movement)
- [ ] Test removing nodes
- [ ] Test load balancing

### Done When
- [ ] Hash ring implemented
- [ ] Even load distribution (tested with 10k keys)
- [ ] Adding node moves < 30% of keys
- [ ] Documents sharded correctly
- [ ] Request routing works

### Interview Questions You Can Answer
- "Explain consistent hashing"
- "Design a distributed cache with consistent hashing"
- "How do you shard a database?"
- "What happens when you add a node to consistent hash ring?"
- "Why use virtual nodes?"

---

## Phase 3.6: Horizontal Scaling

**What:** Multiple API instances with nginx load balancer

### Tasks
- [ ] Remove any local state
- [ ] Use Redis for session storage
- [ ] Use Redis for rate limiting
- [ ] Ensure all APIs are idempotent
- [ ] Configure nginx as load balancer
- [ ] Least connections algorithm
- [ ] Health checks
- [ ] Sticky sessions for WebSockets
- [ ] Update docker-compose.yml
- [ ] Deploy multiple API replicas
- [ ] Configure shared volumes
- [ ] Test scaling
- [ ] Move sessions to Redis
- [ ] JWT tokens (already stateless)
- [ ] Shared rate limiting state
- [ ] Load test with 1000 concurrent users
- [ ] Test failover (kill one instance)
- [ ] Test session persistence
- [ ] Test WebSocket sticky sessions

### Done When
- [ ] 3 API instances running
- [ ] Load balanced across instances
- [ ] Can handle 1000 concurrent requests
- [ ] Failover works (kill one instance)
- [ ] No dropped WebSocket connections
- [ ] Graceful shutdown works

### Interview Questions You Can Answer
- "How do you scale an API horizontally?"
- "Explain sticky sessions and when you need them"
- "Design a stateless API"
- "What's graceful shutdown and why is it important?"
- "Load balancing algorithms - which and when?"

---

## Phase 3.7: Observability (Prometheus + Grafana)

**What:** Metrics, dashboards, and alerting

### Tasks
- [ ] Add Prometheus to Docker Compose
- [ ] Configure scrape targets
- [ ] Set up retention policies
- [ ] Test metric collection
- [ ] Add prometheus_client
- [ ] Expose /metrics endpoint
- [ ] Track request metrics
- [ ] Track custom business metrics
- [ ] Add Grafana to Docker Compose
- [ ] Connect to Prometheus
- [ ] Create dashboards
- [ ] Set up alerts
- [ ] API Performance dashboard
- [ ] RAG Performance dashboard
- [ ] Agent Performance dashboard
- [ ] System Resources dashboard
- [ ] Business Metrics dashboard
- [ ] High error rate alert (>5%)
- [ ] Slow response time alert (p95 >1s)
- [ ] High CPU/memory alert
- [ ] No document uploads in 24h alert
- [ ] Generate load and view metrics
- [ ] Verify dashboards update
- [ ] Test alert triggers
- [ ] Test alert notifications

### Done When
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards showing data
- [ ] Alerts configured
- [ ] Can debug performance issues using metrics
- [ ] Business metrics tracked

### Interview Questions You Can Answer
- "Design an observability system"
- "What metrics would you track for an API?"
- "Explain p50, p95, p99 latency"
- "How do you set up alerting?"
- "What's the RED method?"

---

## Phase 3.8: Production Deployment

**What:** CI/CD pipeline and AWS deployment

### Tasks
- [ ] Create GitHub Actions workflow
- [ ] Run tests on PR
- [ ] Build Docker image on merge
- [ ] Push to container registry
- [ ] Deploy to staging
- [ ] Deploy to production (manual approval)
- [ ] Set up Docker Hub or AWS ECR
- [ ] Configure authentication
- [ ] Tag images (git sha, version)
- [ ] Choose cloud (AWS ECS recommended)
- [ ] Set up infrastructure (Terraform or manual)
- [ ] Deploy services
- [ ] Configure load balancer
- [ ] Set up DNS
- [ ] Use AWS Secrets Manager or similar
- [ ] Store API keys securely
- [ ] Inject secrets at runtime
- [ ] Run Alembic migrations in CI
- [ ] Automated migration on deploy
- [ ] Rollback strategy
- [ ] Set up logging (CloudWatch or similar)
- [ ] Set up metrics (Prometheus in ECS)
- [ ] Set up alerts
- [ ] Set up uptime monitoring
- [ ] Deployment guide
- [ ] Runbook (common issues)
- [ ] Architecture diagram
- [ ] API documentation

### Done When
- [ ] CI/CD pipeline working
- [ ] Deployed to cloud
- [ ] Monitoring active
- [ ] Can deploy without downtime
- [ ] Rollback tested
- [ ] Documentation complete

### Interview Questions You Can Answer
- "How do you deploy to production?"
- "Explain CI/CD pipeline"
- "How do you handle database migrations?"
- "What's blue-green deployment?"
- "How do you manage secrets in production?"

---

## ✅ Project 3 Complete!

**You've built:**
- AI agents with LangGraph and tool use
- Event streaming with Redpanda
- Intelligent triggers (trend/anomaly detection)
- Real-time chat with WebSockets
- Consistent hashing for distribution
- Horizontal scaling (3+ instances)
- Full observability (Prometheus + Grafana)
- Production deployment with CI/CD


---

# 🏆 ALL 3 PROJECTS COMPLETE!

## What You've Accomplished

### ✅ Complete System
- **22 phases** completed
- **15 system design topics** mastered
- **20+ technologies** in production stack
- **80%+ test coverage**
- **Deployed to cloud**

### ✅ Skills Gained
- **Backend:** FastAPI, async Python, PostgreSQL, Redis
- **AI/ML:** RAG, embeddings, vector search, agents
- **Architecture:** Layered, Pipes & Filters, Event-Driven
- **DevOps:** Docker, CI/CD, Prometheus, Grafana
- **System Design:** 15 major patterns implemented
