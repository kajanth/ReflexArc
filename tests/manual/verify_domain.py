#!/usr/bin/env python3
"""
🧪 NSA Domain & Skill Verifier
A static analysis tool to validate ReflexArc domains, configs, skills, and templates.

Usage:
    python3 verify_domain.py [config_path]
    # Default uses config/brain.yaml or NSA_BRAIN_CONFIG
"""

import os
import sys
import ast
from plugin_loader import BrainConfig, load_class, load_function, BUILTIN_MEASURERS

# ANSI Colors
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_RESET = "\033[0m"

errors = 0
warnings = 0

def log_pass(msg):
    print(f"  {C_GREEN}✓{C_RESET} {msg}")

def log_fail(msg):
    global errors
    errors += 1
    print(f"  {C_RED}✗{C_RESET} {msg}")

def log_warn(msg):
    global warnings
    warnings += 1
    print(f"  {C_YELLOW}!{C_RESET} {msg}")

def verify_config_schema(config):
    """Ensure basic fields exist in the config."""
    print(f"\n{C_BLUE}─── Validating Config Schema ───{C_RESET}")
    c = config.config
    brain = c.get("brain", {})
    if not brain:
        log_fail("Missing 'brain' section in config")
    else:
        log_pass("Found 'brain' section")
        if "name" not in brain: log_fail("Missing 'brain.name'")
        else: log_pass(f"Name: {brain['name']}")

    if "sensors" not in c: log_warn("No 'sensors' defined")
    else: log_pass(f"Sensors defined: {len(c['sensors'])}")

    if "predictions" not in c: log_warn("No 'predictions' defined")
    else: log_pass(f"Predictions defined: {len(c['predictions'])}")

def verify_sensors(config):
    """Verify that every external sensor module can be imported statically."""
    print(f"\n{C_BLUE}─── Verifying Sensor Imports ───{C_RESET}")
    sensors = config.config.get("sensors", [])
    
    if not sensors:
        log_warn("Skip: No sensors defined")
        return

    for s in sensors:
        name = s.get("name", "Unknown")
        if "source" in s:
            log_pass(f"Internal sensor '{name}': {s['source']}")
            continue
        
        module_path = s.get("module")
        if not module_path:
            log_fail(f"Sensor '{name}': No 'module' specified")
            continue
            
        try:
            load_class(module_path)
            log_pass(f"External sensor '{name}': {module_path} is importable")
        except Exception as e:
            log_fail(f"External sensor '{name}': Failed to load {module_path} — {type(e).__name__}: {str(e)}")

def verify_measurers(config):
    """Verify prediction and custom measurers can be imported statically."""
    print(f"\n{C_BLUE}─── Verifying Measurer Imports ───{C_RESET}")
    predictions = config.config.get("predictions", [])
    customs = config.config.get("custom_measurers", [])
    
    # Combine all measurers that need loading
    paths = set()
    for p in predictions:
        if "measurer" in p: paths.add(p["measurer"])
    for c in customs:
        if "module" in c: paths.add(c["module"])

    if not paths:
        log_warn("Skip: No predictions or custom measurers defined")
        return

    for path in paths:
        if path in BUILTIN_MEASURERS:
            log_pass(f"Built-in measurer '{path}' is valid")
            continue
        try:
            load_function(path)
            log_pass(f"External measurer '{path}' is importable")
        except Exception as e:
            log_fail(f"External measurer '{path}': Failed to load — {type(e).__name__}: {str(e)}")

def verify_skills():
    """Statically analyze Python skills in skills/ directory for 'def run()' signature."""
    print(f"\n{C_BLUE}─── Auditing Cerebellum Skills (.py) ───{C_RESET}")
    skills_dir = "skills"
    if not os.path.isdir(skills_dir):
        log_fail("Missing 'skills/' directory")
        return
        
    py_files = [f for f in os.listdir(skills_dir) if f.endswith(".py") and f != "__init__.py"]
    if not py_files:
        log_warn("No Python skills found")
        return

    for f in py_files:
        path = os.path.join(skills_dir, f)
        try:
            c = open(path, "r", encoding="utf-8").read()
            tree = ast.parse(c, filename=path)
            
            # Check for def run()
            has_run = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "run":
                    has_run = True
                    break
            
            if has_run:
                log_pass(f"Skill '{f}': valid AST and 'run' functional entrypoint")
            else:
                log_fail(f"Skill '{f}': Missing 'def run(data=None):' entrypoint")
                
        except SyntaxError as e:
            log_fail(f"Skill '{f}': SyntaxError at line {e.lineno}")
        except Exception as e:
            log_fail(f"Skill '{f}': Error analyzing — {str(e)}")

def verify_templates():
    """Read skills/templates/*.md and verify YAML frontmatter variables."""
    print(f"\n{C_BLUE}─── Auditing AI Templates (.md) ───{C_RESET}")
    tpl_dir = os.path.join("skills", "templates")
    if not os.path.isdir(tpl_dir):
        log_warn("Missing 'skills/templates/' directory (or no templates)")
        return
        
    md_files = [f for f in os.listdir(tpl_dir) if f.endswith(".md")]
    if not md_files:
        log_warn("No markdown templates found")
        return

    for f in md_files:
        path = os.path.join(tpl_dir, f)
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
            
        if not content.startswith("---"):
            log_fail(f"Template '{f}': Missing YAML frontmatter (needs '---' at start)")
            continue
            
        # Very simple validation
        parts = content.split("---")
        if len(parts) < 3:
            log_fail(f"Template '{f}': Malformed YAML frontmatter")
            continue
            
        frontmatter = parts[1]
        required_keys = ["name", "model", "category"]
        missing_keys = [k for k in required_keys if f"{k}:" not in frontmatter]
        
        if missing_keys:
            log_fail(f"Template '{f}': Missing keys in frontmatter {missing_keys}")
        else:
            log_pass(f"Template '{f}': Frontmatter valid")

def main():
    print(f"{C_BLUE}======================================{C_RESET}")
    print(f"{C_BLUE}  SYSTEM VERIFICATION TOOL            {C_RESET}")
    print(f"{C_BLUE}======================================{C_RESET}")
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = BrainConfig(config_path)
    
    print(f"\nTesting profile: {C_GREEN}{config.name}{C_RESET} ({config.config_path})")
    
    verify_config_schema(config)
    verify_sensors(config)
    verify_measurers(config)
    verify_skills()
    verify_templates()
    
    print(f"\n{C_BLUE}─── Summary ───{C_RESET}")
    if errors == 0:
        print(f"  {C_GREEN}SUCCESS{C_RESET}: 0 Errors, {warnings} Warnings")
        sys.exit(0)
    else:
        print(f"  {C_RED}FAILED{C_RESET}: {errors} Errors, {warnings} Warnings")
        print("\n  Tip: If importing plugins failed, it's expected if you haven't implemented")
        print("  the hypothetical plugins for that domain yet. You must write the actual Python")
        print("  code in your project before the brain can load them.")
        sys.exit(1)

if __name__ == "__main__":
    main()
