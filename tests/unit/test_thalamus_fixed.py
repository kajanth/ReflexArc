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
                        with patch.object(orchestra