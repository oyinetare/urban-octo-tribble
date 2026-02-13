Testing Workflow

## Prerequisites

1. **Install dependencies:**
```bash
uv sync
``


2. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Add your Anthropic API key (or set up Ollama)

3. **Run migrations:**
```bash
alembic upgrade head
```

4. **Start all services:**
```bash
docker-compose up -d
```

5. **Start Celery worker:**
```bash
celery -A app.celery_app worker --loglevel=info
```

6. **Start FastAPI:**
```bash
uvicorn app.main:app --reload
```

---

## Configuration Options

### Option 1: Using Anthropic Claude (Recommended for Testing)

In `.env`:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx  # Your API key
LLM_FALLBACK_ENABLED=true       # Enable Ollama fallback
```

Get API key: https://console.anthropic.com/

### Option 2: Using Ollama (Local, Free)

1. **Install Ollama:**
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from: https://ollama.com/download
```

2. **Pull a model:**
```bash
ollama pull llama3.2
```

3. **In `.env`:**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Option 3: Dual Setup (Best for Production)

```bash
LLM_PROVIDER=anthropic           # Primary
LLM_FALLBACK_ENABLED=true       # Enable fallback
ANTHROPIC_API_KEY=sk-ant-xxxxx
OLLAMA_BASE_URL=http://localhost:11434
```

This configuration tries Anthropic first, falls back to Ollama if it fails.

---

## Testing Workflow

### Step 1: Register and Login

```bash
### Health
curl -X GET http://localhost:8000/health/live | jq

curl -X GET http://localhost:8000/health/ready | jq

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }' | jq

# Login and save TOKEN
TOKEN=$(curl -c cookies.txt -s -X POST http://localhost:8000/api/v1/auth/login \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=testuser&password=password123" | jq -r '.access_token')

# Refresh token
TOKEN=$(curl -b cookies.txt -s -X POST http://localhost:8000/api/v1/v1/auth/refresh | jq -r '.access_token')
```

### Step 2: Upload a Document

```bash
# Create a test document
echo "The capital of France is Paris. It is known for the Eiffel Tower and the Louvre Museum." > _test_doc/test_doc.txt


curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

Save the `document_id` from the response.

```bash
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@_test_docs/On System Design by Jim Waldo.pdf" \
  -F "title=System Design")

echo $RESPONSE | jq

DOC_ID=$(echo $RESPONSE | jq -r '.id')

while true; do
  STATUS_RESP=$(curl -s -X GET http://localhost:8000/api/v1/documents/$DOC_ID/status -H "Authorization: Bearer $TOKEN")
  echo $STATUS_RESP | jq -c '.'

  CURRENT_STATUS=$(echo $STATUS_RESP | jq -r '.status')
  if [[ "$CURRENT_STATUS" == "completed" || "$CURRENT_STATUS" == "failed" ]]; then
    break
  fi
  sleep 1
done
```

### Step 3: Wait for Processing

Check processing status:
```bash
curl -X GET http://localhost:8000/api/v1/documents/2017627157366444032/status \
  -H "Authorization: Bearer $TOKEN"
```
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about Paris",
    "max_chunks": 5,
    "min_score": 0.5
  }' | jq
```

```bash
# Get all queries (paginated)
curl -X GET "http://localhost:8000/api/v1/query/history?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN" | jq

# Get specific query
curl -X GET http://localhost:8000/api/v1/query/{query_id} \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Dynamo: Amazon’s Highly Available Key-value Store?",
    "limit": 5,
    "score_threshold": 0.1
  }' | jq
```

```bash
curl -X POST http://localhost:8000/api/v1/query/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Dynamo: Amazon’s Highly Available Key-value Store?",
    "limit": 5,
    "score_threshold": 0.1
  }'
```

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Dynamo: Amazon’s Highly Available Key-value Store",
    "limit": 5,
    "score_threshold": 0.1
  }' | jq
```

```bash
curl -X POST http://localhost:8000/api/v1/query/2018343746290192384/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Dynamo: Amazon’s Highly Available Key-value Store?",
    "limit": 5,
    "score_threshold": 0.1
  }' | jq
```

```bash
curl -X POST http://localhost:8000/api/v1/query/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "System Design",
    "limit": 5,
    "score_threshold": 0.1
  }' | jq
```

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is System Design?",
    "max_chunks": 1
  }' | jq
```

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me something",
    "max_chunks": 3,
    "min_score": 0.3
  }'
```

``` bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is system design?",
    "max_chunks": 5,
    "min_score": 0.6
  }'
```

```bash
curl -X POST http://localhost:8000/api/v1/query/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "What is the capital of France?", "max_chunks": 5}' \
  --no-buffer
```

# Re-stream previous query
```bash
curl http://localhost:8000/api/v1/query/2018265147218464768/ask/stream \
  -H "Authorization: Bearer $TOKEN" \
  --no-buffer
```

```bash
curl -X GET http://localhost:8000/api/v1/query/history \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

```bash
curl -X GET http://localhost:8000/api/v1/metrics/cache \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

curl -X GET http://localhost:8000/api/v1/metrics/performance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

curl -X GET http://localhost:8000/api/v1/metrics/summary \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

---

## Testing with Swagger UI

1. **Open Swagger:** http://localhost:8000/docs

2. **Authenticate:**
   - Click "Authorize" button
   - Login to get token
   - Enter token in format: `Bearer YOUR_TOKEN`

3. **Test endpoints:**
   - POST `/api/v1/documents/upload` - Upload document
   - GET `/api/v1/documents/{id}/status` - Check processing
   - POST `/api/v1/documents/{id}/ask` - Ask about document
   - POST `/api/v1/query` - Ask across all documents
   - GET `/api/v1/queries` - View history

---

## Advanced Testing

### Test Different File Types

```bash
# PDF
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "title=Research Paper"

# DOCX
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@report.docx" \
  -F "title=Annual Report"
```

### Test Edge Cases


Expected: "I couldn't find any relevant information..."

2. **Query with low similarity threshold:**

3. **Test provider fallback:**
   - Set `ANTHROPIC_API_KEY` to invalid value
   - Make a query
   - Should fallback to Ollama (if enabled)
   - Check logs: "Trying fallback provider: ollama"

---

Database Chunk → Celery Task → Qdrant
     ↓                            ↓
  chunk.id  →  add_document_chunk → payload.chunk_id
                                     ↓
                                   Search
                                     ↓
                                   RAG Service
                                     ↓
                                  Citation
---

```basjh
# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Watch the magic happen
docker-compose logs -f celery-worker
```

---
## Monitoring & Debugging

### Check Celery Logs

```bash
# In Celery worker terminal
# You should see:
# [2026-01-31 12:00:00] Task document_processing completed
# [2026-01-31 12:00:01] Task document_chunking completed
# [2026-01-31 12:00:02] Task embed_chunks completed
```

### Check Redis

```bash
docker exec -it redis redis-cli

# Check if vectors are stored
127.0.0.1:6379> KEYS *
```

### Check Qdrant

```bash
# View collections
curl http://localhost:6333/collections

# View collection info
curl http://localhost:6333/collections/documents
```

### Check Database

```bash
docker exec -it postgres psql -U postgres -d fastapi_db

# Check queries table
SELECT id, query, llm_provider, tokens_used FROM queries;

# Check chunks
SELECT id, document_id, position, tokens FROM chunks;
```

---

## Performance Testing

### Measure Response Times

```bash
# Time a query
time curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Paris known for?"}'
```

Expected:
- Vector search: < 100ms
- LLM generation: 1-3 seconds
- Total: < 5 seconds

### Test Concurrent Queries

```bash
# Install hey (HTTP load testing tool)
go install github.com/rakyll/hey@latest

# Run 10 concurrent requests
hey -n 10 -c 2 -m POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Paris?"}' \
  http://localhost:8000/api/v1/query
```

---

## Troubleshooting

### "LLM generation failed"

**Cause:** API key issue or service unavailable

**Solution:**
1. Check API key is valid
2. Check Ollama is running (if using Ollama)
3. Check logs for specific error
4. Enable fallback and try again

### "No relevant context found"

**Cause:** No documents uploaded or low similarity

**Solution:**
1. Verify document was processed: `GET /documents/{id}/status`
2. Lower `min_score` (try 0.3-0.5)
3. Try more general query
4. Check if chunks were created in database

### "Processing stuck at 'processing'"

**Cause:** Celery worker not running

**Solution:**
```bash
# Restart Celery worker
pkill -f celery
celery -A app.celery_app worker --loglevel=info
```

### Provider fallback not working

**Cause:** Fallback not enabled or secondary provider not configured

**Solution:**
1. Set `LLM_FALLBACK_ENABLED=true`
2. Configure both providers in `.env`
3. Test with intentionally invalid primary key

---

## Next Steps

✅ Basic RAG working? → Implement streaming (Phase 2.5 part 2)
✅ Want better answers? → Adjust chunk size/overlap in config
✅ Want faster responses? → Cache common queries in Redis
✅ Want better search? → Fine-tune similarity thresholds

---

## Example Test Scenario

**Complete end-to-end test:**

1. Upload 3 documents about different topics
2. Wait for all to process
3. Ask specific questions about each
4. Ask cross-document question
5. Check query history
6. Verify citations are accurate
7. Test with different min_score values
8. Monitor response times
9. Check token usage

This validates the entire RAG pipeline! 🎉

----

```bash
docker exec -it urban-octo-tribble-postgres psql -U postgres -d urban-octo-tribble -c SELECT FROM WHERE...
```
