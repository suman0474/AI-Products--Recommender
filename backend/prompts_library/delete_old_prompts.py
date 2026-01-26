"""Delete old individual prompt files after consolidation"""
import os
from pathlib import Path

# Files to delete
files_to_delete = [
    'deep_agent_planner_prompt.txt',
    'deep_agent_worker_prompt.txt',
    'deep_agent_synthesizer_prompt.txt',
    'deep_agent_merger_prompt.txt',
    'deep_agent_iterative_worker_prompt.txt',
    'deep_agent_batch_planner_prompt.txt',
    'deep_agent_batch_worker_prompt.txt',
    'deep_agent_batch_synthesizer_prompt.txt',
    'llm_specs_generation_prompt.txt',
    'llm_specs_iterative_prompt.txt',
    'user_specs_extraction_prompt.txt',
    'key_discovery_prompt.txt',
    'sales_workflow_greeting_prompt.txt',
    'sales_workflow_intent_classifier_prompt.txt',
    'sales_workflow_requirements_extraction_prompt.txt',
    'summary_generation_prompt.txt',
    'merge_requirements_prompt.txt',
    'parameter_selection_prompt.txt',
    'solution_analysis_prompt.txt',
    'solution_instrument_list_prompt.txt',
    'strategy_rag_prompt.txt',
    'standards_rag_prompt.txt',
    'inventory_rag_prompt.txt',
    'strategy_chat_prompt.txt',
    'standards_chat_prompt.txt',
    'index_rag_intent_classification_prompt.txt',
    'index_rag_output_structuring_prompt.txt',
    'intent_classification_prompt.txt',
    'intent_tool_requirements_extraction_prompt.txt',
    'intent_routing_patterns.txt',
    'out_of_domain_message_prompt.txt',
    'ranking_tool_prompt.txt',
    'judge_prompt.txt',
    'vendor_discovery_prompt.txt',
    'model_family_discovery_prompt.txt',
    'schema_generation_prompt.txt',
    'user_specs_prompt.txt',
    'llm_specs_prompt.txt',
    'sales_agent_prompt.txt',
    'requirements_collection_prompt.txt',
    'validator_prompt.txt',
    'web_verifier_prompt.txt',
]

base_dir = Path(__file__).parent
deleted = 0
not_found = 0

print("=" * 60)
print("DELETING OLD INDIVIDUAL PROMPT FILES")
print("=" * 60)

for filename in files_to_delete:
    filepath = base_dir / filename
    if filepath.exists():
        try:
            filepath.unlink()
            print(f"✓ Deleted: {filename}")
            deleted += 1
        except Exception as e:
            print(f"✗ Error: {filename} - {e}")
    else:
        print(f"⊘ Not found: {filename}")
        not_found += 1

print("\n" + "=" * 60)
print(f"✓ Deleted: {deleted} files")
print(f"⊘ Not found: {not_found} files")
print("=" * 60)
print(f"\n🗑️  Cleanup complete! {deleted} old prompt files removed.")
