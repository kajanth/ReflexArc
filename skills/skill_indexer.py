"""
⚡ Metabolic Skill: Skill Indexer
Category: Resource & Cost Optimization
Trigger: Filesystem sensor (new skill created) / Sleep Cycle

Scans all skills in /skills/ and generates a structured manifest
(memory/skill_index.json) with descriptions, categories, and match
keywords. Helps the Thalamus pick the right reflex faster — like
building a "lookup table" for muscle memory.
"""

import os
import ast
import json
import time
import re


SKILL_DIR = "skills"
INDEX_FILE = "memory/skill_index.json"

# Category detection heuristics
CATEGORY_KEYWORDS = {
    "immune": ["quarantine", "firewall", "forensic", "security", "threat", "block"],
    "autonomic": ["cleanup", "homeostasis", "restart", "disk", "pressure", "system_check"],
    "endocrine": ["digest", "notify", "alert", "schedule", "cron"],
    "motor": ["file", "shell", "executor", "api", "organizer", "caller"],
    "metabolic": ["token", "budget", "indexer", "defrag", "cognitive", "cost"],
}


def run(data=None):
    """
    Index all skill files and generate a structured manifest.

    data: Optional, unused.
    """
    skills = {}

    for filename in sorted(os.listdir(SKILL_DIR)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue

        skill_name = filename.replace(".py", "")
        filepath = os.path.join(SKILL_DIR, filename)

        info = _analyze_skill(filepath, skill_name)
        skills[skill_name] = info

    # Build the index
    index = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_skills": len(skills),
        "skills": skills,
        "by_category": _group_by_category(skills),
    }

    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

    # Summary
    categories = index["by_category"]
    cat_summary = ", ".join(f"{cat}: {len(names)}" for cat, names in categories.items())

    result = (
        f"SKILL INDEX: {len(skills)} skills indexed to {INDEX_FILE}. "
        f"Categories: {cat_summary}"
    )
    print(f"[Cerebellum]: {result}")
    return result


def _analyze_skill(filepath, skill_name):
    """Extract metadata from a skill file via AST analysis."""
    info = {
        "name": skill_name,
        "file": filepath,
        "description": "",
        "category": "uncategorized",
        "has_run": False,
        "keywords": [],
        "lines": 0,
    }

    try:
        with open(filepath, "r") as f:
            source = f.read()

        info["lines"] = source.count("\n") + 1

        # Parse AST
        tree = ast.parse(source, filename=filepath)

        # Extract module docstring
        docstring = ast.get_docstring(tree)
        if docstring:
            info["description"] = docstring.split("\n")[0].strip()

            # Detect category from docstring
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in docstring.lower() for kw in keywords):
                    info["category"] = cat
                    break

        # Check for run() function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                info["has_run"] = True
                # Extract run() docstring for keywords
                run_doc = ast.get_docstring(node)
                if run_doc:
                    info["keywords"].extend(_extract_keywords(run_doc))
                break

        # Fallback category detection from filename
        if info["category"] == "uncategorized":
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in skill_name.lower() for kw in keywords):
                    info["category"] = cat
                    break

        # Extract keywords from the filename
        info["keywords"].extend(skill_name.replace("_", " ").split())

    except (SyntaxError, IOError) as e:
        info["description"] = f"Error analyzing: {e}"

    return info


def _extract_keywords(text):
    """Extract meaningful keywords from text."""
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    stopwords = {"the", "and", "for", "with", "from", "this", "that", "str", "none",
                 "optional", "data", "def", "run", "return", "self"}
    return list(set(w for w in words if w not in stopwords))[:10]


def _group_by_category(skills):
    """Group skill names by category."""
    groups = {}
    for name, info in skills.items():
        cat = info.get("category", "uncategorized")
        groups.setdefault(cat, []).append(name)
    return groups
