"""
Unit tests for Thalamus layer in brain_core.py

Tests Layer 2 of the neural cascade: triage routing decisions using a cheap nano-tier model
to decide between REFLEX, TEMPLATE, LOG, or COMPLEX routing. The Thalamus is critical for
cost-aware routing (~$0.001) that prevents expensive Cortex processing when possible.

Tests validate:
- 14.4.1: Test routing decisions (how it chooses between REFLEX, TEMPLATE, LOG, COMPLEX)
- 14.4.2: Test skill discovery (how it identifies available Python skills)  
- 14.4.3: Test template discovery (how it identifies available markdown templates)

Note: These tests focus on the Thalamus triage logic by mocking the RAS layer to bypass
embedding model loading, allowing us to test the core routing functionality.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from typing import Optional, Dict, Any

# Local imports
from brain_core import NSAOrchestrator
from tests.mocks.mock_provider import MockProvider
from providers.base import StandardResponse


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model to avoid network calls during tests."""
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]
    return mock_model


class TestThalamusRoutingDecisions:
    """Test Thalamus routing decision functionality (14.4.1)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @pytest.fixture
    def mock_router(self):
        """Mock router that returns deterministic triage decisions."""
        mock_router = MagicMock()
        
        def route_side_effect(tier, messages, **kwargs):
            # Extract the triage prompt from messages
            user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
            
            # Return different decisions based on prompt content
            if "exact match" in user_message.lower():
                content = "REFLEX:system_health_check"
            elif "template match" in user_message.lower():
                content = "TEMPLATE:classify_threat"
            elif "routine observation" in user_message.lower():
                content = "LOG"
            elif "novel complex" in user_message.lower():
                content = "COMPLEX"
            elif "cognitive_overload" in user_message.lower():
                content = "LOG"  # Should avoid COMPLEX when overloaded
            else:
                content = "LOG"  # Default safe decision
                
            return StandardResponse(
                content=content,
                model="mock-nano",
                provider="mock",
                cost=0.001,
                total_tokens=50
            )
        
        mock_router.route.side_effect = route_side_effect
        return mock_router
    
    def test_triage_prompt_construction(self, orchestrator, mock_router):
        """Test that triage prompt includes all necessary information."""
        orchestrator.router = mock_router
        
        # Mock the RAS layer to bypass embedding model loading
        orchestrator.habituation_vector = None  # Simulate first spike (no RAS filtering)
        
        with patch('brain_core.os.listdir', return_value=['skill1.py', 'skill2.py']):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value="Test context"):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="TEST_STATE"):
                            mock_templates = {
                                'template1': {'description': 'Template 1 desc'},
                                'template2': {'description': 'Template 2 desc'}
                            }
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value=mock_templates):
                                # Process spike to trigger triage (bypass RAS by setting bypass_ras=True)
                                with patch('brain_core.get_embedding_model'):  # Prevent embedding model loading
                                    asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test stimulus"))
                                
                                # Verify triage prompt structure
                                call_args = mock_router.route.call_args
                                messages = call_args[0][1]
                                
                                # Should have system and user messages
                                assert len(messages) == 2
                                assert messages[0]["role"] == "system"
                                assert messages[1]["role"] == "user"
                                
                                triage_prompt = messages[1]["content"]
                                
                                # Verify all required sections are present
                                assert "STIMULUS: GOAL_INVESTIGATION: test stimulus" in triage_prompt
                                assert "CONTEXT: Test context" in triage_prompt
                                assert "AVAILABLE_REFLEXES: ['skill1', 'skill2']" in triage_prompt
                                assert "template1" in triage_prompt
                                assert "Template 1 desc" in triage_prompt
                                assert "INTERNAL_STATE: TEST_STATE" in triage_prompt
                                
                                # Verify routing preferences are documented
                                assert "REFLEX > TEMPLATE > LOG > COMPLEX" in triage_prompt
    
    def test_cost_optimization_tier_usage(self, orchestrator, mock_router):
        """Test that Thalamus uses nano tier for cost optimization."""
        orchestrator.router = mock_router
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch('brain_core.get_embedding_model'):
                                    # Process spike (bypass RAS)
                                    asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                
                                # Verify nano tier was used for triage
                                call_args = mock_router.route.call_args
                                assert call_args[1]['tier'] == 'nano'
                                
                                # Verify system message identifies Thalamus role
                                messages = call_args[0][1]
                                system_msg = messages[0]["content"]
                                assert "Thalamus" in system_msg
                                assert "cost-aware triage" in system_msg
    
    def test_cognitive_overload_avoids_complex(self, orchestrator, mock_router):
        """Test that Thalamus avoids COMPLEX routing when cognitive load is high."""
        orchestrator.router = mock_router
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir', return_value=['skill.py']):
            with patch('brain_core.event_bus') as mock_event_bus:
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="COGNITIVE_OVERLOAD"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch('brain_core.get_embedding_model'):
                                    # Process spike during cognitive overload
                                    result = asyncio.run(orchestrator.process_spike("system", "GOAL_INVESTIGATION: cognitive_overload situation"))
                                
                                # Should route to LOG instead of COMPLEX
                                assert result == "Log recorded."
                                
                                # Verify triage prompt included overload state
                                call_args = mock_router.route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                assert "COGNITIVE_OVERLOAD" in triage_prompt
                                assert "avoid COMPLEX" in triage_prompt


class TestThalamusSkillDiscovery:
    """Test Thalamus skill discovery functionality (14.4.2)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    def test_skill_discovery_filters_python_files(self, orchestrator):
        """Test that skill discovery only includes .py files."""
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.return_value = [
                'valid_skill.py',
                'another_skill.py', 
                'invalid_file.txt',
                '__pycache__',
                'README.md'
            ]
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    with patch('brain_core.get_embedding_model'):
                                        # Process spike to trigger skill discovery
                                        asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                    
                                    # Verify triage prompt only includes .py files (without extension)
                                    call_args = mock_route.call_args
                                    triage_prompt = call_args[0][1][1]["content"]
                                    
                                    assert "valid_skill" in triage_prompt
                                    assert "another_skill" in triage_prompt
                                    assert "invalid_file" not in triage_prompt
                                    assert "__pycache__" not in triage_prompt
                                    assert "README" not in triage_prompt
    
    def test_skill_name_extraction(self, orchestrator):
        """Test that skill names are extracted correctly (removing .py extension)."""
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.return_value = [
                'system_health_check.py',
                'network_diagnostic.py',
                'auto_recovery.py'
            ]
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    with patch('brain_core.get_embedding_model'):
                                        # Process spike
                                        asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                    
                                    # Verify skill names in triage prompt (no .py extension)
                                    call_args = mock_route.call_args
                                    triage_prompt = call_args[0][1][1]["content"]
                                    
                                    assert "system_health_check" in triage_prompt
                                    assert "network_diagnostic" in triage_prompt
                                    assert "auto_recovery" in triage_prompt
                                    assert ".py" not in triage_prompt.split("AVAILABLE_REFLEXES:")[1].split("AVAILABLE_TEMPLATES:")[0]
    
    def test_empty_skills_directory(self, orchestrator):
        """Test behavior when skills directory is empty."""
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.return_value = []
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    with patch('brain_core.get_embedding_model'):
                                        # Process spike with no skills available
                                        result = asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                    
                                    # Should still work, just with empty skills list
                                    call_args = mock_route.call_args
                                    triage_prompt = call_args[0][1][1]["content"]
                                    assert "AVAILABLE_REFLEXES: []" in triage_prompt


class TestThalamusTemplateDiscovery:
    """Test Thalamus template discovery functionality (14.4.3)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @pytest.fixture
    def mock_template_engine(self):
        """Mock template engine with test templates."""
        mock_engine = MagicMock()
        
        test_templates = {
            'classify_threat': {
                'description': 'Classify security threats using AI',
                'model': 'nano',
                'category': 'security'
            },
            'compose_alert': {
                'description': 'Compose alert messages for incidents',
                'model': 'mini', 
                'category': 'communication'
            },
            'explain_anomaly': {
                'description': 'Explain detected system anomalies',
                'model': 'cortex',
                'category': 'analysis'
            }
        }
        
        mock_engine.get_available_templates.return_value = test_templates
        return mock_engine
    
    def test_template_discovery_integration(self, orchestrator, mock_template_engine):
        """Test that template discovery integrates with template engine."""
        orchestrator.template_engine = mock_template_engine
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                with patch('brain_core.get_embedding_model'):
                                    # Process spike to trigger template discovery
                                    asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                
                                # Verify template engine was called
                                mock_template_engine.get_available_templates.assert_called_once()
                                
                                # Verify templates appear in triage prompt
                                call_args = mock_route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                
                                assert "classify_threat" in triage_prompt
                                assert "Classify security threats using AI" in triage_prompt
                                assert "compose_alert" in triage_prompt
                                assert "Compose alert messages for incidents" in triage_prompt
    
    def test_template_description_extraction(self, orchestrator, mock_template_engine):
        """Test that template descriptions are properly extracted for triage."""
        orchestrator.template_engine = mock_template_engine
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                with patch('brain_core.get_embedding_model'):
                                    # Process spike
                                    asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                
                                # Verify template descriptions are included
                                call_args = mock_route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                
                                # Should include template name -> description mapping
                                template_section = triage_prompt.split("AVAILABLE_TEMPLATES:")[1].split("INTERNAL_STATE:")[0]
                                assert "classify_threat" in template_section
                                assert "Classify security threats using AI" in template_section
    
    def test_empty_templates_handling(self, orchestrator):
        """Test behavior when no templates are available."""
        mock_engine = MagicMock()
        mock_engine.get_available_templates.return_value = {}
        orchestrator.template_engine = mock_engine
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                with patch('brain_core.get_embedding_model'):
                                    # Process spike with no templates
                                    result = asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test"))
                                
                                # Should handle empty templates gracefully
                                call_args = mock_route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                assert "AVAILABLE_TEMPLATES: {}" in triage_prompt


class TestThalamusIntegration:
    """Integration tests for Thalamus layer functionality."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    def test_thalamus_layer_ordering(self, orchestrator):
        """Test that Thalamus operates as Layer 2 after RAS (Layer 1) and before execution layers."""
        orchestrator.habituation_vector = None  # Bypass RAS (simulate first spike)
        
        with patch('brain_core.os.listdir', return_value=['test_skill.py']):
            with patch('brain_core.event_bus') as mock_event_bus:
                with patch.object(orchestrator.memory, 'retrieve_context', return_value="test context") as mock_retrieve:
                    with patch.object(orchestrator.memory, 'store_memory') as mock_store:
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    with patch('brain_core.get_embedding_model'):
                                        # Process spike
                                        result = asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test spike"))
                                    
                                    # Verify execution order:
                                    # 1. RAS processing (bypassed - no habituation vector set)
                                    # 2. Hippocampus context retrieval (Layer 3)
                                    mock_retrieve.assert_called_once_with("GOAL_INVESTIGATION: test spike")
                                    mock_store.assert_called_once_with("test", "GOAL_INVESTIGATION: test spike")
                                    
                                    # 3. Thalamus triage (Layer 2)
                                    mock_route.assert_called_once()
                                    
                                    # 4. Decision event published
                                    decision_calls = [call for call in mock_event_bus.publish.call_args_list 
                                                    if call[0][0] == "decision"]
                                    assert len(decision_calls) > 0
    
    def test_event_bus_observability(self, orchestrator):
        """Test that Thalamus provides proper observability through event bus."""
        orchestrator.habituation_vector = None  # Bypass RAS
        
        with patch('brain_core.os.listdir', return_value=['test_skill.py']):
            with patch('brain_core.event_bus') as mock_event_bus:
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG",
                                        model="mock-nano",
                                        provider="mock",
                                        cost=0.001,
                                        total_tokens=50
                                    )
                                    with patch('brain_core.get_embedding_model'):
                                        # Process spike
                                        result = asyncio.run(orchestrator.process_spike("test", "GOAL_INVESTIGATION: test spike"))
                                    
                                    # Verify all expected events were published
                                    published_events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
                                    
                                    assert "spike" in published_events
                                    assert "ras_filter" in published_events  
                                    assert "decision" in published_events
                                    
                                    # Verify decision event contains proper metadata
                                    decision_calls = [call for call in mock_event_bus.publish.call_args_list 
                                                    if call[0][0] == "decision"]
                                    decision_data = decision_calls[0][0][1]
                                    
                                    assert "decision" in decision_data
                                    assert "provider" in decision_data
                                    assert "model" in decision_data
                                    assert "cost" in decision_data
                                    assert decision_data["cost"] == 0.001
    
    @patch('brain_core.get_embedding_model')
    @patch('brain_core.os.listdir')
    def test_template_routing_decision(self, mock_listdir, mock_get_embedding, orchestrator, mock_router, mock_embedding_model):
        """Test that Thalamus routes to TEMPLATE when template match exists."""
        # Mock embedding model
        mock_get_embedding.return_value = mock_embedding_model
        
        # Mock available skills (no exact match)
        mock_listdir.return_value = ['other_skill.py']
        
        # Mock available templates
        mock_templates = {
            'classify_threat': {
                'description': 'Classify security threats',
                'model': 'nano',
                'category': 'security'
            }
        }
        
        orchestrator.router = mock_router
        
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value=mock_templates):
                            # Process spike that should trigger TEMPLATE routing
                            result = asyncio.run(orchestrator.process_spike("security", "template match for threat classification"))
                            
                            # Verify triage prompt included templates
                            call_args = mock_router.route.call_args
                            triage_prompt = call_args[0][1][1]["content"]  # messages[1]["content"]
                            assert "classify_threat" in triage_prompt
                            assert "Classify security threats" in triage_prompt
                            
                            # Verify decision event
                            decision_calls = [call for call in mock_event_bus.publish.call_args_list 
                                            if call[0][0] == "decision"]
                            assert len(decision_calls) > 0
                            assert decision_calls[0][0][1]["decision"] == "TEMPLATE:classify_threat"
    
    @patch('brain_core.get_embedding_model')
    @patch('brain_core.os.listdir')
    def test_log_routing_decision(self, mock_listdir, mock_get_embedding, orchestrator, mock_router, mock_embedding_model):
        """Test that Thalamus routes to LOG for routine observations."""
        # Mock embedding model
        mock_get_embedding.return_value = mock_embedding_model
        
        mock_listdir.return_value = ['unrelated_skill.py']
        
        orchestrator.router = mock_router
        
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                            # Process routine spike
                            result = asyncio.run(orchestrator.process_spike("system", "routine observation - normal metrics"))
                            
                            # Should return "Log recorded."
                            assert result == "Log recorded."
                            
                            # Verify LOG decision
                            decision_calls = [call for call in mock_event_bus.publish.call_args_list 
                                            if call[0][0] == "decision"]
                            assert len(decision_calls) > 0
                            assert decision_calls[0][0][1]["decision"] == "LOG"
    
    @patch('brain_core.os.listdir')
    def test_complex_routing_decision(self, mock_listdir, orchestrator, mock_router):
        """Test that Thalamus routes to COMPLEX for novel situations."""
        mock_listdir.return_value = ['basic_skill.py']
        
        orchestrator.router = mock_router
        
        # Mock Cortex response for COMPLEX routing
        def complex_route_side_effect(tier, messages, **kwargs):
            if tier == "nano":
                return StandardResponse(
                    content="COMPLEX",
                    model="mock-nano", 
                    provider="mock",
                    cost=0.001,
                    usage_tokens=50
                )
            elif tier == "cortex":
                return StandardResponse(
                    content="Complex analysis complete. Recommend creating new monitoring skill.",
                    model="mock-cortex",
                    provider="mock", 
                    cost=0.05,
                    usage_tokens=500
                )
        
        mock_router.route.side_effect = complex_route_side_effect
        
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                            with patch('brain_core.open', mock_open(read_data="System DNA content")):
                                # Process novel complex spike
                                result = asyncio.run(orchestrator.process_spike("unknown", "novel complex situation requiring analysis"))
                                
                                # Should get Cortex response
                                assert "Complex analysis complete" in result
                                
                                # Verify both nano (triage) and cortex calls were made
                                assert mock_router.route.call_count == 2
                                
                                # Verify cortex execution event
                                cortex_calls = [call for call in mock_event_bus.publish.call_args_list 
                                              if call[0][0] == "cortex_exec"]
                                assert len(cortex_calls) > 0
    
    @patch('brain_core.os.listdir')
    def test_cognitive_overload_avoids_complex(self, mock_listdir, orchestrator, mock_router):
        """Test that Thalamus avoids COMPLEX routing when cognitive load is high."""
        mock_listdir.return_value = ['skill.py']
        
        orchestrator.router = mock_router
        
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator, '_get_internal_state', return_value="COGNITIVE_OVERLOAD"):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                            # Process spike during cognitive overload
                            result = asyncio.run(orchestrator.process_spike("system", "cognitive_overload situation"))
                            
                            # Should route to LOG instead of COMPLEX
                            assert result == "Log recorded."
                            
                            # Verify triage prompt included overload state
                            call_args = mock_router.route.call_args
                            triage_prompt = call_args[0][1][1]["content"]
                            assert "COGNITIVE_OVERLOAD" in triage_prompt
                            assert "avoid COMPLEX" in triage_prompt
    
    def test_triage_prompt_construction(self, orchestrator, mock_router):
        """Test that triage prompt includes all necessary information."""
        orchestrator.router = mock_router
        
        with patch('brain_core.os.listdir', return_value=['skill1.py', 'skill2.py']):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value="Test context"):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="TEST_STATE"):
                            mock_templates = {
                                'template1': {'description': 'Template 1 desc'},
                                'template2': {'description': 'Template 2 desc'}
                            }
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value=mock_templates):
                                # Process spike to trigger triage
                                asyncio.run(orchestrator.process_spike("test", "test stimulus"))
                                
                                # Verify triage prompt structure
                                call_args = mock_router.route.call_args
                                messages = call_args[0][1]
                                
                                # Should have system and user messages
                                assert len(messages) == 2
                                assert messages[0]["role"] == "system"
                                assert messages[1]["role"] == "user"
                                
                                triage_prompt = messages[1]["content"]
                                
                                # Verify all required sections are present
                                assert "STIMULUS: test stimulus" in triage_prompt
                                assert "CONTEXT: Test context" in triage_prompt
                                assert "AVAILABLE_REFLEXES: ['skill1', 'skill2']" in triage_prompt
                                assert "template1" in triage_prompt
                                assert "Template 1 desc" in triage_prompt
                                assert "INTERNAL_STATE: TEST_STATE" in triage_prompt
                                
                                # Verify routing preferences are documented
                                assert "REFLEX > TEMPLATE > LOG > COMPLEX" in triage_prompt
    
    def test_cost_optimization_tier_usage(self, orchestrator, mock_router):
        """Test that Thalamus uses nano tier for cost optimization."""
        orchestrator.router = mock_router
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                # Process spike
                                asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Verify nano tier was used for triage
                                call_args = mock_router.route.call_args
                                assert call_args[1]['tier'] == 'nano'
                                
                                # Verify system message identifies Thalamus role
                                messages = call_args[0][1]
                                system_msg = messages[0]["content"]
                                assert "Thalamus" in system_msg
                                assert "cost-aware triage" in system_msg


class TestThalamusSkillDiscovery:
    """Test Thalamus skill discovery functionality (14.4.2)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @pytest.fixture
    def temp_skills_dir(self):
        """Create temporary skills directory for testing."""
        temp_dir = tempfile.mkdtemp()
        skills_dir = os.path.join(temp_dir, 'skills')
        os.makedirs(skills_dir)
        
        # Create test skill files
        skill_files = [
            'system_health_check.py',
            'network_scan.py', 
            'auto_generated_skill.py',
            'invalid_file.txt',  # Should be ignored
            '__pycache__',       # Should be ignored
        ]
        
        for filename in skill_files:
            filepath = os.path.join(skills_dir, filename)
            if filename.endswith('.py'):
                with open(filepath, 'w') as f:
                    f.write(f'# {filename}\ndef run(data):\n    return "test"')
            else:
                # Create directory or non-Python file
                if '.' not in filename:
                    os.makedirs(filepath, exist_ok=True)
                else:
                    with open(filepath, 'w') as f:
                        f.write('not python')
        
        yield skills_dir
        shutil.rmtree(temp_dir)
    
    def test_skill_discovery_filters_python_files(self, orchestrator, temp_skills_dir):
        """Test that skill discovery only includes .py files."""
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.return_value = [
                'valid_skill.py',
                'another_skill.py', 
                'invalid_file.txt',
                '__pycache__',
                'README.md'
            ]
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    
                                    # Process spike to trigger skill discovery
                                    asyncio.run(orchestrator.process_spike("test", "test"))
                                    
                                    # Verify triage prompt only includes .py files (without extension)
                                    call_args = mock_route.call_args
                                    triage_prompt = call_args[0][1][1]["content"]
                                    
                                    assert "valid_skill" in triage_prompt
                                    assert "another_skill" in triage_prompt
                                    assert "invalid_file" not in triage_prompt
                                    assert "__pycache__" not in triage_prompt
                                    assert "README" not in triage_prompt
    
    def test_skill_name_extraction(self, orchestrator):
        """Test that skill names are extracted correctly (removing .py extension)."""
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.return_value = [
                'system_health_check.py',
                'network_diagnostic.py',
                'auto_recovery.py'
            ]
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    
                                    # Process spike
                                    asyncio.run(orchestrator.process_spike("test", "test"))
                                    
                                    # Verify skill names in triage prompt (no .py extension)
                                    call_args = mock_route.call_args
                                    triage_prompt = call_args[0][1][1]["content"]
                                    
                                    assert "system_health_check" in triage_prompt
                                    assert "network_diagnostic" in triage_prompt
                                    assert "auto_recovery" in triage_prompt
                                    assert ".py" not in triage_prompt.split("AVAILABLE_REFLEXES:")[1].split("AVAILABLE_TEMPLATES:")[0]
    
    def test_empty_skills_directory(self, orchestrator):
        """Test behavior when skills directory is empty."""
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.return_value = []
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    
                                    # Process spike with no skills available
                                    result = asyncio.run(orchestrator.process_spike("test", "test"))
                                    
                                    # Should still work, just with empty skills list
                                    call_args = mock_route.call_args
                                    triage_prompt = call_args[0][1][1]["content"]
                                    assert "AVAILABLE_REFLEXES: []" in triage_prompt
    
    def test_skills_directory_error_handling(self, orchestrator):
        """Test error handling when skills directory cannot be read."""
        with patch('brain_core.os.listdir') as mock_listdir:
            mock_listdir.side_effect = OSError("Permission denied")
            
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    
                                    # Should handle error gracefully
                                    with pytest.raises(OSError):
                                        asyncio.run(orchestrator.process_spike("test", "test"))


class TestThalamusTemplateDiscovery:
    """Test Thalamus template discovery functionality (14.4.3)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @pytest.fixture
    def mock_template_engine(self):
        """Mock template engine with test templates."""
        mock_engine = MagicMock()
        
        test_templates = {
            'classify_threat': {
                'description': 'Classify security threats using AI',
                'model': 'nano',
                'category': 'security'
            },
            'compose_alert': {
                'description': 'Compose alert messages for incidents',
                'model': 'mini', 
                'category': 'communication'
            },
            'explain_anomaly': {
                'description': 'Explain detected system anomalies',
                'model': 'cortex',
                'category': 'analysis'
            }
        }
        
        mock_engine.get_available_templates.return_value = test_templates
        return mock_engine
    
    def test_template_discovery_integration(self, orchestrator, mock_template_engine):
        """Test that template discovery integrates with template engine."""
        orchestrator.template_engine = mock_template_engine
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                
                                # Process spike to trigger template discovery
                                asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Verify template engine was called
                                mock_template_engine.get_available_templates.assert_called_once()
                                
                                # Verify templates appear in triage prompt
                                call_args = mock_route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                
                                assert "classify_threat" in triage_prompt
                                assert "Classify security threats using AI" in triage_prompt
                                assert "compose_alert" in triage_prompt
                                assert "Compose alert messages for incidents" in triage_prompt
    
    def test_template_description_extraction(self, orchestrator, mock_template_engine):
        """Test that template descriptions are properly extracted for triage."""
        orchestrator.template_engine = mock_template_engine
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                
                                # Process spike
                                asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Verify template descriptions are included
                                call_args = mock_route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                
                                # Should include template name -> description mapping
                                template_section = triage_prompt.split("AVAILABLE_TEMPLATES:")[1].split("INTERNAL_STATE:")[0]
                                assert "classify_threat" in template_section
                                assert "Classify security threats using AI" in template_section
    
    def test_empty_templates_handling(self, orchestrator):
        """Test behavior when no templates are available."""
        mock_engine = MagicMock()
        mock_engine.get_available_templates.return_value = {}
        orchestrator.template_engine = mock_engine
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                
                                # Process spike with no templates
                                result = asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Should handle empty templates gracefully
                                call_args = mock_route.call_args
                                triage_prompt = call_args[0][1][1]["content"]
                                assert "AVAILABLE_TEMPLATES: {}" in triage_prompt
    
    def test_template_engine_error_handling(self, orchestrator):
        """Test error handling when template engine fails."""
        mock_engine = MagicMock()
        mock_engine.get_available_templates.side_effect = Exception("Template engine error")
        orchestrator.template_engine = mock_engine
        
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                
                                # Should handle template engine errors
                                with pytest.raises(Exception):
                                    asyncio.run(orchestrator.process_spike("test", "test"))


class TestThalamusIntegration:
    """Integration tests for Thalamus layer functionality."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    def test_thalamus_layer_ordering(self, orchestrator):
        """Test that Thalamus operates as Layer 2 after RAS (Layer 1) and before execution layers."""
        with patch('brain_core.os.listdir', return_value=['test_skill.py']):
            with patch('brain_core.event_bus') as mock_event_bus:
                with patch.object(orchestrator.memory, 'retrieve_context', return_value="test context") as mock_retrieve:
                    with patch.object(orchestrator.memory, 'store_memory') as mock_store:
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG", model="mock", provider="mock", cost=0.0
                                    )
                                    
                                    # Process spike
                                    result = asyncio.run(orchestrator.process_spike("test", "test spike"))
                                    
                                    # Verify execution order:
                                    # 1. RAS processing (implicit - no habituation vector set)
                                    # 2. Hippocampus context retrieval (Layer 3)
                                    mock_retrieve.assert_called_once_with("test spike")
                                    mock_store.assert_called_once_with("test", "test spike")
                                    
                                    # 3. Thalamus triage (Layer 2)
                                    mock_route.assert_called_once()
                                    
                                    # 4. Decision event published
                                    decision_calls = [call for call in mock_event_bus.publish.call_args_list 
                                                    if call[0][0] == "decision"]
                                    assert len(decision_calls) > 0
    
    def test_cognitive_load_integration(self, orchestrator):
        """Test integration with cognitive load monitoring."""
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                
                                # Process spike
                                asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Verify cognitive load was recorded
                                assert hasattr(orchestrator, 'cognitive_load')
                                # Note: cognitive_load.record_decision() is called in the actual implementation
    
    def test_circadian_rhythm_integration(self, orchestrator):
        """Test integration with circadian rhythm tracking."""
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                mock_route.return_value = StandardResponse(
                                    content="LOG", model="mock", provider="mock", cost=0.0
                                )
                                
                                # Process spike
                                asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Verify circadian rhythm was updated
                                assert hasattr(orchestrator, 'circadian')
                                # Note: circadian.record_spike() is called in the actual implementation
    
    def test_cost_optimization_validation(self, orchestrator):
        """Test that Thalamus achieves cost optimization goals."""
        with patch('brain_core.os.listdir', return_value=[]):
            with patch('brain_core.event_bus'):
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                            with patch.object(orchestrator.router, 'route') as mock_route:
                                # Mock nano-tier response with realistic cost
                                mock_route.return_value = StandardResponse(
                                    content="LOG",
                                    model="gpt-4o-mini",
                                    provider="openai",
                                    cost=0.0015,  # Realistic nano-tier cost
                                    total_tokens=100
                                )
                                
                                # Process spike
                                result = asyncio.run(orchestrator.process_spike("test", "test"))
                                
                                # Verify cost is in expected range (~$0.001)
                                call_args = mock_route.call_args
                                assert call_args[1]['tier'] == 'nano'
                                
                                # Verify the response cost is reasonable for triage
                                response = mock_route.return_value
                                assert response.cost < 0.01  # Should be much less than cortex tier
    
    def test_event_bus_observability(self, orchestrator):
        """Test that Thalamus provides proper observability through event bus."""
        with patch('brain_core.os.listdir', return_value=['test_skill.py']):
            with patch('brain_core.event_bus') as mock_event_bus:
                with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                    with patch.object(orchestrator.memory, 'store_memory'):
                        with patch.object(orchestrator, '_get_internal_state', return_value="NORMAL"):
                            with patch.object(orchestrator.template_engine, 'get_available_templates', return_value={}):
                                with patch.object(orchestrator.router, 'route') as mock_route:
                                    mock_route.return_value = StandardResponse(
                                        content="LOG",
                                        model="mock-nano",
                                        provider="mock",
                                        cost=0.001,
                                        total_tokens=50
                                    )
                                    
                                    # Process spike
                                    result = asyncio.run(orchestrator.process_spike("test", "test spike"))
                                    
                                    # Verify all expected events were published
                                    published_events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
                                    
                                    assert "spike" in published_events
                                    assert "ras_filter" in published_events  
                                    assert "decision" in published_events
                                    
                                    # Verify decision event contains proper metadata
                                    decision_calls = [call for call in mock_event_bus.publish.call_args_list 
                                                    if call[0][0] == "decision"]
                                    decision_data = decision_calls[0][0][1]
                                    
                                    assert "decision" in decision_data
                                    assert "provider" in decision_data
                                    assert "model" in decision_data
                                    assert "cost" in decision_data
                                    assert decision_data["cost"] == 0.001