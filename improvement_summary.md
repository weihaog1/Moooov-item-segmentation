# Item Segmentation System Improvement Summary

---

## 1. Synonym Detection & Merging

**Problem:** Inconsistent tokenization with different terms for the same product

**Solution:**
- Periodically extract top 1000-10000 high-frequency terms per language, use LLM to identify synonym groups (confidence >0.85)
- Automatically merge synonyms in dictionaries to canonical terms
- All queries auto-normalize to canonical terms, new `synonym_mappings` table added

**Impact:** Improved dictionary consistency, reduced duplicate entries

**Usage:**
```bash
# Run periodically 
python scripts/detect_synonyms.py   # Detect synonyms
python scripts/merge_synonyms.py    # Merge into dictionaries
```

---

## 2. Smart Filtering Mechanism

**Problem:** Results contain stopwords, promotional terms, and other noise

**Solution:**
- **LLM Prompt Filtering:** Covers stopwords in 10 languages, promotional terms, special characters
- **Post-processing Filter:** Auto-discard tokens with confidence <0.3, filter single characters


---

## 3. Error Handling & Fallback

**Problem:** LLM timeouts and network failures cause processing failures

**Solution:**
- **Retry Mechanism:** Exponential backoff (2s→4s→8s), max 3 retries
- **Circuit Breaker:** Opens after 5 consecutive failures, auto-recovery after 60s
- **Fallback Chain:** Cache → spaCy → LLM+Retry → Simple Tokenization → Return Original

no silent failures

---

## 4. Streaming Processing Architecture

**Problem:** Cannot support large data volumes and distributed scaling

**Solution:**
- **Celery + Redis task queue**, async processing without blocking API
- **Independent Worker Pools:**
  - Dictionary Workers (10 concurrency): Dictionary-only, ~1000 req/s
  - LLM Workers (2 concurrency): Full tokenization, ~5-10 req/s
- **Async APIs:** `/tokenize/async`, `/batch/async` support up to 1000 items per batch

**Impact:** Supports 10x data volume, independent scaling

**Scaling:**
```bash
docker-compose up -d --scale celery_dictionary_worker=3  # Scale to 30 concurrency
docker-compose up -d --scale celery_llm_worker=5         # Scale to 10 concurrency
```

---

## 5. Current System Architecture

### Service Components
- **MySQL:** Dictionaries, cache, synonym mappings
- **Redis:** Message queue, task distribution
- **API Service:** FastAPI, sync + async endpoints
- **Dictionary Workers:** 10 concurrency, lightweight processing
- **LLM Workers:** 2 concurrency, accurate tokenization

### Processing Flow
**Synchronous Mode:** Client → API → Processing → Return Result 

**Asynchronous Mode:** Client → API → Redis Queue → Worker Pool → Client Polls Result

### Fallback Strategy
1. Check cache first
2. Try spaCy pattern matching (fast)
3. Call LLM processing (with retry + circuit breaker)
4. Fallback to simple tokenization + dictionary lookup
5. Last resort: return original keyword

### Tech Stack
- **Backend:** Python + FastAPI + aiomysql
- **AI:** DeepSeek LLM + spaCy
- **Queue:** Celery + Redis
- **Deployment:** Docker Compose (4 services)

### Key Configuration
- LLM Timeout: 30s
- Max Retries: 3
- Circuit Breaker Threshold: 5 failures
- Dictionary Concurrency: 10
- LLM Concurrency: 2

---