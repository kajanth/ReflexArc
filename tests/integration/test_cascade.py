"""
Integration tests for the full neural cascade flow.

Tests the complete spike processing through all layers:
- RAS (Reticular Activating System) - novelty filtering
- Thalamus - triage and routing decisions  
- Hippocampus - memory storage and context retrieval
- Cerebellum - reflex execution (skills)
- Template Engine - guided AI responses
- Cortex - complex reasoning
- Basal Ganglia - habit reinforcement

These tests verify the bio-inspired neural cascade architecture
processes spikes correctly through each layer with proper cost optimization.
"""

import pytest
import asyncio
import tempfile
import os
import json
import time
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any

# Local imports
from brain_core import NSAOrchestrator
from tests.mocks.mock_provider import MockProvider
from providers.router import ModelRouter
from skill_template_engine import SkillTemplateEngine
from basal_ganglia import BasalGanglia
from memory.hippocampus import Hippocampus
from event_bus import EventBus


class TestCascadeIntegration:
    """Integration tests for the full neural cascade."""
    
    @pytest.fixture
    async def mock_brain(self, temp_db_path):
        """Create a mock NSA brain with test configuration."""
        # Create temporary directories for skills and templates
        self.temp_skills_dir = tempfile.mkdtemp()
        self.temp_templates_dir = os.path.join(self.temp_skills_dir, "templates")
        os.makedirs(self.temp_templates_dir)
        
        # Create a test skill
        test_skill_content = '''
def run(data=None):
    """Test skill for integration testing."""
    return f"Test skill executed with: {data}"
'''
        with open(os.path.join(self.temp_skills_dir, "test_skill.py"), "w") as f:
            f.write(test_skill_content)
        
        # Create a test template
        test_template_content = '''---
name: test_template
model: nano
category: test
description: Test template for integration testing
max_tokens: 100
---

# System Prompt
You are a test template in the NSA system.

# User Prompt
Process this stimulus: {{stimulus}}
Context: {{context}}
Respond with: "Template processed: [stimulus]"
'''
        with open(os.path.join(self.temp_templates_dir, "test_template.md"), "w") as f:
            f.write(test_template_content)
        
        # Create mock provider with predictable responses
        mock_provider = MockProvider()
        
        # Set up triage responses for different scenarios
        mock_provider.set_response("REFLEX:test_skill", "REFLEX:test_skill")
        mock_provider.set_response("TEMPLATE:test_template", "TEMPLATE:test_template") 
        mock_provider.set_response("COMPLEX", "COMPLEX")
        mock_provider.set_response("LOG", "LOG")
        
        # Mock the skills directory
        with patch('os.listdir') as mock_listdir:
            def mock_listdir_side_effect(path):
                if path == 'skills':
                    return ['test_skill.py', '__init__.py']
                elif path == self.temp_skills_dir:
                    return ['test_skill.py']
                else:
                    return os.listdir(path)
            
            mock_listdir.side_effect = mock_listdir_side_effect
            
            # Mock importlib for skill loading
            with patch('importlib.import_module') as mock_import:
                mock_skill_module = MagicMock()
                mock_skill_module.run.return_value = "Test skill executed"
                mock_import.return_value = mock_skill_module
                
                # Mock agent.md file
                with patch('builtins.open', mock_open(read_data="Test agent DNA")):
                    # Create brain with mocked components
                    brain = NSAOrchestrator(db_path=temp_db_path)
                    
                    # Replace router with mock
                    brain.router = ModelRouter()
                    brain.router.providers = {"mock": mock_provider}
                    brain.router._provider_models = {
                        "mock": await mock_provider.get_available_models()
                    }
                    
                    # Mock template engine with test templates
                    with patch('skill_template_engine.TEMPLATES_DIR', self.temp_templates_dir):
                        brain.template_engine = SkillTemplateEngine(brain.router)
                        brain.template_engine._template_cache = {
                            "test_template": {
                                "meta": {
                                    "name": "test_template",
                                    "model": "nano", 
                                    "category": "test",
                                    "description": "Test template",
                                    "max_tokens": 100
                                },
                                "system_prompt": "You are a test template in the NSA system.",
                                "user_prompt": 'Process this stimulus: {{stimulus}}\nContext: {{context}}\nRespond with: "Template processed: [stimulus]"',
                                "filepath": os.path.join(self.temp_templates_dir, "test_template.md")
                            }
                        }
                    
                    yield brain, mock_provider, mock_skill_module
    
    def teardown_method(self):
        """Clean up temporary files."""
        if hasattr(self, 'temp_skills_dir') and os.path.exists(self.temp_skills_dir):
            import shutil
            shutil.rmtree(self.temp_skills_dir)
    
    @pytest.mark.asyncio
    async def test_spike_to_ras_to_thalamus_to_reflex_flow(self, mock_brain):
        """Test complete flow: Spike → RAS → Thalamus → Reflex execution."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up triage to return REFLEX decision
        triage_prompt_pattern = "STIMULUS:"
        mock_provider.responses = {}
        
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            
            # Check if this is a triage call
            if any("STIMULUS:" in msg.get("content", "") for msg in messages):
                return StandardResponse(
                    content="REFLEX:test_skill",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            else:
                return StandardResponse(
                    content="Mock response",
                    model="mock-nano", 
                    usage_tokens=30,
                    cost=0.0005,
                    latency_ms=5.0
                )
        
        brain.router.route = mock_route
        
        # Process a spike that should trigger reflex
        result = await brain.process_spike("system", "Test system alert requiring reflex action")
        
        # Verify the reflex was executed
        assert result == "Test skill executed"
        mock_skill_module.run.assert_called_once()
        
        # Verify habit was reinforced in Basal Ganglia
        habit = brain.basal_ganglia.get_habit_optimization("REFLEX:test_skill")
        assert habit["count"] == 1
    
    @pytest.mark.asyncio
    async def test_spike_to_ras_to_thalamus_to_template_flow(self, mock_brain):
        """Test complete flow: Spike → RAS → Thalamus → Template execution."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up triage to return TEMPLATE decision
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            
            # Check if this is a triage call
            if any("STIMULUS:" in msg.get("content", "") for msg in messages):
                return StandardResponse(
                    content="TEMPLATE:test_template",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            else:
                # Template execution call
                return StandardResponse(
                    content="Template processed: Test system alert",
                    model="mock-nano",
                    usage_tokens=30,
                    cost=0.0005,
                    latency_ms=5.0
                )
        
        brain.router.route = mock_route
        
        # Process a spike that should trigger template
        result = await brain.process_spike("system", "Test system alert requiring template processing")
        
        # Verify the template was executed
        assert "Template processed" in result
        
        # Verify habit was reinforced in Basal Ganglia
        habit = brain.basal_ganglia.get_habit_optimization("TEMPLATE:test_template")
        assert habit["count"] == 1
    
    @pytest.mark.asyncio
    async def test_spike_to_ras_to_thalamus_to_cortex_flow(self, mock_brain):
        """Test complete flow: Spike → RAS → Thalamus → Cortex reasoning."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up triage to return COMPLEX decision
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            
            # Check if this is a triage call
            if any("STIMULUS:" in msg.get("content", "") for msg in messages):
                return StandardResponse(
                    content="COMPLEX",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            elif tier == "cortex":
                # Cortex reasoning call
                return StandardResponse(
                    content="Complex analysis: This requires detailed investigation and custom solution.",
                    model="mock-cortex",
                    usage_tokens=200,
                    cost=0.02,
                    latency_ms=100.0
                )
            else:
                return StandardResponse(
                    content="Mock response",
                    model="mock-nano",
                    usage_tokens=30,
                    cost=0.0005,
                    latency_ms=5.0
                )
        
        brain.router.route = mock_route
        
        # Process a spike that should trigger cortex
        result = await brain.process_spike("system", "Complex novel security threat requiring analysis")
        
        # Verify cortex reasoning was executed
        assert "Complex analysis" in result
        assert "detailed investigation" in result
    
    @pytest.mark.asyncio
    async def test_ras_habituation_filtering(self, mock_brain):
        """Test that RAS filters out habituated (similar) spikes."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Process the same spike multiple times
        first_result = await brain.process_spike("system", "Repeated system message")
        
        # Second identical spike should be filtered by RAS
        second_result = await brain.process_spike("system", "Repeated system message")
        
        # First spike should be processed
        assert first_result is not None
        
        # Second spike should be filtered (returns None)
        assert second_result is None
    
    @pytest.mark.asyncio
    async def test_hippocampus_memory_integration(self, mock_brain):
        """Test that Hippocampus stores and retrieves context during cascade."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Store some initial memories
        await brain.memory.store_memory("system", "Previous security incident with malware")
        await brain.memory.store_memory("system", "Network intrusion detected last week")
        
        # Set up triage to return LOG (so we can verify memory was accessed)
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            
            # Verify that context was retrieved and included in triage
            triage_content = messages[-1]["content"] if messages else ""
            assert "CONTEXT:" in triage_content
            
            return StandardResponse(
                content="LOG",
                model="mock-nano",
                usage_tokens=50,
                cost=0.001,
                latency_ms=10.0
            )
        
        brain.router.route = mock_route
        
        # Process a security-related spike
        result = await brain.process_spike("security", "New security alert detected")
        
        # Verify memory was stored
        count = await brain.memory.get_memory_count()
        assert count == 3  # 2 initial + 1 new
        
        # Verify result
        assert result == "Log recorded."
    
    @pytest.mark.asyncio
    async def test_basal_ganglia_habit_optimization(self, mock_brain):
        """Test that Basal Ganglia optimizes repeated patterns."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up triage to consistently return REFLEX
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            return StandardResponse(
                content="REFLEX:test_skill",
                model="mock-nano",
                usage_tokens=50,
                cost=0.001,
                latency_ms=10.0
            )
        
        brain.router.route = mock_route
        
        # Execute the same pattern multiple times
        pattern_id = "REFLEX:test_skill"
        
        for i in range(5):
            await brain.process_spike("system", f"Test alert {i}")
        
        # Verify habit was reinforced and optimized
        habit = brain.basal_ganglia.get_habit_optimization(pattern_id)
        assert habit["count"] == 5
        assert habit["latency_multiplier"] < 1.0  # Should be optimized
        assert habit["cost_multiplier"] < 1.0     # Should be optimized
        
        # Verify it's considered habitual
        assert brain.basal_ganglia.is_habitual(pattern_id, threshold=3)
    
    @pytest.mark.asyncio
    async def test_bypass_ras_for_special_spikes(self, mock_brain):
        """Test that special spikes (GOAL_INVESTIGATION, PHANTOM_SPIKE, HEARTBEAT) bypass RAS."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up mock for homeostasis skill
        with patch('importlib.import_module') as mock_import:
            mock_homeostasis = MagicMock()
            mock_homeostasis.run.return_value = 75  # Healthy system
            
            def import_side_effect(module_name):
                if module_name == "skills.homeostasis":
                    return mock_homeostasis
                else:
                    return mock_skill_module
            
            mock_import.side_effect = import_side_effect
            
            # Test HEARTBEAT bypass
            result = await brain.process_spike("internal", "HEARTBEAT_SIGNAL periodic check")
            assert "Heartbeat: System Healthy" in result
            mock_homeostasis.run.assert_called_once()
        
        # Test GOAL_INVESTIGATION bypass
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            return StandardResponse(
                content="LOG",
                model="mock-nano",
                usage_tokens=50,
                cost=0.001,
                latency_ms=10.0
            )
        
        brain.router.route = mock_route
        
        result = await brain.process_spike("internal", "GOAL_INVESTIGATION checking system status")
        assert result == "Log recorded."
        
        # Test PHANTOM_SPIKE bypass
        result = await brain.process_spike("predictive", "PHANTOM_SPIKE potential future threat")
        assert result == "Log recorded."
    
    @pytest.mark.asyncio
    async def test_error_handling_and_escalation(self, mock_brain):
        """Test error handling and escalation in the cascade."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up triage to return REFLEX, but skill will fail
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            
            if any("STIMULUS:" in msg.get("content", "") for msg in messages):
                return StandardResponse(
                    content="REFLEX:nonexistent_skill",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            elif tier == "cortex":
                # Should escalate to cortex after skill failure
                return StandardResponse(
                    content="Cortex handling failed reflex escalation",
                    model="mock-cortex",
                    usage_tokens=200,
                    cost=0.02,
                    latency_ms=100.0
                )
            else:
                return StandardResponse(
                    content="Mock response",
                    model="mock-nano",
                    usage_tokens=30,
                    cost=0.0005,
                    latency_ms=5.0
                )
        
        brain.router.route = mock_route
        
        # Process spike that will cause skill failure and escalation
        result = await brain.process_spike("system", "Test alert for nonexistent skill")
        
        # Should escalate to cortex after reflex failure
        assert "Cortex handling failed reflex escalation" in result
    
    @pytest.mark.asyncio
    async def test_event_bus_integration(self, mock_brain):
        """Test that cascade publishes appropriate events to the event bus."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Capture events published to event bus
        published_events = []
        
        def mock_publish(event_type, data):
            published_events.append((event_type, data))
        
        with patch('event_bus.publish', side_effect=mock_publish):
            # Set up triage to return REFLEX
            def mock_route(tier, messages, **kwargs):
                from providers.base import StandardResponse
                return StandardResponse(
                    content="REFLEX:test_skill",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            
            brain.router.route = mock_route
            
            # Process a spike
            await brain.process_spike("system", "Test system alert")
            
            # Verify expected events were published
            event_types = [event[0] for event in published_events]
            
            assert "spike" in event_types
            assert "ras_filter" in event_types  
            assert "decision" in event_types
            assert "reflex_exec" in event_types
            assert "reinforce_spike" in event_types
    
    @pytest.mark.asyncio
    async def test_concurrent_spike_processing(self, mock_brain):
        """Test that multiple spikes can be processed concurrently."""
        brain, mock_provider, mock_skill_module = mock_brain
        
        # Set up triage to return different decisions for different spikes
        def mock_route(tier, messages, **kwargs):
            from providers.base import StandardResponse
            
            content = messages[-1]["content"] if messages else ""
            
            if "reflex_spike" in content:
                return StandardResponse(
                    content="REFLEX:test_skill",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            elif "template_spike" in content:
                return StandardResponse(
                    content="TEMPLATE:test_template", 
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            elif tier == "nano":
                return StandardResponse(
                    content="LOG",
                    model="mock-nano",
                    usage_tokens=50,
                    cost=0.001,
                    latency_ms=10.0
                )
            else:
                return StandardResponse(
                    content="Template processed: concurrent test",
                    model="mock-nano",
                    usage_tokens=30,
                    cost=0.0005,
                    latency_ms=5.0
                )
        
        brain.router.route = mock_route
        
        # Process multiple spikes concurrently
        tasks = [
            brain.process_spike("system", "reflex_spike alert 1"),
            brain.process_spike("system", "template_spike alert 2"), 
            brain.process_spike("system", "log_spike alert 3"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all spikes were processed without exceptions
        for result in results:
            assert not isinstance(result, Exception)
        
        # Verify different processing paths were taken
        assert len([r for r in results if r and "Test skill executed" in str(r)]) >= 1
        assert len([r for r in results if r and "Template processed" in str(r)]) >= 1
        assert len([r for r in results if r == "Log recorded."]) >= 1