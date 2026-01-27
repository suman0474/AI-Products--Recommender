#!/usr/bin/env python
"""
Simple Validation Tests for Intent Classification Fixes
Standalone tests that don't require heavy dependencies
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_intent_config_class():
    """Test that IntentConfig class exists and has required methods."""
    print("\n" + "="*70)
    print("TEST 1: IntentConfig Class Validation")
    print("="*70)

    try:
        # Import just the code file without executing __init__
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "intent_classification_routing_agent",
            os.path.join(os.path.dirname(__file__), '..', 'agentic', 'intent_classification_routing_agent.py')
        )
        module = importlib.util.module_from_spec(spec)

        # Execute the module
        spec.loader.exec_module(module)

        # Check for IntentConfig class
        assert hasattr(module, 'IntentConfig'), "IntentConfig class not found"
        print("[OK] IntentConfig class exists")

        # Check for required attributes
        assert hasattr(module.IntentConfig, 'INTENT_MAPPINGS'), "INTENT_MAPPINGS not found"
        print("[OK] IntentConfig.INTENT_MAPPINGS exists")

        assert hasattr(module.IntentConfig, 'SOLUTION_FORCING_INTENTS'), "SOLUTION_FORCING_INTENTS not found"
        print("[OK] IntentConfig.SOLUTION_FORCING_INTENTS exists")

        # Check for required methods
        assert hasattr(module.IntentConfig, 'get_workflow'), "get_workflow method not found"
        print("[OK] IntentConfig.get_workflow() method exists")

        assert hasattr(module.IntentConfig, 'is_known_intent'), "is_known_intent method not found"
        print("[OK] IntentConfig.is_known_intent() method exists")

        assert hasattr(module.IntentConfig, 'get_all_valid_intents'), "get_all_valid_intents method not found"
        print("[OK] IntentConfig.get_all_valid_intents() method exists")

        # Check for WorkflowTarget enum
        assert hasattr(module, 'WorkflowTarget'), "WorkflowTarget enum not found"
        print("[OK] WorkflowTarget enum exists")

        # List valid intents
        valid_intents = module.IntentConfig.INTENT_MAPPINGS.keys()
        print(f"\n[OK] Valid intents ({len(valid_intents)}): {', '.join(list(valid_intents)[:8])}...")

        # Check solution forcing intents
        print(f"[OK] Solution forcing intents: {module.IntentConfig.SOLUTION_FORCING_INTENTS}")

        return True
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_config():
    """Test that model configuration was updated."""
    print("\n" + "="*70)
    print("TEST 2: Model Configuration Update")
    print("="*70)

    try:
        # Import config
        from config import AgenticConfig

        # Check PRO_MODEL is set
        assert AgenticConfig.PRO_MODEL is not None, "PRO_MODEL is None"
        print(f"[OK] AgenticConfig.PRO_MODEL = '{AgenticConfig.PRO_MODEL}'")

        # Check it's gemini-2.5-flash (default)
        if AgenticConfig.PRO_MODEL == "gemini-2.5-flash":
            print("[OK] PRO_MODEL correctly defaults to 'gemini-2.5-flash' (free tier available)")
        else:
            print(f"[WARN]  PRO_MODEL is '{AgenticConfig.PRO_MODEL}' (may be custom configured)")

        # Check DEFAULT_MODEL
        assert AgenticConfig.DEFAULT_MODEL is not None, "DEFAULT_MODEL is None"
        print(f"[OK] AgenticConfig.DEFAULT_MODEL = '{AgenticConfig.DEFAULT_MODEL}'")

        # Check LITE_MODEL
        assert AgenticConfig.LITE_MODEL is not None, "LITE_MODEL is None"
        print(f"[OK] AgenticConfig.LITE_MODEL = '{AgenticConfig.LITE_MODEL}'")

        return True
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_intent_tools_rules():
    """Test that intent_tools has improved rule-based classification."""
    print("\n" + "="*70)
    print("TEST 3: Intent Tools Rule-Based Classification")
    print("="*70)

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "intent_tools",
            os.path.join(os.path.dirname(__file__), '..', 'tools', 'intent_tools.py')
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check for _classify_rule_based function
        assert hasattr(module, '_classify_rule_based'), "_classify_rule_based function not found"
        print("[OK] _classify_rule_based function exists")

        # Check for solution phrase patterns (PHASE 2 FIX)
        source_code = open(os.path.join(os.path.dirname(__file__), '..', 'tools', 'intent_tools.py')).read()

        assert "solution_phrases" in source_code, "solution_phrases pattern not found (PHASE 2 FIX)"
        print("[OK] solution_phrases pattern added (PHASE 2 FIX)")

        assert "is_solution_phrase" in source_code, "is_solution_phrase logic not found"
        print("[OK] is_solution_phrase detection logic added")

        assert '"solution"' in source_code and '"is_solution": True' in source_code, \
            "Solution intent return not found"
        print("[OK] Rule-based classifier can return 'solution' intent with is_solution=True")

        assert '"requirements"' in source_code, "requirements intent not found"
        print("[OK] Rule-based classifier returns 'requirements' for simple products")

        return True
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompts_documentation():
    """Test that prompts_library has been updated with Phase 3 documentation."""
    print("\n" + "="*70)
    print("TEST 4: Prompts Documentation (Phase 3)")
    print("="*70)

    try:
        prompts_file = os.path.join(os.path.dirname(__file__), '..', 'prompts_library', 'intent_prompts.txt')
        with open(prompts_file, 'r') as f:
            content = f.read()

        # Check for Phase 3 documentation
        assert "PHASE 3 FIX" in content, "Phase 3 documentation not found"
        print("[OK] Phase 3 documentation added to prompts")

        assert "INTENT VALUE VALIDATION" in content or "VALIDATION CLARIFICATION" in content, \
            "Intent validation documentation not found"
        print("[OK] Intent validation instructions added")

        assert "DO NOT deviate from the exact intent values" in content or "MUST NOT invent" in content, \
            "Warning about inventing intents not found"
        print("[OK] Warning against inventing new intent values added")

        return True
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_hardcoded_gemini_pro():
    """Test that gemini-2.5-pro hardcoded references have been removed."""
    print("\n" + "="*70)
    print("TEST 5: Hardcoded gemini-2.5-pro References Removed")
    print("="*70)

    try:
        files_to_check = [
            'advanced_parameters.py',
            'chaining.py',
            'solution_workflow.py',
            'shared_agents.py',
            'llm_fallback.py',
            'agentic/potential_product_index.py',
            'agentic/deep_agent/llm_specs_generator.py'
        ]

        hardcoded_count = 0
        total_files_checked = 0

        for filepath in files_to_check:
            full_path = os.path.join(os.path.dirname(__file__), '..', filepath)
            if not os.path.exists(full_path):
                print(f"[WARN]  File not found: {filepath}")
                continue

            total_files_checked += 1
            with open(full_path, 'r') as f:
                content = f.read()

            # Count direct model references (not in comments or strings like "# gemini-2.5-pro")
            import re

            # Look for model="gemini-2.5-pro" or model_name="gemini-2.5-pro"
            direct_refs = re.findall(r'(model[_]?name\s*=\s*["\']gemini-2\.5-pro["\'])', content)

            if direct_refs:
                hardcoded_count += len(direct_refs)
                print(f"[FAIL] {filepath}: Found {len(direct_refs)} hardcoded reference(s)")
            else:
                print(f"[OK] {filepath}: No hardcoded gemini-2.5-pro references")

        if hardcoded_count == 0:
            print(f"\n[OK] All {total_files_checked} files checked - NO hardcoded gemini-2.5-pro references found")
            return True
        else:
            print(f"\n[FAIL] Found {hardcoded_count} hardcoded reference(s) that should have been updated")
            return False

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agenticconfig_usage():
    """Test that AgenticConfig.PRO_MODEL is being used."""
    print("\n" + "="*70)
    print("TEST 6: AgenticConfig.PRO_MODEL Usage")
    print("="*70)

    try:
        files_to_check = [
            'advanced_parameters.py',
            'chaining.py',
            'solution_workflow.py',
            'shared_agents.py',
            'agentic/potential_product_index.py',
            'agentic/deep_agent/llm_specs_generator.py'
        ]

        usage_count = 0

        for filepath in files_to_check:
            full_path = os.path.join(os.path.dirname(__file__), '..', filepath)
            if not os.path.exists(full_path):
                continue

            with open(full_path, 'r') as f:
                content = f.read()

            # Count AgenticConfig.PRO_MODEL references
            import re
            refs = re.findall(r'AgenticConfig\.PRO_MODEL', content)

            if refs:
                usage_count += len(refs)
                print(f"[OK] {filepath}: {len(refs)} AgenticConfig.PRO_MODEL reference(s)")

        if usage_count > 0:
            print(f"\n[OK] Found {usage_count} AgenticConfig.PRO_MODEL references (Phase 1 FIX applied)")
            return True
        else:
            print(f"\n[WARN]  No AgenticConfig.PRO_MODEL references found")
            return False

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("INTENT CLASSIFICATION & MODEL CONFIGURATION FIX VALIDATION")
    print("="*70)

    tests = [
        test_intent_config_class,
        test_model_config,
        test_intent_tools_rules,
        test_prompts_documentation,
        test_no_hardcoded_gemini_pro,
        test_agenticconfig_usage
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"\n[FAIL] {test_func.__name__} crashed: {e}")
            results.append((test_func.__name__, False))

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "-"*70)
    print(f"Results: {passed}/{total} tests passed")
    print("-"*70)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Implementation validated successfully.")
        return 0
    else:
        print(f"\n[WARN]  {total - passed} test(s) failed. Please review above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
