"""
🧠 ReflexArc Evolution Swarm — ADK Agent Package

This package exposes the Evolution Swarm as a discoverable ADK agent.
The swarm is composed of three specialized LlmAgent personas:
  - CapabilityEnhancer: Proposes new features
  - CodeFixer: Resolves bugs from the error task backlog
  - SecurityAuditor: Identifies vulnerabilities
"""
from adk_agents.evolution_swarm.agent import root_agent
