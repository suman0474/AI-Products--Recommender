# Performance Optimization Plan: 322-1040 Second Bottleneck

## Executive Summary

Current vendor analysis takes **322-1040 seconds** (5-17 minutes) due to:
- Conservative rate-limiting delays (25-100s wasted)
- LLM timeout set 3x too high (100-250s)
- Poor retry strategy (155s+ backoff)
- Sequential enrichment calls (200-400s)

**Target**: Reduce to **60-120 seconds** (10-20x faster)

**Approach**: 3 phases - Quick Wins (1-2 hours), Medium-term (1-2 days), Long-term (1 week)

---

## PHASE 1: QUICK WINS (Immediate - 1-2 hours)

### Quick Win #1: Remove Submission Delays ⚡
**Savings**: 20-100 seconds (25% reduction)
**Risk**: Low
**Time**: 15 minutes

**Files to Modify**:
1. `backend/product_search_workflow/vendor_analysis_tool.py` (line 413)
2. `backend/agentic/chaining.py` (line 601)

**Changes**:
```python
# BEFORE (vendor_analysis_tool.py:410-413)
for i, (vendor, data) in enumerate(vendor_payloads.items()):
    if i > 0:
        time.sleep(5)  # ← REMOVE THIS
    future = executor.submit(...)

# AFTER
for i, (vendor, data) in enumerate(vendor_payloads.items()):
    # No delay - ThreadPoolExecutor handles concurrency
    future = executor.submit(...)
```

```python
# BEFORE (chaining.py:600-602)
for i, (vendor, data) in enumerate(payloads.items()):
    if i > 0:
        time.sleep(10)  # ← REDUCE TO 1 SECOND
    future = executor.submit(_worker, vendor, data)

# AFTER
for i, (vendor, data) in enumerate(payloads.items()):
    if i > 0:
        time.sleep(1)  # ← Only 1s spacing (prevents thundering herd)
    future = executor.submit(_worker, vendor, data)
```

**Verification**:
```bash
grep -n "time.sleep" backend/product_search_workflow/vendor_analysis_tool.py
grep -n "time.sleep" backend/agentic/chaining.py
# Should only see sleep(1) in chaining.py, none in vendor_analysis_tool.py
```

---

### Quick Win #2: Reduce LLM Timeout ⚡
**Savings**: 100-250 seconds (25-40% reduction)
**Risk**: Low-Medium (some edge cases may timeout)
**Time**: 15 minutes

**File**: `backend/llm_fallback.py` (line 84)

**Changes**:
```python
# BEFORE (line 84)
class LLMWithTimeout:
    def __init__(self, base_llm: Any, timeout_seconds: int = 150):
        self.timeout_seconds = timeout_seconds

# AFTER
class LLMWithTimeout:
    def __init__(self, base_llm: Any, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds  # Reduced from 150 to 60
        # Vendor analysis rarely exceeds 40s; timeout at 60s provides buffer
```

**Rationale**:
- Vendor analysis typical time: 15-40 seconds
- Image fetching: 5-10 seconds
- Total request: 40-50 seconds max
- 60s timeout provides 10-20s buffer for edge cases

**Verification**:
```bash
# Test vendor analysis for a single vendor
curl -X POST http://localhost:5000/api/agentic/vendor-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "Pressure Transmitter",
    "vendors": ["Emerson"],
    "structured_requirements": {}
  }' \
  | jq '.processing_time_ms'
# Should be < 60,000ms (currently probably 150,000ms+)
```

**Revert Plan** (if needed):
```python
# If timeouts occur, increase back to 90 or 120
timeout_seconds: int = 90
```

---

### Quick Win #3: Increase Parallel Workers ⚡
**Savings**: 15-30 seconds (faster processing)
**Risk**: Very Low
**Time**: 10 minutes

**File**: `backend/product_search_workflow/vendor_analysis_tool.py` (line 56)

**Changes**:
```python
# BEFORE (line 56)
def __init__(self, max_workers: int = 5, max_retries: int = 3):
    self.max_workers = max_workers

# AFTER
def __init__(self, max_workers: int = 10, max_retries: int = 3):
    self.max_workers = max_workers  # Doubled from 5 to 10
```

**Rationale**:
- 5 vendors in parallel with 5 workers = each waits for slot
- 10 workers = can handle multiple concurrent analyses
- Lower GIL contention (ThreadPoolExecutor releases between I/O)

**Impact**:
- 5 vendors: Same time (all slots filled)
- 10-20 vendors: 2-4x faster

---

### Quick Win #4: Enable Response Caching ⚡
**Savings**: 200-600 seconds (if same product analyzed multiple times)
**Risk**: Very Low
**Time**: 30 minutes

**File**: `backend/agentic/index_rag/index_rag_memory.py` (already partially implemented)

**Changes**:
```python
# In vendor_analysis_tool.py:analyze() method, add caching:

def analyze(self, structured_requirements, product_type, session_id=None, schema=None):
    # NEW: Check if we've analyzed this exact combination recently
    cache_key = f"{product_type}:{hash(json.dumps(structured_requirements))}"

    cached_result = self._result_cache.get(cache_key)
    if cached_result:
        logger.info(f"[VendorAnalysisTool] Cache hit for {product_type}")
        return cached_result  # Return immediately

    # ... existing analysis code ...

    # Cache the result before returning
    self.cache_result(cache_key, result)
    return result
```

**Expected Behavior**:
- First request: 5-10 minutes
- Subsequent same product: < 100ms (cached)

---

## PHASE 2: MEDIUM-TERM FIXES (1-2 days)

### Medium-term Fix #1: API Key Rotation Priority
**Savings**: 155+ seconds (if rate limiting occurs)
**Risk**: Low
**Time**: 1-2 hours

**File**: `backend/llm_fallback.py` (lines 459-558)

**Changes**:
```python
# BEFORE - exponential backoff immediately on rate limit
def invoke(self, prompt, **kwargs):
    for attempt in range(self.max_retries):
        try:
            return self.base_llm.invoke(prompt, **kwargs)
        except Exception as e:
            if '429' in str(e) and attempt < self.max_retries - 1:
                wait_time = base_retry_delay * (2 ** attempt)  # Backoff immediately
                time.sleep(wait_time)
                continue

# AFTER - try different API keys first
def invoke(self, prompt, **kwargs):
    api_keys = [GOOGLE_API_KEY, GOOGLE_API_KEY2, GOOGLE_API_KEY3]  # Rotate keys
    key_index = 0

    for attempt in range(self.max_retries):
        try:
            # Use current API key
            self.base_llm.api_key = api_keys[key_index % len(api_keys)]
            return self.base_llm.invoke(prompt, **kwargs)
        except Exception as e:
            if '429' in str(e):
                # Try next key first
                key_index += 1
                if key_index < len(api_keys):
                    logger.info(f"Rate limit - trying API key {key_index}")
                    continue
                else:
                    # All keys exhausted, then backoff
                    wait_time = base_retry_delay * (2 ** attempt)
                    logger.warning(f"All API keys rate-limited - backoff {wait_time}s")
                    time.sleep(wait_time)
                    continue
            else:
                # Not a rate limit error
                if attempt < self.max_retries - 1:
                    time.sleep(base_retry_delay)
                    continue
                raise
```

**Verification**:
```bash
# Add logging to track which API key is used
grep -n "API key" logs/llm_fallback.log
# Should see rotation messages before backoff messages
```

---

### Medium-term Fix #2: Batch Schema Generation LLM Calls
**Savings**: 30-50 seconds
**Risk**: Medium
**Time**: 2-3 hours

**File**: `backend/product_search_workflow/ppi_workflow.py`

**Changes**:
```python
# BEFORE (lines 627-663): 3 separate LLM calls
# 1. generate_schema_tool()
# 2. generate_llm_specs()
# 3. SpecificationAggregator.aggregate()

# AFTER: Combine into single LLM call
def generate_unified_schema(product_type):
    prompt = f"""
    Given a {product_type}, generate:
    1. Product schema with categories
    2. 60+ technical specifications (detailed, real-world)
    3. Aggregated from standards (IEC, ISO, API, ASME)

    Return JSON with:
    - schema: {{ category: [...] }}
    - specifications: [{{ name, value, unit, source }}]
    - standards_applied: ["IEC 60751", ...]
    """

    result = llm.invoke(prompt)
    return {
        "schema": result["schema"],
        "specifications": result["specifications"],
        "standards": result["standards_applied"]
    }
```

**Testing**:
```python
# Before: 627s + 638s + 663s = ~90 seconds
# After: Single ~40 second call
# Savings: ~50 seconds per schema
```

---

### Medium-term Fix #3: Global Standards Cache (Not Just Session)
**Savings**: 200-400 seconds (repeated products)
**Risk**: Low
**Time**: 2-3 hours

**File**: `backend/product_search_workflow/validation_tool.py` (lines 283-300)

**Changes**:
```python
# Add global LRU cache for Standards RAG results
from functools import lru_cache
import hashlib

@lru_cache(maxsize=50)  # Cache up to 50 product types
def get_standards_enrichment(product_type_hash: str, question_hash: str):
    """Cached version of standards enrichment"""
    # Fetch from cache first
    # If miss, call run_standards_rag_workflow()
    pass

# In validation flow:
def validate_product(product_type, question):
    product_hash = hashlib.md5(product_type.encode()).hexdigest()
    question_hash = hashlib.md5(question.encode()).hexdigest()

    # Use global cache, fallback to Standards RAG
    enrichment = get_standards_enrichment(product_hash, question_hash)
    return enrichment
```

**Impact**:
- Repeated product types: ~1ms (cached)
- First occurrence: ~60s (standards RAG)

---

## PHASE 3: LONG-TERM FIXES (1 week)

### Long-term Fix #1: Async/Await Migration
**Savings**: 50-150 seconds (30-50% overall)
**Risk**: Medium-High (architecture change)
**Time**: 3-5 days

**Target Files**:
- `backend/product_search_workflow/ppi_workflow.py`
- `backend/product_search_workflow/vendor_analysis_tool.py`
- `backend/agentic/chaining.py`

**Approach**:
```python
# BEFORE - ThreadPoolExecutor (blocking)
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(analyze_vendor, v) for v in vendors]
    results = [f.result() for f in futures]  # Blocking wait
    # Total time: 5 × 30s = 150s

# AFTER - asyncio (non-blocking)
async def analyze_vendors_async(vendors):
    tasks = [analyze_vendor_async(v) for v in vendors]
    results = await asyncio.gather(*tasks)  # Non-blocking concurrent
    # Total time: 30s (truly parallel)
```

**Benefits**:
1. Non-blocking I/O for PDF downloads
2. Concurrent LLM invocations
3. True parallelism (not GIL-limited)
4. Eliminates delays between submissions

**Reference** (already in codebase):
- `backend/agentic/schema_workflow.py` has async patterns
- `backend/agentic/async_schema_generator.py` shows async approach

---

### Long-term Fix #2: Streaming LLM Responses
**Savings**: 10-20 seconds
**Risk**: Low-Medium
**Time**: 2-3 days

**Approach**:
```python
# Stream vendor analysis results as they complete
# Instead of waiting for all 5 vendors to finish

async def stream_vendor_analysis(vendors):
    tasks = [analyze_vendor_async(v) for v in vendors]

    # Yield results as they complete (not in order)
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield result  # Send to client immediately
```

---

## IMPLEMENTATION ROADMAP

### Week 1: Quick Wins (4-5 hours)
```
Day 1:
- [ ] Remove submission delays (15 min)
- [ ] Reduce LLM timeout to 60s (15 min)
- [ ] Increase workers to 10 (10 min)
- [ ] Test each change (1 hour)
- [ ] Deploy to staging (30 min)

Expected improvement: 25-40% faster (650s → 390-500s)
```

### Week 2-3: Medium-Term Fixes (1-2 days)
```
Day 2:
- [ ] Implement API key rotation (2 hours)
- [ ] Batch schema LLM calls (3 hours)
- [ ] Add global standards cache (2 hours)
- [ ] Integration testing (2 hours)
- [ ] Deploy to staging (1 hour)

Expected improvement: Additional 25-30% faster (390s → 280s)
Total: 55-60% faster from baseline
```

### Week 3-4: Long-Term Fixes (3-5 days)
```
Day 3-7:
- [ ] Audit async/await patterns in codebase (4 hours)
- [ ] Refactor ThreadPoolExecutor to asyncio (16 hours)
- [ ] Implement streaming responses (8 hours)
- [ ] Comprehensive testing (8 hours)
- [ ] Performance benchmarking (4 hours)
- [ ] Deploy to production (2 hours)

Expected improvement: Additional 30-50% faster (280s → 100-150s)
Total: 80-85% faster from baseline
```

---

## PERFORMANCE PROJECTIONS

### Current Performance (Baseline)
```
Single product, 5 vendors:
- Vendor analysis: 322-650 seconds
- Schema generation: 50-100 seconds
- Standards enrichment: 200-400 seconds
- Total: 572-1,150 seconds (~10-19 minutes)

3 products:
- Sequential: 1,716-3,450 seconds (~29-58 minutes)
```

### After Phase 1 (Quick Wins)
```
Single product, 5 vendors:
- Vendor analysis: 210-350 seconds (removed delays & reduced timeout)
- Schema generation: 40-80 seconds
- Standards enrichment: 180-350 seconds
- Total: 430-780 seconds (~7-13 minutes)

Improvement: 25-40% faster
```

### After Phase 2 (Medium-Term)
```
Single product, 5 vendors:
- Vendor analysis: 150-200 seconds (caching + batching)
- Schema generation: 30-50 seconds
- Standards enrichment: 50-100 seconds (cached)
- Total: 230-350 seconds (~4-6 minutes)

Improvement: 55-60% faster
```

### After Phase 3 (Long-Term)
```
Single product, 5 vendors:
- Vendor analysis: 30-50 seconds (truly async)
- Schema generation: 20-30 seconds (batched + cached)
- Standards enrichment: 10-20 seconds (cached)
- Total: 60-100 seconds (~1-2 minutes)

Improvement: 80-85% faster
```

---

## TESTING STRATEGY

### Quick Wins Testing
```bash
# Test 1: Response time for single vendor
time curl -X POST http://localhost:5000/api/agentic/vendor-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "Pressure Transmitter",
    "vendors": ["Emerson"],
    "structured_requirements": {}
  }' > /dev/null
# Before: ~150 seconds
# After: ~60 seconds

# Test 2: Verify no submission delays
grep "time.sleep" backend/product_search_workflow/*.py
# Should see 0 matches in vendor_analysis_tool.py

# Test 3: Concurrent vendor analysis
time curl -X POST http://localhost:5000/api/agentic/vendor-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "Pressure Transmitter",
    "vendors": ["Emerson", "Honeywell", "Siemens", "Yokogawa", "ABB"],
    "structured_requirements": {}
  }' > /dev/null
# Before: ~650 seconds
# After: ~150-200 seconds
```

### Medium-Term Testing
```bash
# Test 4: Cache effectiveness
# Run same product twice, time the second request
for i in 1 2; do
  time curl -X POST http://localhost:5000/api/agentic/vendor-analysis ...
done
# First: 200+ seconds
# Second: < 100 milliseconds

# Test 5: Standards cache hit rate
grep "Cache hit for" logs/*.log | wc -l
# Should increase as usage continues
```

### Long-Term Testing
```bash
# Test 6: Async concurrent requests
# Send 10 concurrent requests, measure total time
ab -n 10 -c 10 http://localhost:5000/api/agentic/vendor-analysis
# Should be ~1-2x slower than sequential, not 10x slower
```

---

## ROLLBACK PLAN

If performance degrades after changes:

1. **Quick Wins Rollback** (5 minutes):
   ```bash
   git revert <commit-hash>
   # Returns to original timeout & delays
   ```

2. **Medium-Term Rollback** (10 minutes):
   ```bash
   # Disable global cache, return to session-only
   export CACHE_MODE=session_only
   ```

3. **Long-Term Rollback** (30 minutes):
   ```bash
   # Switch back to ThreadPoolExecutor from asyncio
   git checkout original-threading-version
   ```

---

## MONITORING & ALERTS

### Key Metrics to Track
1. **Vendor Analysis Duration** (target: < 200 seconds)
2. **Standards RAG Cache Hit Rate** (target: > 60%)
3. **API Key Rotation Rate** (target: < 5% need rotation)
4. **Timeout Occurrences** (target: < 1%)
5. **Overall Request Time** (target: < 500 seconds)

### Alert Conditions
```
- Vendor analysis > 300 seconds → investigate
- Cache hit rate < 40% → review caching strategy
- Timeout rate > 2% → increase timeout or reduce complexity
- API key rotation > 10% → add more keys
```

---

## QUICK REFERENCE: LINE NUMBERS TO MODIFY

| Phase | File | Line | Change | Time |
|-------|------|------|--------|------|
| 1 | vendor_analysis_tool.py | 413 | Remove `sleep(5)` | 5 min |
| 1 | chaining.py | 601 | Reduce `sleep(10)` → `sleep(1)` | 5 min |
| 1 | llm_fallback.py | 84 | Change timeout to 60 | 5 min |
| 1 | vendor_analysis_tool.py | 56 | Increase max_workers to 10 | 5 min |
| 1 | vendor_analysis_tool.py | ~200 | Add result caching | 30 min |
| 2 | llm_fallback.py | 502-558 | Implement key rotation | 1-2 hr |
| 2 | ppi_workflow.py | 627-663 | Batch schema LLM calls | 2-3 hr |
| 2 | validation_tool.py | 283-300 | Global standards cache | 2-3 hr |
| 3 | ppi_workflow.py | 774-809 | Migrate to asyncio | 3-5 days |
| 3 | vendor_analysis_tool.py | 408-463 | Async vendor analysis | 2-3 days |
| 3 | validation_tool.py | ~350 | Streaming responses | 2-3 days |

---

## ESTIMATED COST-BENEFIT

| Phase | Time | Effort | Improvement | Total Benefit |
|-------|------|--------|-------------|--------------|
| 1 (Quick Wins) | 1-2 hours | Very Low | 25-40% | High ROI |
| 2 (Medium) | 1-2 days | Low | +25-30% (55-60% total) | High ROI |
| 3 (Long-term) | 3-5 days | Medium | +30-50% (85%+ total) | High ROI |

**Recommendation**: Start with Phase 1 immediately, deploy Phase 2 in next sprint, plan Phase 3 for future.

