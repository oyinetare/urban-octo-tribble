## Questions

### 1
- 1
    - Explain the difference between sync and async in Python
    - RESTful API design principles
    - What's the difference between SQLAlchemy and SQLModel?
    - How do you handle database migrations in production?
    - How do you structure a FastAPI application?
    - API versioning strategies
    - N-Layered architecture benefits, trade-offs and alternatives

- 2
    - When and why would I need decorators?
    - Explain how JWT authentication works
    - What's the difference between access and refresh tokens?
    - How do you secure a REST API?
    - Session-based vs token-based auth - trade-offs? assuming thats the same question as Stateless authentication vs sessions
    - Importance of security headers

- 3
    - Redis operations
    - How middleware ware is implemented
    - Design a rate limiting system
    - Rate limiting strategies (IP, user, endpoint)
    - Explain Token Bucket algorithm
    - How do you implement rate limiting in a distributed system?
    - What's the difference between rate limiting algorithms?

- 4
    - Design a distributed unique ID generator
    - Explain Twitter Snowflake algorithm
    - What happens if the clock goes backward?
    - UUID vs Snowflake - which and when?

- 5
    - Design a URL shortening service (like bit.ly)
    - How do you handle hash collisions?
    - How do you scale a URL shortener?
    - Base62 vs Base64 - which and why?
    - Base62 encoding/decoding
    - HTTP redirects (301 vs 302)
    - Collision handling strategies
    - Analytics tracking
    - URL shortening architecture
    - Base conversion algorithms
    - Caching strategies for hot links

- 6
    - Design a notification system
    - Background task processing
    - Event-driven architecture basics
    - Push vs Pull notification patterns
    - Push vs Pull notifications - trade-offs?
    - Webhook implementation. How do you ensure webhook delivery? i.e.   Webhook reliability (retries, timeouts)
    - How do you handle notification preferences?
    - Notification system architecture
    - At-least-once delivery

- 7
    - How do you test a FastAPI application?
    - What's your logging strategy?
    - How do you dockerize a Python app?
    - What are health checks and why are they important?

---

### 2
- 1
    - Design a file storage system
    - How do you handle large file uploads?
    - Local storage vs object storage - trade-offs?
    - How do you validate uploaded files?
    - Object storage vs file storage
    - File upload patterns
    - Metadata vs content separation
    - Async processing triggers

- 2
    - Design a document processing pipeline
    - How do you handle background tasks at scale?
    - Explain Celery architecture
    - How do you retry failed tasks?
    - Pipes and Filters architecture
    - Worker pool patterns
    - Task queue vs message queue
    - Error handling in distributed systems

- 3
    - Chunking strategies and trade-offs (size, overlap)
    - How do you chunk documents for RAG?
    - What's the optimal chunk size and why?
    - Why use overlapping chunks?
    - How do you handle very long documents?
    - Context window management
    - Text preprocessing pipelines
    - Generator patterns in Python

- 4
    - How do vector databases work?
    - Explain semantic search vs keyword search
    - What's HNSW and why use it? and other undex types (IVF)
    - HNSW index algorithm understanding
    - How do you choose embedding dimensions and trade-offs?
    - Design a semantic search system
    - Batch processing optimization
    - Cosine similarity
    - Search relevance tuning
    - Approximate nearest neighbor search
    - Vector databases vs traditional databases

- 5
    - Explain RAG architecture
    - How do you reduce LLM hallucinations?
    - Design a document Q&A system
    - What's the difference between RAG and fine-tuning?
    - How do you handle LLM streaming?
    - Streaming responses
    - Server-Sent Events (SSE)

- 6
    - Design a hybrid search system
    - Explain Reciprocal Rank Fusion (RRF)
    - Vector vs keyword search - when to use each?
    - How do you combine multiple ranking signals?
    - Postgres full-text search
    - GIN indexes
    - Reciprocal Rank Fusion
    - Hybrid search implementation
    - Search quality evaluation
    - Hybrid search architecture
    - Re-ranking algorithms
    - Search quality metrics
    - Index optimization
    - Query performance tuning
    - Design a search system for technical documents

- 7
    - How do you optimize RAG system costs?
    - Explain cache invalidation strategies
    - How do you balance cost and quality?
    - Design a caching layer for AI applications
    - How do you prevent cache stampede?
    - Multi-layer caching strategies
    - Query optimization
    - Connection pool tuning
    - Caching trade-offs (TTL, consistency)
    - Cost optimization techniques
    - Cost vs quality trade-offs
    - Performance optimization strategies

---

### 3
- 1
    - Design an AI agent system
    - Explain ReAct prompting
    - How do you give LLMs tools?
    - What's the difference between RAG and agents?
    - How do you handle agent failures?
    - LangGraph framework
    - Agent state machines
    - Tool calling with Claude
    - Multi-step reasoning
    - Agent streaming
    - Agentic AI architecture
    - ReAct pattern (Reasoning + Acting)
    - Tool abstraction
    - Agent error handling
    - Conversation management

- 2
    - Design an event-driven system - Event-driven architecture
    - Kafka vs RabbitMQ - when to use each?
    - How do you ensure message ordering?
    - Explain consumer groups
    - How do you handle duplicate events?
    - Kafka/Redpanda basics
    - Pub/sub patterns
    - Message serialization
    - Consumer groups
    - Event sourcing
    - Event-driven architecture
    - Message ordering guarantees
    - Exactly-once vs at-least-once
    - Partitioning strategies

- 3
    - Design an intelligent monitoring system
    - How do you detect anomalies in time-series data?
    - Design a trend detection system

- 4
    - Design a real-time chat system
    - WebSocket vs Server-Sent Events - when to use each?
    - How do you handle WebSocket scaling?
    - Design a notification system with WebSockets
    - WebSocket implementation
    - Connection management
    - Real-time messaging
    - Bidirectional communication
    - WebSocket vs HTTP polling
    - Connection pooling
    - Heartbeat/ping-pong
    - Reconnection strategies

- 6
    - Explain consistent hashing
    - Consistent hashing vs simple hashing
    - Design a distributed cache with consistent hashing
    - How do you shard a database?
    - What happens when you add a node to consistent hash ring?
    - Why use virtual nodes?
    - Sharding strategies
    - Load distribution
    - Virtual nodes for better distribution
    - Data partitioning strategies
    - Replication for fault tolerance

- 7
    - Design an observability system
    - What metrics would you track for an API?
    - Explain p50, p95, p99 latency
    - How do you set up alerting?
    - What's the RED method?
    - RED method (Rate, Errors, Duration)
    - USE method (Utilization, Saturation, Errors)
    - SLIs, SLOs, SLAs
    - Observability (metrics, logs, traces)
    - Percentiles vs averages
    - Prometheus metrics
    - Grafana dashboards
    - Application instrumentation
    - Alerting rules
    - PromQL queries

- 8
    - How do you deploy to production?
    - Explain CI/CD pipeline
    - How do you handle database migrations?
    - What's blue-green deployment?
    - How do you manage secrets in production?

---

## Design patterns

### 1
- 1
    - Repository pattern
    - DI
    - DTOs
- 2
    - Strategy pattern
    - Decorator pattern
    - Middleware pattern
- 3
    - Token bucket algorithm
    - Middleware chain pattern
- 4
    - Singleton pattern
    - Factory pattern
- 5
    - Encoder pattern
    - Redirect pattern
    - Builder Pattern
- 6
    - Observer Pattern (Event Listeners)
    - Background Task Pattern
    - Template Method Pattern (Notification Formatting)

---

### 2
- 1
    - Adapter Pattern (Storage Abstraction)
    - Chain of Responsibility (File Validation)
    - Background Task Pattern (Async Processing)
- 2
    - Strategy Pattern (Text Extraction)
    - Template Method Pattern (Processing Pipeline)
    - Chain of Responsibility (Pipeline Stages)
- 3
    - Iterator Pattern (Chunk Generation)
    - Builder Pattern (Chunk Creation)
    - Repository Pattern (Chunk Storage)
- 4
    - Adapter Pattern (Vector Store)
    - Strategy Pattern (Embedding Models)
    - Batch Processing Pattern
- 5
    - Template Method Pattern (RAG Pipeline)
    - Strategy Pattern (Prompt Strategies)
- 6
    - Composite Pattern (Search Strategies)
    - Facade Pattern (Unified Search Interface)
- 7
    - Cache-Aside Pattern
    - Decorator Pattern (Caching Decorator)
    - Query Classification

---

### 3
- 1
    - State Machine Pattern (LangGraph)
    - Command Pattern (Agent Tools)
- 2
    - Event Sourcing Pattern
    - Publisher Pattern
    - Subscriber Pattern
- 3
- 4
    - Observer Pattern
    - WebSocket Endpoint
- 5
    - Consistent Hash Ring (from Phase 1.4 reference)
    - Middleware for Request Routing
    - Document Sharding
