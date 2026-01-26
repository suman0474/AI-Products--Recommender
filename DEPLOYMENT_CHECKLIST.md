# Deployment Checklist for HIGH Priority Fixes

## Pre-Deployment Verification

### Step 1: Code Review ✓
- [x] LangGraph recursion limit fix in standards_rag_workflow.py
- [x] Azure Blob null checks in generic_image_utils.py
- [x] Image fetching integration in vendor_analysis_tool.py
- [x] New vendor_image_utils.py module created
- [x] All files passed Python syntax validation

**Status**: Ready for deployment

---

## Step 2: Environment Configuration Checklist

### Required for Deployment
- [ ] **GOOGLE_API_KEY** is set in `.env`
  ```bash
  echo $GOOGLE_API_KEY | grep -o "AIzaSy.*" | head -c 20
  # Should output: AIzaSy... (first 20 chars)
  ```

- [ ] **PINECONE_API_KEY** is set
  ```bash
  echo $PINECONE_API_KEY | grep -o "pcsk_.*" | head -c 20
  # Should output: pcsk_... (first 20 chars)
  ```

### Optional but Recommended
- [ ] **REDIS_URL** is accessible (or set `USE_REDIS_RATE_LIMIT=false`)
  ```bash
  redis-cli ping
  # Expected output: PONG

  # If not running:
  docker run -d -p 6379:6379 --name redis redis:latest
  ```

- [ ] **AZURE_STORAGE_CONNECTION_STRING** is valid
  ```bash
  python -c "
  from azure.storage.blob import BlobServiceClient
  try:
      client = BlobServiceClient.from_connection_string(
          '${AZURE_STORAGE_CONNECTION_STRING}'
      )
      list(client.list_containers())
      print('✓ Azure connection OK')
  except Exception as e:
      print('✗ Azure connection failed:', e)
  "
  ```

- [ ] **GOOGLE_CX** is set (for vendor product image search)
  ```bash
  echo $GOOGLE_CX
  # Should output: a long string like "c123456789..."
  ```

**Configuration Status**:
```bash
#!/bin/bash
echo "=== DEPLOYMENT CONFIGURATION CHECK ==="
[ -n "$GOOGLE_API_KEY" ] && echo "✓ GOOGLE_API_KEY" || echo "✗ GOOGLE_API_KEY"
[ -n "$PINECONE_API_KEY" ] && echo "✓ PINECONE_API_KEY" || echo "✗ PINECONE_API_KEY"
[ -n "$AZURE_STORAGE_CONNECTION_STRING" ] && echo "✓ AZURE_STORAGE_CONNECTION_STRING" || echo "✗ AZURE_STORAGE_CONNECTION_STRING"
[ -n "$GOOGLE_CX" ] && echo "✓ GOOGLE_CX" || echo "✗ GOOGLE_CX"
redis-cli ping &>/dev/null && echo "✓ Redis" || echo "✗ Redis"
```

---

## Step 3: Pre-Deployment Testing

### Test 1: Python Syntax Validation
```bash
cd /app/backend

python -m py_compile agentic/standards_rag/standards_rag_workflow.py
python -m py_compile generic_image_utils.py
python -m py_compile agentic/vendor_image_utils.py
python -m py_compile product_search_workflow/vendor_analysis_tool.py

echo "✓ All files compiled successfully"
```

### Test 2: Import Validation
```bash
python -c "
from agentic.standards_rag.standards_rag_workflow import run_standards_rag_workflow
from agentic.vendor_image_utils import fetch_vendor_product_images
from product_search_workflow.vendor_analysis_tool import VendorAnalysisTool
print('✓ All imports successful')
"
```

### Test 3: Configuration Validation
```bash
python -c "
import os
required = ['GOOGLE_API_KEY', 'PINECONE_API_KEY']
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f'✗ Missing: {missing}')
else:
    print('✓ All required configs present')
"
```

### Test 4: Unit Test Standards RAG Recursion Fix
```bash
python -c "
from agentic.standards_rag.standards_rag_workflow import run_standards_rag_workflow
import time

# Test with simple question
question = 'What is a pressure transmitter?'
session_id = 'test-' + str(int(time.time()))

try:
    result = run_standards_rag_workflow(
        question=question,
        session_id=session_id,
        recursion_limit=50  # Test new parameter
    )
    if result.get('status') == 'success':
        print('✓ Standards RAG workflow works')
        print(f'  Processing time: {result.get(\"final_response\", {}).get(\"metadata\", {}).get(\"processing_time_ms\")}ms')
    else:
        print(f'✗ Workflow failed: {result.get(\"error\")}')
except Exception as e:
    print(f'✗ Exception: {e}')
"
```

### Test 5: Unit Test Azure Blob Null Check
```bash
python -c "
from generic_image_utils import cache_generic_image_to_azure

# Test with Azure not configured
test_image = {
    'image_bytes': b'fake_image_data',
    'content_type': 'image/png',
    'file_size': 1000
}

# Should return False gracefully, not crash
result = cache_generic_image_to_azure('Test Product', test_image)
print(f'✓ Azure caching gracefully handled: {result}')
"
```

### Test 6: Unit Test Vendor Image Fetching
```bash
python -c "
from agentic.vendor_image_utils import fetch_vendor_product_images

# Test image fetching (may be slow if Google CSE fails)
images = fetch_vendor_product_images('Emerson', product_type='Pressure Transmitter')
print(f'✓ Vendor image fetching returned {len(images)} images')
for img in images[:2]:
    print(f'  - {img.get(\"source\")}: {img.get(\"domain\")}')
"
```

**All Tests Passed?** ✓ Proceed to deployment

---

## Step 4: Deployment Options

### Option A: Direct File Replacement (Fastest)

**Time**: 5-10 minutes
**Risk**: Low
**Steps**:

```bash
# 1. Backup current files
cp backend/agentic/standards_rag/standards_rag_workflow.py \
   backend/agentic/standards_rag/standards_rag_workflow.py.backup

cp backend/generic_image_utils.py \
   backend/generic_image_utils.py.backup

cp backend/product_search_workflow/vendor_analysis_tool.py \
   backend/product_search_workflow/vendor_analysis_tool.py.backup

# 2. Copy new vendor_image_utils.py
cp /tmp/vendor_image_utils.py backend/agentic/vendor_image_utils.py

# 3. Restart Flask/Gunicorn
systemctl restart app
# OR for Docker:
docker restart <container-name>

# 4. Verify
curl http://localhost:5000/health
# Expected: {"status": "ok"}
```

### Option B: Git-based Deployment (Recommended)

**Time**: 15-30 minutes
**Risk**: Low
**Steps**:

```bash
# 1. Create feature branch
git checkout -b fix/high-priority-performance-and-stability

# 2. Stage changes
git add backend/agentic/standards_rag/standards_rag_workflow.py
git add backend/generic_image_utils.py
git add backend/product_search_workflow/vendor_analysis_tool.py
git add backend/agentic/vendor_image_utils.py

# 3. Verify changes
git diff --cached backend/
# Review changes carefully

# 4. Commit with message
git commit -m "Fix: High priority performance and stability improvements

- Increase LangGraph recursion limit to 50 (fixes 13 timeout errors)
- Add Azure Blob null checks (graceful fallback for 30+ crashes)
- Integrate vendor product image fetching in analysis workflow
- New vendor_image_utils module with Google CSE + SerpAPI fallback"

# 5. Push to feature branch (for code review)
git push origin fix/high-priority-performance-and-stability

# 6. After approval, merge to main
git checkout main
git pull origin main
git merge fix/high-priority-performance-and-stability
git push origin main

# 7. Deploy from main
docker build -t aipr:latest .
docker run -d -p 5000:5000 --env-file .env aipr:latest
```

### Option C: Rolling Deployment (Zero Downtime)

**Time**: 20-40 minutes
**Risk**: Very Low
**Steps**:

```bash
# 1. Deploy to canary instance (10% traffic)
docker run -d -p 5001:5000 \
  --env-file .env \
  --label version=v2-fixed \
  aipr:latest

# 2. Route 10% of traffic to canary
# (via load balancer or reverse proxy config)
# nginx.conf:
#   upstream backend {
#       server localhost:5000 weight=90;
#       server localhost:5001 weight=10;
#   }

# 3. Monitor canary for 15 minutes
while true; do
  curl -s http://localhost:5001/health | jq .
  sleep 30
done

# 4. If no errors, increase to 50%
# (update nginx.conf weights to 50/50)

# 5. Monitor for another 15 minutes
# 6. Full rollout (100% to new version)
# 7. Take down old instance
docker stop <old-container-id>
```

---

## Step 5: Post-Deployment Verification

### Verification 1: Application Health
```bash
# Check if app is running
curl http://localhost:5000/health
# Expected: {"status":"ok"}

# Check error logs
docker logs <container-name> | grep ERROR | head -20
# Should see NO instances of:
# - "Recursion limit of 25 reached"
# - "'NoneType' object has no attribute 'get_blob_client'"
```

### Verification 2: Standards RAG Workflow
```bash
# Test Standards RAG to verify recursion fix
curl -X POST http://localhost:5000/api/standards/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is a pressure transmitter?",
    "session_id": "test-session"
  }' | jq '.metadata.processing_time_ms'

# Expected: < 30,000ms (previously would timeout)
```

### Verification 3: Vendor Analysis
```bash
# Test vendor analysis with image enrichment
curl -X POST http://localhost:5000/api/agentic/vendor-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "Pressure Transmitter",
    "vendors": ["Emerson"],
    "structured_requirements": {}
  }' | jq '.vendor_matches[0].product_images'

# Expected: array of image objects with URL, source, domain
# Should see product_images field populated
```

### Verification 4: Error Log Monitoring
```bash
# Monitor logs for the next 1 hour
docker logs -f <container-name> | grep -E "WARN|ERROR"

# Expected to see:
# - "[CACHE_AZURE] Azure Blob Storage not configured" (WARNING - expected if Azure not set)
# - "[VENDOR_IMAGES] Retrieved X images for VENDOR" (INFO - expected)
# - "[VendorAnalysisTool] Enriching matches" (INFO - expected)

# Should NOT see:
# - "'NoneType' object has no attribute 'get_blob_client'" (ERROR)
# - "Recursion limit of 25 reached" (ERROR)
```

### Verification 5: Performance Baseline
```bash
#!/bin/bash
# Measure response times before/after

echo "=== PERFORMANCE BASELINE ==="

# Test 1: Single vendor analysis
echo -n "Single vendor analysis: "
time curl -s -X POST http://localhost:5000/api/agentic/vendor-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "Pressure Transmitter",
    "vendors": ["Emerson"],
    "structured_requirements": {}
  }' > /dev/null

# Test 2: Multiple vendor analysis
echo -n "Five vendor analysis: "
time curl -s -X POST http://localhost:5000/api/agentic/vendor-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "Pressure Transmitter",
    "vendors": ["Emerson", "Honeywell", "Siemens", "Yokogawa", "ABB"],
    "structured_requirements": {}
  }' > /dev/null

# Test 3: Standards RAG
echo -n "Standards RAG query: "
time curl -s -X POST http://localhost:5000/api/standards/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the standards for pressure transmitters?",
    "session_id": "perf-test"
  }' > /dev/null

echo ""
echo "=== BASELINE RECORDED ==="
echo "Save these times for comparison with Phase 1 optimizations"
```

---

## Step 6: Rollback Plan

If issues occur post-deployment:

### Immediate Rollback (< 5 minutes)
```bash
# 1. Identify the issue
docker logs <container-name> | tail -50

# 2. Decide which fix caused it
# - Recursion limit fix: Would cause workflow hangs
# - Azure null check: Would cause image caching warnings
# - Image fetching: Would cause vendor analysis slowness

# 3. Revert the problematic file
git revert <commit-hash>
# OR restore from backup
cp backend/agentic/standards_rag/standards_rag_workflow.py.backup \
   backend/agentic/standards_rag/standards_rag_workflow.py

# 4. Restart
docker restart <container-name>

# 5. Verify
curl http://localhost:5000/health
```

### Selective Rollback (if one fix causes issues)

```bash
# Option 1: Revert just the recursion limit (if causing hangs)
# Edit standards_rag_workflow.py:544
# Change recursion_limit=50 back to default (remove parameter)

# Option 2: Disable image fetching (if causing slowness)
# Edit vendor_analysis_tool.py:464-515
# Comment out the image enrichment section

# Option 3: Keep Azure null checks (safe, always useful)
# These have no downside
```

---

## Deployment Timeline

### Recommended Deployment Schedule

**Phase 1: Preparation (1 hour)**
- [ ] Review all code changes
- [ ] Run all pre-deployment tests
- [ ] Prepare rollback plan
- [ ] Alert team of deployment

**Phase 2: Deployment (15-30 minutes)**
- [ ] Choose deployment method (Option A, B, or C)
- [ ] Execute deployment
- [ ] Monitor error logs (5 minutes)

**Phase 3: Verification (30 minutes)**
- [ ] Run post-deployment verification tests
- [ ] Measure performance baseline
- [ ] Compare with previous metrics

**Phase 4: Monitoring (1 hour)**
- [ ] Monitor logs for errors
- [ ] Track key metrics
- [ ] Gather user feedback
- [ ] Document results

**Total Time**: 2.5 - 3 hours (with monitoring)

---

## Success Criteria

Deployment is successful if:

✅ **No Critical Errors**
```bash
docker logs <container-name> | grep ERROR
# Should return empty or only warnings
```

✅ **Recursion Limit Fixed**
```bash
grep "Recursion limit of 25" logs/*.log
# Should return 0 matches (previously had 13)
```

✅ **Azure Null Checks Working**
```bash
grep "Azure Blob Storage not configured" logs/*.log
# Should see WARNING messages instead of crashes
```

✅ **Image Enrichment Working**
```bash
grep "product_images" logs/*.log | wc -l
# Should see several mentions
```

✅ **Performance Baseline Established**
```bash
# Response times documented for Phase 1 optimization
# Can compare with improvements after quick wins
```

---

## Support & Troubleshooting

### Issue: "Recursion limit" errors still appearing

**Cause**: Configuration not reloaded
**Solution**:
```bash
# Force reload of Python modules
docker restart <container-name>
# Or manually clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

### Issue: "Azure Blob not configured" warnings

**Cause**: Azure connection string invalid
**Solution**:
```bash
# Option 1: Fix connection string
export AZURE_STORAGE_CONNECTION_STRING='...'

# Option 2: Disable Azure (graceful fallback already implemented)
# Just note these are memory-only now
```

### Issue: Image fetching causing timeout

**Cause**: Google CSE API slow or quota exhausted
**Solution**:
```bash
# Check if Google CSE is rate-limited
grep "Google CSE" logs/*.log | tail -5

# Option 1: Set GOOGLE_CX environment variable
export GOOGLE_CX='your_cse_id'

# Option 2: SerpAPI will fallback automatically
# Ensure SERPAPI_API_KEY is set
export SERPAPI_API_KEY='...'
```

### Issue: Performance slower than expected

**Cause**: Likely submission delays not removed or timeout still 150s
**Solution**:
```bash
# Verify fixes applied
grep "time.sleep(5)" backend/product_search_workflow/vendor_analysis_tool.py
# Should return empty

grep "timeout_seconds = 60" backend/llm_fallback.py
# Should show the fix
```

---

## Final Checklist

Before marking deployment as complete:

- [ ] All syntax checks passed
- [ ] All imports validated
- [ ] Environment configured
- [ ] Pre-deployment tests all green
- [ ] Deployment executed successfully
- [ ] Application is running (health check OK)
- [ ] No critical errors in logs
- [ ] Post-deployment verification complete
- [ ] Performance baseline established
- [ ] Rollback plan tested
- [ ] Team notified of changes
- [ ] Documentation updated
- [ ] Monitoring in place for next 24 hours

---

## Post-Deployment Monitoring (First 24 Hours)

**Hour 0-1**: Monitor logs actively for errors
**Hour 1-4**: Check logs every 30 minutes
**Hour 4-24**: Check logs hourly
**Day 2+**: Check logs daily

**Metrics to Track**:
- Error rate (should be 0%)
- Recursion limit errors (should be 0)
- Azure Blob errors (should be warnings only)
- Average response time (baseline for Phase 1 optimizations)
- Cache hit rate (should increase over time)

**Success**: No critical errors, performance baseline established, ready for Phase 1 performance optimizations.

