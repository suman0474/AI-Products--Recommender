"""
Debug Implementation Demo
=========================

Shows actual terminal output with debug logs enabled.
Run this to see debugging in action with inputs and outputs.

Usage:
    python test_debug_demo.py
"""

import sys
import time
import logging
from datetime import datetime

# Configure logging to show all debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Enable debug flags
from debug_flags import set_debug_flag, enable_preset, debug_log, timed_execution, debug_langgraph_node, issue_debug, get_issue_counters, reset_issue_counters

print("\n" + "="*80)
print("DEBUG IMPLEMENTATION DEMONSTRATION")
print("="*80 + "\n")

# ============================================================================
# DEMO 1: Basic Debug Flags
# ============================================================================

print("\n" + "="*80)
print("DEMO 1: Basic Debug Flags - Flag Management")
print("="*80 + "\n")

print("[INPUT] Setting DEBUG_AGENTIC_API flag to True")
set_debug_flag("AGENTIC_API", True)

print("[INPUT] Setting DEBUG_WORKFLOW flag to True")
set_debug_flag("AGENTIC_WORKFLOW", True)

print("\n[OUTPUT] Testing basic debug log decorator:\n")

@debug_log("AGENTIC_API", log_args=True)
def fetch_workflow(workflow_id: str, user_id: str):
    """Simulates fetching a workflow from API"""
    print(f"[PROCESSING] Fetching workflow {workflow_id} for user {user_id}")
    time.sleep(0.5)
    return {"workflow_id": workflow_id, "status": "active", "user_id": user_id}

result = fetch_workflow("wf_123", "user_456")
print(f"[RESULT] {result}\n")

# ============================================================================
# DEMO 2: Timing Execution
# ============================================================================

print("\n" + "-"*80)
print("DEMO 2: Timing Execution - Performance Monitoring")
print("-"*80 + "\n")

print("[INPUT] Function takes 1.5 seconds with 1000ms threshold")
set_debug_flag("AGENTIC_WORKFLOW", True)

@timed_execution("AGENTIC_WORKFLOW", threshold_ms=1000)
def process_rag_query(query: str):
    """Simulates RAG query processing"""
    print(f"[PROCESSING] Running RAG query: '{query}'")
    time.sleep(1.5)
    return {"results": ["result_1", "result_2", "result_3"], "processing_type": "RAG"}

result = process_rag_query("What is SIL 3 certification?")
print(f"[RESULT] Found {len(result['results'])} results\n")

# ============================================================================
# DEMO 3: LangGraph Node Debugging
# ============================================================================

print("\n" + "*"*80)
print("DEMO 3: LangGraph Node Debugging - State Mutation Tracking")
print("*"*80 + "\n")

print("[INPUT] Workflow state with initial keys: ['input', 'messages']")
set_debug_flag("AGENTIC_WORKFLOW", True)

initial_state = {
    "input": "I need a pressure transmitter",
    "messages": ["user_message_1"],
    "current_workflow": "instrument_identifier"
}

print(f"[INPUT STATE] {initial_state}\n")

@debug_langgraph_node("AGENTIC_WORKFLOW", "classify_intent")
def classify_intent_node(state):
    """Simulates intent classification node"""
    print("[PROCESSING] Classifying user intent...")
    time.sleep(0.3)
    state["intent"] = "requirements"
    state["confidence"] = 0.95
    state["messages"].append("classified_intent")
    return state

result_state = classify_intent_node(initial_state)
print(f"[OUTPUT STATE] Added keys: intent, confidence")
print(f"[RESULT STATE] {result_state}\n")

# ============================================================================
# DEMO 4: Workflow State Transitions
# ============================================================================

print("\n" + "*"*80)
print("DEMO 4: Workflow Transitions - Route Decision Logging")
print("*"*80 + "\n")

from agentic.debug_utils import log_workflow_transition

print("[INPUT] User intent: 'requirements' detected")
set_debug_flag("INTENT_ROUTER", True)

log_workflow_transition(
    "INTENT_ROUTER",
    "classify_intent",
    "instrument_identifier_workflow",
    condition="intent==requirements"
)

print("[OUTPUT] Transition logged to terminal\n")

# ============================================================================
# DEMO 5: Issue-Specific Debugging
# ============================================================================

print("\n" + "*"*80)
print("DEMO 5: Issue-Specific Debugging - LLM & Cache Tracking")
print("*"*80 + "\n")

reset_issue_counters()

print("[INPUT] Making LLM API call for spec extraction")
issue_debug.llm_call("gpt-4", "specification_extraction", tokens=5000)

print("[INPUT] Cache miss on RAG query")
issue_debug.cache_miss("RAG_INDEX", "pressure_transmitter_4-20mA")

print("[INPUT] Cache hit on embedding")
issue_debug.cache_hit("EMBEDDING_CACHE", "SIL_3_certification")

print("[INPUT] LLM fallback triggered")
issue_debug.llm_fallback_triggered("gpt-4", "gpt-3.5-turbo", "rate_limit")

print("\n[OUTPUT] Counters summary:")
counters = get_issue_counters()
for counter_name, count in counters.items():
    if count > 0:
        print(f"  • {counter_name}: {count}")

print()

# ============================================================================
# DEMO 6: Session Orchestrator Integration
# ============================================================================

print("\n" + "*"*80)
print("DEMO 6: Session Orchestrator - Real Integration Test")
print("*"*80 + "\n")

set_debug_flag("SESSION_ORCHESTRATOR", True)

print("[INPUT] Creating new user session")
print("  user_id: user_abc123")
print("  main_thread_id: main_user_abc123_1706489400")
print()

try:
    from agentic.session_orchestrator import SessionOrchestrator

    orchestrator = SessionOrchestrator.get_instance()

    session = orchestrator.create_session(
        user_id="user_abc123",
        main_thread_id="main_user_abc123_1706489400",
        zone="US-EAST"
    )

    print(f"[OUTPUT] Session created successfully")
    print(f"[RESULT] {session.to_dict()}\n")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}\n")

# ============================================================================
# DEMO 7: Intent Router Integration
# ============================================================================

print("\n" + "*"*80)
print("DEMO 7: Intent Router - Real Integration Test")
print("*"*80 + "\n")

set_debug_flag("INTENT_ROUTER", True)

print("[INPUT] User query: 'I need a pressure transmitter 0-100 PSI 4-20mA output'")
print("       session_id: user_abc123")
print()

try:
    from agentic.intent_classification_routing_agent import IntentClassificationRoutingAgent

    agent = IntentClassificationRoutingAgent()

    result = agent.classify(
        query="I need a pressure transmitter 0-100 PSI 4-20mA output",
        session_id="user_abc123"
    )

    print(f"[OUTPUT] Classification result:")
    print(f"  • target_workflow: {result.target_workflow.value}")
    print(f"  • intent: {result.intent}")
    print(f"  • confidence: {result.confidence:.2f}")
    print(f"  • reasoning: {result.reasoning}")
    print(f"  • classification_time_ms: {result.classification_time_ms:.2f}\n")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}\n")

# ============================================================================
# DEMO 8: Debug Presets
# ============================================================================

print("\n" + "*"*80)
print("DEMO 8: Debug Presets - Enable Multiple Flags at Once")
print("*"*80 + "\n")

from debug_flags import enable_preset, get_enabled_flags

print("[INPUT] Enabling 'rag' preset for RAG system debugging")
enable_preset("rag")

print("\n[OUTPUT] Enabled flags:")
enabled_flags = get_enabled_flags()
for flag in sorted(enabled_flags.keys()):
    print(f"  + {flag}")

print()

# ============================================================================
# DEMO 9: Debug Context Manager
# ============================================================================

print("\n" + "*"*80)
print("DEMO 9: Debug Context Manager - Structured Debug Blocks")
print("*"*80 + "\n")

from agentic.debug_utils import DebugContext

print("[INPUT] Running workflow with DebugContext")
set_debug_flag("AGENTIC_WORKFLOW", True)

with DebugContext("AGENTIC_WORKFLOW", "process_product_requirements", session_id="user_abc123"):
    print("[PROCESSING] Processing product requirements...")
    time.sleep(0.2)

    print("[PROCESSING] Extracting specifications...")
    time.sleep(0.3)

    specs = {
        "pressure_range": "0-100 PSI",
        "output_signal": "4-20mA",
        "accuracy": "±0.5%"
    }

    print(f"[RESULT] Extracted {len(specs)} specifications")

print()

# ============================================================================
# DEMO 10: Complete Workflow Simulation
# ============================================================================

print("\n" + "*"*80)
print("DEMO 10: Complete Workflow Simulation - End-to-End")
print("*"*80 + "\n")

enable_preset("workflow")
reset_issue_counters()

print("[START] Simulating complete user request flow\n")

# Step 1: User input
user_input = "I need a pressure transmitter with 0-100 PSI range and 4-20mA output"
print(f"[1] USER INPUT: '{user_input}'")

# Step 2: Intent classification
from agentic.intent_classification_routing_agent import IntentClassificationRoutingAgent
try:
    agent = IntentClassificationRoutingAgent()
    routing_result = agent.classify(
        query=user_input,
        session_id="demo_session_123"
    )
    print(f"[2] INTENT CLASSIFIED: {routing_result.intent}")
    print(f"    → Route to: {routing_result.target_workflow.value}")
    print(f"    → Confidence: {routing_result.confidence:.2f}")

    # Step 3: Track LLM calls
    from agentic.debug_utils import track_llm_query
    track_llm_query(
        "INSTRUMENT_IDENTIFIER",
        "gpt-4",
        "spec_extraction",
        tokens_estimated=2000
    )
    print(f"[3] LLM CALL TRACKED: gpt-4 for spec extraction (~2000 tokens)")

    # Step 4: Cache operations
    from agentic.debug_utils import track_cache_operation
    track_cache_operation("PRODUCT_INDEX", "miss", "pressure_transmitter_0_100psi")
    print(f"[4] CACHE MISS: Product index query not cached")

    # Step 5: Database lookup
    print(f"[5] DATABASE LOOKUP: Searching products...")
    time.sleep(0.5)
    found_products = [
        {"id": "prod_001", "name": "PT-001", "pressure_range": "0-100 PSI", "output": "4-20mA"},
        {"id": "prod_002", "name": "PT-002", "pressure_range": "0-100 PSI", "output": "4-20mA"},
        {"id": "prod_003", "name": "PT-003", "pressure_range": "0-100 PSI", "output": "0-10V"},
    ]
    print(f"    → Found {len(found_products)} matching products")

    # Step 6: Cache the result
    track_cache_operation("PRODUCT_INDEX", "write", "pressure_transmitter_0_100psi", success=True)
    print(f"[6] CACHE WRITE: Caching product index results")

    # Step 7: Final result
    print(f"\n[FINAL OUTPUT] {len(found_products)} products found:")
    for i, product in enumerate(found_products, 1):
        print(f"    {i}. {product['name']}: {product['pressure_range']} PSI, {product['output']}")

    print(f"\n[STATISTICS]")
    counters = get_issue_counters()
    for counter_name, count in counters.items():
        if count > 0:
            print(f"    • {counter_name}: {count}")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n\n" + "="*80)
print("DEMO SUMMARY")
print("="*80)

print("""
+ Demo 1: Basic debug flags and log decorator
+ Demo 2: Timing execution with slow function detection
+ Demo 3: LangGraph node state mutation tracking
+ Demo 4: Workflow transition logging
+ Demo 5: Issue-specific debugging (LLM, cache, API keys)
+ Demo 6: Session orchestrator integration
+ Demo 7: Intent router integration
+ Demo 8: Debug presets for quick enablement
+ Demo 9: Debug context manager for structured blocks
+ Demo 10: Complete end-to-end workflow simulation

WHAT YOU SAW IN THE LOGS:
==============================================================================

1. [AGENTIC_API] >> ENTER fetch_workflow(...)
   └─ Function entry logged with arguments

2. [AGENTIC_API] << EXIT fetch_workflow => OK
   └─ Function exit logged with return status

3. [AGENTIC_WORKFLOW] SLOW: process_rag_query took 1500.45ms (threshold: 1000ms)
   └─ Slow function detection and warning

4. [AGENTIC_WORKFLOW] NODE_ENTER: classify_intent | state_keys=[...] | messages=1
   [AGENTIC_WORKFLOW] NODE_EXIT: classify_intent | 300.23ms | +['intent', 'confidence'] | -[]
   └─ LangGraph node execution with state mutations

5. [INTENT_ROUTER] TRANSITION: classify_intent -> instrument_identifier_workflow
   └─ Workflow routing decisions

6. [DEBUG:LLM_CALLS] CALL #1: model=gpt-4, purpose=specification_extraction, ~5000 tokens
   [DEBUG:CACHE] HIT [RAG_INDEX]: embedding_cache...
   [DEBUG:CACHE] MISS [RAG_INDEX]: pressure_transmitter_4_20mA...
   └─ Issue-specific debug tracking (always enabled)

7. [SESSION_ORCHESTRATOR] Created session for user 'user_abc123': main_user_abc123_1706489400
   └─ Session management events

8. [INTENT_ROUTER] Classifying: 'I need a pressure transmitter...'
   [INTENT_ROUTER] TRANSITION: classify_intent -> instrument_identifier_workflow
   └─ Intent classification with routing

HOW TO USE IN YOUR PROJECTS:
==============================================================================

Via environment variables:
    export DEBUG_AGENTIC_WORKFLOW=1
    export DEBUG_INTENT_ROUTER=1
    python main.py

Via presets (in code):
    from debug_flags import enable_preset
    enable_preset("workflow")     # Enable workflow debugging
    enable_preset("rag")          # Enable RAG system debugging
    enable_preset("full")         # Enable all debugging

Via decorators:
    from debug_flags import debug_log, timed_execution
    from agentic.debug_utils import debug_rag_query

    @debug_log("MY_MODULE")
    @timed_execution("MY_MODULE", threshold_ms=5000)
    def my_function():
        pass

Via context manager:
    from agentic.debug_utils import DebugContext

    with DebugContext("AGENTIC_WORKFLOW", "my_operation"):
        # Your code here
        pass

""")

print("="*80)
print("All debugging features are working! Check the logs above for outputs.")
print("="*80 + "\n")
