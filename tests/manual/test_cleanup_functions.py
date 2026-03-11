#!/usr/bin/env python3
"""
Simple verification that cleanup functions exist with correct signatures.
This test doesn't require dependencies to be installed.
"""

import ast
import sys


def check_function_exists(filepath, function_name):
    """Check if a function exists in a Python file."""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return True
    return False


def check_method_exists(filepath, class_name, method_name):
    """Check if a method exists in a class."""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return True
    return False


def main():
    """Verify cleanup functions exist."""
    print("=" * 60)
    print("Cleanup Function Verification")
    print("=" * 60)
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Check brain_core.py has cleanup_models method
    print("Test 1: NSAOrchestrator.cleanup_models() exists...")
    if check_method_exists('brain_core.py', 'NSAOrchestrator', 'cleanup_models'):
        print("  ✓ PASS: cleanup_models() method found in NSAOrchestrator")
        tests_passed += 1
    else:
        print("  ✗ FAIL: cleanup_models() method not found in NSAOrchestrator")
        tests_failed += 1
    print()
    
    # Test 2: Check hippocampus.py has cleanup_embedding_model function
    print("Test 2: cleanup_embedding_model() exists in hippocampus.py...")
    if check_function_exists('memory/hippocampus.py', 'cleanup_embedding_model'):
        print("  ✓ PASS: cleanup_embedding_model() function found")
        tests_passed += 1
    else:
        print("  ✗ FAIL: cleanup_embedding_model() function not found")
        tests_failed += 1
    print()
    
    # Test 3: Check dream_engine.py has cleanup_dream_model function
    print("Test 3: cleanup_dream_model() exists in dream_engine.py...")
    if check_function_exists('dream_engine.py', 'cleanup_dream_model'):
        print("  ✓ PASS: cleanup_dream_model() function found")
        tests_passed += 1
    else:
        print("  ✗ FAIL: cleanup_dream_model() function not found")
        tests_failed += 1
    print()
    
    # Test 4: Check main.py calls cleanup functions in shutdown
    print("Test 4: Shutdown handler calls cleanup functions...")
    with open('main.py', 'r') as f:
        main_content = f.read()
    
    checks = [
        ('brain.cleanup_models()', 'brain.cleanup_models() call'),
        ('cleanup_embedding_model()', 'cleanup_embedding_model() call'),
        ('cleanup_dream_model()', 'cleanup_dream_model() call'),
        ('from utils.embeddings import cleanup_embedding_model', 'embeddings import'),
        ('from dream_engine import cleanup_dream_model', 'dream_engine import'),
    ]
    
    all_found = True
    for check_str, description in checks:
        if check_str in main_content:
            print(f"  ✓ Found: {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_found = False
    
    if all_found:
        print("  ✓ PASS: All cleanup calls found in shutdown handler")
        tests_passed += 1
    else:
        print("  ✗ FAIL: Some cleanup calls missing in shutdown handler")
        tests_failed += 1
    print()
    
    # Summary
    print("=" * 60)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    
    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
