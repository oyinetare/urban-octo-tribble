# Priority-ordered checklist for building an API

### 1. Foundation (Must have)
- [ ] **URI Design & HTTP Methods**
    - [ ] API designed around resources
    - [ ] Nouns for resource names & plural nouns for collections
    - [ ] Avoid mirroring internal database structure
    - [ ] Uniform interface + stateless request model
- [ ] **Consistent Response Format**
    - [ ] Standardised success responses
    - [ ] Standardised error response structure
    - [ ] Appropriate HTTP status codes
- [ ] **Validation & Error Handling**
    - [x] Input validation
    - [x] Exception handling
    - [x] Clear, actionable error messages
- [ ] **Basic Security**
    - [x] HTTPS (non-negotiable)
    - [x] Authentication (OAuth 2.0, JWT, or API Keys)
    - [x] Authorisation (who can access what)
- [ ] **Documentation**
    - [x] OpenAPI/Swagger specification
    - [x] Clear endpoint descriptions
    - [x] Request/response examples

### 2. Scalability & Reliability (Before production)
- [ ] **Asynchronous Operations (Where Appropriate)**
    - [ ] Only for long-running operations
    - [ ] Returns 202 (Accepted) with status tracking
    - [ ] Don't make simple CRUD async unnecessarily
- [ ] **Pagination, Filtering & Sorting**
    - [x] For any collection endpoints
    - [x] Consistent query parameter naming
- [x] **Rate Limiting**
    - [x] Prevent abuse
    - [x] Return 429 (Too Many Requests)
    - [x] Include rate limit headers
- [x] **Versioning**
    - [x] URI versioning (e.g., `/v1/resources`)
    - [x] Or header-based versioning
    - [x] Plan deprecation strategy
- [ ] **Idempotency**
    - [x] Idempotency keys for POST requests
    - [x] Ensure PUT/DELETE are idempotent by design

### 3. Production Hardening
- [ ] **Testing**
    - [ ] Unit tests
    - [ ] Integration tests
    - [ ] Contract tests
- [ ] **Monitoring & Logging**
    - [ ] Request/response logging
    - [ ] Performance metrics
    - [ ] Error tracking
    - [ ] Health check endpoints (non-public)
- [ ] **Caching**
    - [ ] Cache-Control headers
    - [ ] ETag support
    - [ ] Conditional requests (If-None-Match)
- [ ] **Request/Response Optimisation**
    - [ ] Payload size limits
    - [ ] Compression (gzip/brotli)
    - [ ] Support partial responses (field filtering)
    - [ ] Handle large payloads (streaming/chunking if needed)
- [ ] **CORS Configuration**
    - [ ] If browser-facing
    - [ ] Specify allowed origins, methods, headers

### 4. Advanced Features (Nice to have)
- [ ] **HATEOAS (Hypermedia Links)**
    - [ ] Self-descriptive APIs
    - [ ] Discoverability(Optional adds complexity)
- [ ] **Webhooks/Event Notifications**
    - [ ] For async operation completion
    - [ ] Real-time updates
- [ ] **Deployment Strategy**
    - [ ] CI/CD pipeline
    - [ ] Blue-green or canary deployments
    - [ ] Rollback procedures

___

## RESTful web API methods and their HTTP status codes

| Method  |  HTTP Status Codes | Idempotent |
|---------|-------------------|--------------
| GET     |                     | NO       |
|         | 200 (OK)            |          |
|         | 204 (No content)    |          |
|         | 404 (Not found)     |          |
| POST    |                     | YES      |
|         | 200 (OK)            |          |
|         | 201 (Created)       |          |
|         | 204 (No content)    |          |
|         | 400 (Bad Request)   |          |
|         | 405 (Method Not Allowed)|      |
| PUT     |                     | YES      |
|         | 200 (OK)            |          |
|         | 201 (Created)       |          |
|         | 204 (No content)    |          |
|         | 409 (Conflict)      |          |
| PATCH   |                     | YES      |
|         | 200 (OK)            |          |
|         | 400 (Bad Request)   |          |
|         | 409 (Conflict)      |          |
|         | 415 (Unsupported Media Type)|  |
| DELETE   |                    | YES      |
|          | 204 (NO CONTENT)   |          |
|          | 404 (NOT FOUND)    |          |

___

## References
- [Azure Architecture - Best practices for RESTful web API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [Azure Architecture - API design](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design)
