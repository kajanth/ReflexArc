"""
🧠 NSA Skill Template Engine
Layer 4.5 — Guided AI Reasoning

Bridges the gap between $0 Python reflexes (Layer 5) and expensive
raw Cortex reasoning (Layer 4). Templates are markdown files with
YAML frontmatter that define structured prompts, model selection,
and output format.

Now uses the ModelRouter for provider-agnostic execution.
"""

import os
import re
import json
import time


TEMPLATES_DIR = "skills/templates"


class SkillTemplateEngine:
    def __init__(self, router):
        """
        Args:
            router: ModelRouter instance for provider-agnostic AI calls.
        """
        self.router = router
        self._template_cache = {}
        self._load_templates()

    def _load_templates(self):
        """Discover and parse all .md templates in the templates directory."""
        self._template_cache.clear()

        if not os.path.isdir(TEMPLATES_DIR):
            return

        for filename in os.listdir(TEMPLATES_DIR):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(TEMPLATES_DIR, filename)
            template = self._parse_template(filepath)
            if template:
                name = template["meta"].get("name", filename.replace(".md", ""))
                self._template_cache[name] = template

    def _parse_template(self, filepath):
        """
        Parse a markdown template into metadata + prompts.

        Returns:
            {
                "meta": {name, model, category, description, output_format, max_tokens},
                "system_prompt": str,
                "user_prompt": str,
                "filepath": str,
            }
        """
        try:
            with open(filepath, "r") as f:
                content = f.read()
        except IOError:
            return None

        # Extract YAML frontmatter between --- delimiters
        meta = {}
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            body = content[frontmatter_match.end():]

            # Simple YAML parser (no external dependency)
            for line in frontmatter.strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value.isdigit():
                        value = int(value)
                    elif value.replace(".", "", 1).isdigit():
                        value = float(value)
                    meta[key] = value
        else:
            body = content

        # Extract system prompt and user prompt sections
        system_prompt = ""
        user_prompt = ""

        sections = re.split(r'^#+\s+', body, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue

            lower = section.lower()
            if lower.startswith("system prompt") or lower.startswith("system"):
                lines = section.split("\n", 1)
                system_prompt = lines[1].strip() if len(lines) > 1 else ""
            elif lower.startswith("user prompt") or lower.startswith("user") or lower.startswith("prompt"):
                lines = section.split("\n", 1)
                user_prompt = lines[1].strip() if len(lines) > 1 else ""

        # Fallback: if no sections found, treat entire body as user prompt
        if not user_prompt and not system_prompt:
            user_prompt = body.strip()

        return {
            "meta": meta,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "filepath": filepath,
        }

    def get_available_templates(self):
        """Return list of available template names with descriptions."""
        return {
            name: {
                "description": t["meta"].get("description", ""),
                "model": t["meta"].get("model", "nano"),
                "category": t["meta"].get("category", "general"),
            }
            for name, t in self._template_cache.items()
        }

    def get_template_names(self):
        """Return just the template names for triage prompt."""
        return list(self._template_cache.keys())

    def execute(self, template_name, variables=None):
        """
        Execute an AI skill template via the ModelRouter.

        Args:
            template_name: Name of the template to execute.
            variables: Dict of variables to substitute into the prompt.

        Returns:
            (str, StandardResponse): The AI response text and full response object.
        """
        # Reload templates to pick up any new ones
        self._load_templates()

        if template_name not in self._template_cache:
            return f"Template '{template_name}' not found. Available: {list(self._template_cache.keys())}", None

        template = self._template_cache[template_name]
        meta = template["meta"]
        variables = variables or {}

        # Substitute variables in prompts
        system_prompt = self._substitute(template["system_prompt"], variables)
        user_prompt = self._substitute(template["user_prompt"], variables)

        # Determine model tier (maps to router tier)
        tier = meta.get("model", "nano")

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        max_tokens = meta.get("max_tokens", 200)

        try:
            # Route through the ModelRouter (provider-agnostic)
            response = self.router.route(
                tier=tier,
                messages=messages,
                max_tokens=max_tokens,
            )

            result = response.content

            # Format output based on output_format
            output_format = meta.get("output_format", "text")
            if output_format == "json":
                try:
                    result = json.dumps(json.loads(result), indent=2)
                except json.JSONDecodeError:
                    pass

            print(
                f"[Template:{template_name}] "
                f"Provider: {response.provider} | Model: {response.model} | "
                f"Tokens: {response.prompt_tokens}+{response.completion_tokens} | "
                f"Cost: ${response.cost:.6f}"
            )

            return result, response

        except Exception as e:
            return f"Template execution failed: {e}", None

    def _substitute(self, text, variables):
        """Replace {{variable}} placeholders with actual values."""
        def replace_match(match):
            key = match.group(1).strip()
            return str(variables.get(key, f"[MISSING: {key}]"))

        return re.sub(r'\{\{(\w+)\}\}', replace_match, text)

    def reload(self):
        """Force reload all templates from disk."""
        self._load_templates()
