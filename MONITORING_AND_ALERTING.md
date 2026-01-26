# Monitoring & Alerting Setup for Performance Fixes

## Overview

This guide establishes monitoring for:
1. **Fix Validation** - Verify fixes are working
2. **Performance Tracking** - Measure improvements from optimizations
3. **Error Detection** - Alert on regressions
4. **User Experience** - Track real-world impact

---

## PART 1: LOG-BASED MONITORING

### Monitoring Dashboard (ELK Stack / Splunk)

#### Search Queries for Validation

**Query 1: Recursion Limit Errors (Should be 0)**
```
source="/var/log/app.log" "Recursion limit of 25 reached"
| stats count
# Expected: 0 (previously: 13+)
```

**Query 2: Azure Blob Null Reference (Should be 0 ERRORs)**
```
source="/var/log/app.log" "'NoneType' object has no attribute 'get_blob_client'"
| stats count by severity
# Expected: 0 ERRORs (may see WARNINGs - graceful fallback)
```

**Query 3: Azure Blob Graceful Fallback (Expected)**
```
source="/var/log/app.log" "Azure Blob Storage not configured"
| stats count
# Expected: > 0 (if Azure not set up)
# Indicates graceful fallback working
```

**Query 4: Image Enrichment Working**
```
source="/var/log/app.log" "Enriching matches with vendor product images"
| stats count
# Expected: > 0 for vendor analysis requests
```

**Query 5: Standards RAG Completion**
```
source="/var/log/app.log" "Workflow complete in"
| stats avg(processing_time_ms), max(processing_time_ms), min(processing_time_ms)
# Expected: avg < 30,000ms (previously timeouts)
```

---

## PART 2: METRICS-BASED MONITORING

### Prometheus Setup

#### Custom Metrics Implementation

**File**: `backend/monitoring/metrics.py` (NEW - to create)

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# === RECURSION LIMIT MONITORING ===
recursion_limit_errors = Counter(
    'standards_rag_recursion_limit_errors_total',
    'Total recursion limit errors in Standards RAG',
    ['product_type']
)

# === PERFORMANCE METRICS ===
vendor_analysis_duration = Histogram(
    'vendor_analysis_duration_seconds',
    'Vendor analysis processing time',
    buckets=(30, 60, 120, 300, 600)  # 30s, 1m, 2m, 5m, 10m
)

standards_rag_duration = Histogram(
    'standards_rag_duration_seconds',
    'Standards RAG processing time',
    buckets=(5, 10, 20, 60, 120)
)

# === AZURE BLOB MONITORING ===
azure_blob_cache_failures = Counter(
    'azure_blob_cache_failures_total',
    'Total Azure Blob caching failures',
    ['reason']  # 'not_configured', 'connection_error', 'timeout'
)

azure_blob_cache_successes = Counter(
    'azure_blob_cache_successes_total',
    'Total Azure Blob caching successes'
)

# === IMAGE FETCHING MONITORING ===
vendor_image_fetch_duration = Histogram(
    'vendor_image_fetch_duration_seconds',
    'Time to fetch vendor product images',
    buckets=(1, 3, 5, 10)
)

vendor_image_fetch_results = Counter(
    'vendor_image_fetch_results_total',
    'Vendor image fetch results',
    ['source', 'status']  # source: google_cse/serpapi, status: success/failure
)

# === CACHING METRICS ===
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Global cache hit rate',
    labels=['cache_type']  # standards_rag, vendor_analysis, schema
)

# === LLM TIMEOUT MONITORING ===
llm_timeout_events = Counter(
    'llm_timeout_events_total',
    'Total LLM timeout events',
    ['model', 'operation']
)

# === USAGE METRICS ===
workflow_duration_seconds = Histogram(
    'workflow_duration_seconds',
    'Total workflow processing time',
    buckets=(60, 120, 300, 600, 1200)  # 1m to 20m
)

# === REQUEST VOLUME ===
requests_total = Counter(
    'requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)
```

#### Instrumentation

**File**: `backend/product_search_workflow/vendor_analysis_tool.py` (MODIFY)

```python
# Add at top
from monitoring.metrics import (
    vendor_analysis_duration,
    azure_blob_cache_failures,
    vendor_image_fetch_duration
)

# In analyze() method
def analyze(self, structured_requirements, product_type, ...):
    start_time = time.time()

    try:
        # ... analysis code ...

        # Record duration
        duration = time.time() - start_time
        vendor_analysis_duration.observe(duration)

        # Record vendor image fetching
        try:
            image_start = time.time()
            images = fetch_vendor_product_images(vendor)
            vendor_image_fetch_duration.observe(time.time() - image_start)
        except Exception as e:
            vendor_image_fetch_failures.labels(
                source='google_cse',
                status='failure'
            ).inc()

    except Exception as e:
        # Record errors
        if 'Recursion limit' in str(e):
            recursion_limit_errors.labels(product_type=product_type).inc()
        raise
```

#### Prometheus Queries

**Alert Rule 1: Recursion Limit Errors Detected**
```promql
increase(standards_rag_recursion_limit_errors_total[5m]) > 0
```
- **Threshold**: > 0 in 5 minutes
- **Severity**: CRITICAL
- **Action**: Investigate Standards RAG workflow

**Alert Rule 2: Azure Blob Cache Failures**
```promql
rate(azure_blob_cache_failures_total[5m]) > 0.05
```
- **Threshold**: > 5% failure rate
- **Severity**: WARNING
- **Action**: Check Azure connection string

**Alert Rule 3: Vendor Analysis Too Slow**
```promql
histogram_quantile(0.95, vendor_analysis_duration_seconds_bucket) > 300
```
- **Threshold**: 95th percentile > 5 minutes
- **Severity**: WARNING
- **Action**: Investigate performance (see Phase 1 optimizations)

**Alert Rule 4: Standards RAG Timeout**
```promql
increase(llm_timeout_events_total{operation="standards_rag"}[5m]) > 0
```
- **Threshold**: Any timeout in 5 minutes
- **Severity**: WARNING
- **Action**: Check LLM rate limits or increase timeout

**Alert Rule 5: Image Fetch Failures**
```promql
rate(vendor_image_fetch_results_total{status="failure"}[5m]) > 0.1
```
- **Threshold**: > 10% failure rate
- **Severity**: INFO
- **Action**: Note - gracefully falls back to non-image results

---

## PART 3: APPLICATION METRICS (Flask/Gunicorn)

### Response Time Tracking

**Middleware**: Track response times per endpoint

```python
# backend/monitoring/middleware.py

from flask import request, g
import time
from monitoring.metrics import requests_total

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time

    # Record Prometheus metric
    requests_total.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()

    # Log slow requests
    if duration > 30:  # Slow if > 30 seconds
        logger.warning(
            f"Slow request: {request.method} {request.path} "
            f"took {duration:.2f}s (status: {response.status_code})"
        )

    return response
```

### Endpoint-Specific Monitoring

**Vendor Analysis Endpoint**
```python
@app.route('/api/agentic/vendor-analysis', methods=['POST'])
def vendor_analysis():
    start_time = time.time()

    try:
        # ... vendor analysis code ...
        result = tool.analyze(...)

        # Log success
        duration = time.time() - start_time
        logger.info(
            f"[VENDOR_ANALYSIS] Complete: "
            f"{result['vendors_analyzed']} vendors, "
            f"{result['total_matches']} matches, "
            f"{duration:.1f}s"
        )

        return jsonify(result)

    except Exception as e:
        # Log error with timing
        duration = time.time() - start_time
        logger.error(
            f"[VENDOR_ANALYSIS] Failed after {duration:.1f}s: {e}"
        )
        raise
```

---

## PART 4: DATADOG DASHBOARD SETUP

### Dashboard Creation

**Datadog Dashboard JSON** (to import):

```json
{
  "title": "AI Product Recommender - Fix Monitoring",
  "widgets": [
    {
      "id": 1,
      "definition": {
        "type": "query_value",
        "requests": [
          {
            "q": "avg:standards_rag_duration_seconds{*}",
            "aggregator": "avg"
          }
        ],
        "title": "Standards RAG Avg Duration (s)"
      }
    },
    {
      "id": 2,
      "definition": {
        "type": "query_value",
        "requests": [
          {
            "q": "sum:standards_rag_recursion_limit_errors_total{*}",
            "aggregator": "sum"
          }
        ],
        "title": "Recursion Limit Errors (24h)"
      }
    },
    {
      "id": 3,
      "definition": {
        "type": "timeseries",
        "requests": [
          {
            "q": "rate(azure_blob_cache_successes_total{*}[1m])",
            "display_type": "line"
          },
          {
            "q": "rate(azure_blob_cache_failures_total{*}[1m])",
            "display_type": "line"
          }
        ],
        "title": "Azure Blob Cache Success/Failure Rate"
      }
    },
    {
      "id": 4,
      "definition": {
        "type": "distribution",
        "requests": [
          {
            "q": "vendor_analysis_duration_seconds{*}",
            "display_type": "distribution"
          }
        ],
        "title": "Vendor Analysis Duration Distribution"
      }
    }
  ]
}
```

### Alert Setup

**Alert 1: Recursion Limit Regression**
```
Alert when: avg:standards_rag_recursion_limit_errors_total{*} > 0
For: 5 minutes
Notify: @slack-alerts
Message: "Recursion limit errors detected - Standards RAG may be hanging"
```

**Alert 2: Azure Blob Caching Issues**
```
Alert when: avg:azure_blob_cache_failures_total{*} > 5
For: 10 minutes
Notify: @slack-alerts
Message: "Azure Blob caching failures exceeding threshold"
```

**Alert 3: Performance Degradation**
```
Alert when: p95:vendor_analysis_duration_seconds{*} > 300
For: 15 minutes
Notify: @slack-alerts
Message: "Vendor analysis taking > 5 minutes (p95)"
```

---

## PART 5: LOG AGGREGATION RULES

### CloudWatch Insights Queries

**Query 1: Daily Error Summary**
```
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| stats count() by @logStream
```

**Query 2: Standards RAG Performance Trend**
```
fields @timestamp, processing_time_ms
| filter @message like /Workflow complete in/
| stats avg(processing_time_ms), max(processing_time_ms), min(processing_time_ms) by bin(5m)
```

**Query 3: Vendor Analysis Bottleneck Detection**
```
fields vendor, analysis_time_ms
| filter @message like /START analysis for vendor/
| stats avg(analysis_time_ms), max(analysis_time_ms) by vendor
| sort max(analysis_time_ms) desc
```

**Query 4: Cache Hit Rate**
```
fields @timestamp, cache_hit, cache_miss
| stats sum(cache_hit) as hits, sum(cache_miss) as misses
| fields 100 * hits / (hits + misses) as hit_rate_percent
```

---

## PART 6: CUSTOM HEALTH CHECKS

### Health Check Endpoint

**File**: `backend/monitoring/health.py`

```python
from flask import jsonify
from datetime import datetime
import logging

@app.route('/health', methods=['GET'])
def health_check():
    """
    Comprehensive health check including fix validations.
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }

    # Check 1: Recursion Limit Fix
    try:
        from agentic.standards_rag.standards_rag_workflow import run_standards_rag_workflow
        # Try to import with new parameter
        import inspect
        sig = inspect.signature(run_standards_rag_workflow)
        has_recursion_param = 'recursion_limit' in sig.parameters
        health_status['checks']['recursion_limit_fix'] = {
            'status': 'ok' if has_recursion_param else 'missing',
            'message': 'Recursion limit parameter present' if has_recursion_param else 'Missing recursion_limit parameter'
        }
    except Exception as e:
        health_status['checks']['recursion_limit_fix'] = {
            'status': 'error',
            'message': str(e)
        }

    # Check 2: Azure Blob Null Check
    try:
        from generic_image_utils import cache_generic_image_to_azure
        # Try calling with None manager (should not crash)
        test_data = {'image_bytes': b'test', 'content_type': 'image/png'}
        result = cache_generic_image_to_azure('test', test_data)
        health_status['checks']['azure_null_check'] = {
            'status': 'ok',
            'message': 'Azure null check implemented'
        }
    except TypeError as e:  # Would be TypeError if fix not applied
        health_status['checks']['azure_null_check'] = {
            'status': 'error',
            'message': 'NoneType error - fix not applied'
        }

    # Check 3: Vendor Image Utils Module
    try:
        from agentic.vendor_image_utils import fetch_vendor_product_images
        health_status['checks']['vendor_image_utils'] = {
            'status': 'ok',
            'message': 'Vendor image utilities module loaded'
        }
    except ImportError:
        health_status['checks']['vendor_image_utils'] = {
            'status': 'error',
            'message': 'Module not found'
        }

    # Check 4: Database/Cache Connections
    try:
        # Try Redis
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        health_status['checks']['redis'] = {'status': 'ok'}
    except Exception as e:
        health_status['checks']['redis'] = {
            'status': 'warning',
            'message': str(e)
        }

    # Check 5: Vector Store (Pinecone)
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        pc.list_indexes()
        health_status['checks']['pinecone'] = {'status': 'ok'}
    except Exception as e:
        health_status['checks']['pinecone'] = {
            'status': 'warning',
            'message': str(e)
        }

    # Determine overall status
    errors = [c for c in health_status['checks'].values() if c['status'] == 'error']
    if errors:
        health_status['status'] = 'unhealthy'
        health_status['error_count'] = len(errors)
        return jsonify(health_status), 503

    warnings = [c for c in health_status['checks'].values() if c['status'] == 'warning']
    if warnings:
        health_status['status'] = 'degraded'

    return jsonify(health_status), 200
```

### Health Check Integration

**Monitoring Tool Setup** (K8s, ECS, etc.):
```yaml
# kubernetes/deployment.yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## PART 7: ALERTING RULES SUMMARY

| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| Recursion limit errors | > 0 in 5m | CRITICAL | Revert recursion fix |
| Azure Blob failures | > 5% in 5m | WARNING | Check Azure credentials |
| Vendor analysis duration | p95 > 5m | WARNING | Check Phase 1 optimizations |
| Standards RAG timeout | > 0 in 5m | WARNING | Increase timeout or optimize |
| Image fetch failures | > 10% in 5m | INFO | Graceful fallback active |
| Cache hit rate | < 40% | WARNING | Review caching strategy |
| API key rotation rate | > 10% | WARNING | Add more API keys |

---

## PART 8: MONITORING DASHBOARD (Text-based Quick View)

### Dashboard Commands

```bash
#!/bin/bash
# Quick monitoring view

echo "=== AIPR MONITORING DASHBOARD ==="
echo ""

echo "1. ERROR SUMMARY (Last Hour)"
docker logs <container> 2>&1 | grep -c ERROR
echo ""

echo "2. RECURSION LIMIT ERRORS (Last 24h)"
docker logs <container> 2>&1 | grep -c "Recursion limit of 25"
echo ""

echo "3. AZURE BLOB FAILURES (Last Hour)"
docker logs <container> 2>&1 | grep "Azure Blob" | grep -c "failed\|error"
echo ""

echo "4. VENDOR IMAGE SUCCESSES (Last Hour)"
docker logs <container> 2>&1 | grep -c "Retrieved.*images for"
echo ""

echo "5. STANDARDS RAG AVG TIME"
docker logs <container> 2>&1 | grep "Workflow complete in" | awk '{print $5}' | \
  awk '{sum+=$1; count++} END {if (count>0) printf "%.0f ms\n", sum/count}'
echo ""

echo "6. VENDOR ANALYSIS AVG TIME"
docker logs <container> 2>&1 | grep "END analysis for vendor" | tail -5 | awk '{print "  "$0}'
echo ""

echo "=== END DASHBOARD ==="
```

---

## PART 9: INTEGRATION WITH EXISTING MONITORING

### If Using Datadog

```python
# Add to app initialization
from datadog import initialize, api
from datadog_checks.base import AgentCheck

options = {
    'api_key': os.getenv('DATADOG_API_KEY'),
    'app_key': os.getenv('DATADOG_APP_KEY')
}
initialize(**options)

# Send custom metrics
def send_metric(metric_name, value, tags=None):
    api.Metric.send(
        metric=f'aipr.{metric_name}',
        points=value,
        tags=tags or []
    )
```

### If Using New Relic

```python
import newrelic.agent

# Initialize
newrelic.agent.initialize(os.getenv('NEW_RELIC_CONFIG_FILE'))

# Add instrumentation
@newrelic.agent.function_trace(name='vendor_analysis')
def analyze_vendors(...):
    # Automatically tracked by New Relic
    pass
```

### If Using Prometheus + Grafana

Create Grafana dashboard from Prometheus metrics:
```bash
# Export Prometheus metrics
curl http://localhost:9090/api/v1/query?query=vendor_analysis_duration_seconds

# Build Grafana dashboard in UI:
# Datasource: Prometheus (localhost:9090)
# Graphs:
#   - Vendor analysis duration (histogram)
#   - Recursion limit errors (counter)
#   - Azure blob success/failure (rate)
```

---

## PART 10: MONITORING CHECKLIST

After deploying fixes, verify monitoring is working:

- [ ] Prometheus metrics scraping active
- [ ] Datadog/monitoring platform receiving data
- [ ] Log aggregation showing recent logs
- [ ] Health check endpoint returning 200
- [ ] All custom metrics visible in dashboard
- [ ] Alert rules configured and active
- [ ] Slack/PagerDuty integrations working
- [ ] Baseline metrics recorded
- [ ] Performance tracking dashboard created
- [ ] Team trained on reading metrics

---

## SUMMARY

Monitoring setup provides:

1. **Fix Validation**: Confirms all three fixes deployed successfully
2. **Error Detection**: Catches regressions immediately
3. **Performance Tracking**: Measures impact of optimizations
4. **User Impact**: Shows real-world improvement
5. **Alerting**: Team notified of issues

**Next Steps**:
1. Deploy monitoring middleware
2. Configure alert rules
3. Create dashboard
4. Set baseline metrics
5. Begin tracking improvements from Phase 1 optimizations

