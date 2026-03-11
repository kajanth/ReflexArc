"""
Integration tests for API endpoints and neural cascade interaction.

Tests the full API server integration with the NSA brain, including
spike processing, sensor management, and system status endpoints.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from api_server import NSAApiServer
from api.models import SpikeRequest, GoalRequest, SkillRunRequest, SensorToggleRequest
from tests.mocks.mock_provider import MockProvider


class MockNSAOrchestrator:
    """Mock NSA brain for API testing."""
    
    def __init__(self):
        self.process_spike_calls = []
        self.internal_state = {
            "ras_threshold": 0.7,
            "memory_count": 42,
            "habit_strength": 0.85
        }
        
        # Mock components
        self.router = MockRouter()
        self.circadian = MockCircadian()
        self.cognitive_load = MockCognitiveLoad()
        self.template_engine = MockTemplateEngine()
        self.dream_engine = MockDreamEngine()
        self.prefrontal_cortex = MockPrefrontalCortex()
        self.predictive_cortex = MockPredictiveCortex()
        self.brocas_area = MockBrocasArea()
        
    async def process_spike(self, sense_type: str, description: str):
        """Mock spike processing."""
        self.process_spike_calls.append((sense_type, description))
        
        # Simulate different outcomes based on description
        if "filtered" in description.lower():
            return None  # RAS filtered
        elif "reflex" in description.lower():
            return "REFLEX: auto_response_skill executed"
        elif "template" in description.lower():
            return "TEMPLATE: alert_composed via template"
        else:
            return "CORTEX: complex reasoning completed"
    
    def _get_internal_state(self):
        """Return mock internal state."""
        return self.internal_state


class MockRouter:
    """Mock model router."""
    
    def get_status(self):
        return {
            "openai": {"status": "healthy", "cost": 0.05},
            "anthropic": {"status": "healthy", "cost": 0.03},
            "gemini": {"status": "circuit_open", "cost": 0.00}
        }


class MockCircadian:
    """Mock circadian rhythm manager."""
    
    def get_phase(self):
        return "active"


class MockCognitiveLoad:
    """Mock cognitive load tracker."""
    
    def get_metrics(self):
        return {
            "cortex_ratio": 0.15,
            "reflex_ratio": 0.85,
            "load_level": "optimal"
        }


class MockTemplateEngine:
    """Mock template engine."""
    
    def get_available_templates(self):
        return ["classify_threat", "compose_alert", "explain_anomaly"]


class MockDreamEngine:
    """Mock dream engine."""
    
    def __init__(self):
        self.is_dreaming = False
        
    def get_recent_journals(self, limit):
        return [
            {"date": "2024-01-15", "insights": 3, "patterns": 2},
            {"date": "2024-01-14", "insights": 1, "patterns": 1}
        ][:limit]
    
    def get_patterns(self):
        return [
            {"pattern": "high_cpu_followed_by_alert", "confidence": 0.92},
            {"pattern": "webhook_spam_detection", "confidence": 0.78}
        ]


class MockPrefrontalCortex:
    """Mock prefrontal cortex (goal system)."""
    
    def __init__(self):
        self.is_evaluating = False
        self.goals = {
            "goal_1": {
                "objective": "Keep CPU usage below 80%",
                "metric": "cpu_percent",
                "operator": "<",
                "value": 80.0,
                "status": "on_track"
            }
        }
    
    def get_goals(self):
        return self.goals
    
    def add_goal(self, objective, metric, operator, value, priority):
        goal_id = f"goal_{len(self.goals) + 1}"
        goal = {
            "id": goal_id,
            "objective": objective,
            "metric": metric,
            "operator": operator,
            "value": value,
            "priority": priority,
            "status": "new"
        }
        self.goals[goal_id] = goal
        return goal
    
    def remove_goal(self, goal_id):
        return self.goals.pop(goal_id, None) is not None
    
    async def evaluate_all(self):
        """Mock goal evaluation."""
        self.is_evaluating = True
        await asyncio.sleep(0.1)  # Simulate work
        self.is_evaluating = False


class MockPredictiveCortex:
    """Mock predictive cortex."""
    
    def __init__(self):
        self.is_predicting = False
        self.phantom_history = [
            {"timestamp": 1642234567, "channel": "cpu", "predicted": 85.0, "actual": 82.0},
            {"timestamp": 1642234567, "channel": "memory", "predicted": 70.0, "actual": 68.0}
        ]
    
    def get_predictions(self):
        return {
            "cpu": {"current": 65.0, "predicted": 70.0, "confidence": 0.85},
            "memory": {"current": 55.0, "predicted": 60.0, "confidence": 0.78}
        }
    
    def get_summary(self):
        return {
            "channels": 2,
            "accuracy": 0.82,
            "phantom_spikes": len(self.phantom_history)
        }
    
    def get_phantom_history(self, limit):
        return self.phantom_history[:limit]


class MockBrocasArea:
    """Mock Broca's area (natural language interface)."""
    
    def __init__(self):
        self.sensor_mgr = None
    
    async def chat(self, message):
        """Mock chat response."""
        return {
            "response": f"Mock response to: {message}",
            "confidence": 0.95,
            "processing_time": 0.1
        }


class MockSensorManager:
    """Mock sensor manager."""
    
    def __init__(self):
        self.sensors = {
            "system_vitals": {"enabled": True, "healthy": True},
            "filesystem": {"enabled": True, "healthy": True},
            "webhooks": {"enabled": False, "healthy": True}
        }
    
    def all_sensors(self):
        return self.sensors
    
    def get_status_summary(self):
        enabled = sum(1 for s in self.sensors.values() if s["enabled"])
        healthy = sum(1 for s in self.sensors.values() if s["healthy"])
        return {
            "total": len(self.sensors),
            "enabled": enabled,
            "healthy": healthy
        }
    
    def enable(self, sensor_name):
        if sensor_name in self.sensors:
            self.sensors[sensor_name]["enabled"] = True
            return True
        return False
    
    def disable(self, sensor_name):
        if sensor_name in self.sensors:
            self.sensors[sensor_name]["enabled"] = False
            return True
        return False
    
    def toggle(self, sensor_name):
        if sensor_name in self.sensors:
            current = self.sensors[sensor_name]["enabled"]
            self.sensors[sensor_name]["enabled"] = not current
            return not current
        return None
    
    def is_enabled(self, sensor_name):
        return self.sensors.get(sensor_name, {}).get("enabled", False)


class TestAPIIntegration(AioHTTPTestCase):
    """Test API endpoint integration with neural cascade."""
    
    async def get_application(self):
        """Create test application."""
        self.mock_brain = MockNSAOrchestrator()
        self.mock_sensor_mgr = MockSensorManager()
        
        # Create API server with mocks
        api_server = NSAApiServer(
            brain=self.mock_brain,
            host="127.0.0.1",
            port=8080,
            sensor_mgr=self.mock_sensor_mgr
        )
        
        return api_server.app
    
    @unittest_run_loop
    async def test_spike_endpoint_basic(self):
        """Test basic spike injection endpoint."""
        spike_data = {
            "sense_type": "test_api",
            "description": "Test spike from API",
            "priority": "normal"
        }
        
        resp = await self.client.request("POST", "/spike", json=spike_data)
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["sense_type"], "test_api")
        self.assertIn("Test spike from API", data["result"])
        
        # Verify brain was called
        self.assertEqual(len(self.mock_brain.process_spike_calls), 1)
        call = self.mock_brain.process_spike_calls[0]
        self.assertEqual(call[0], "test_api")
        self.assertIn("Test spike from API", call[1])
    
    @unittest_run_loop
    async def test_spike_endpoint_validation(self):
        """Test spike endpoint input validation."""
        # Missing required fields
        resp = await self.client.request("POST", "/spike", json={})
        self.assertEqual(resp.status, 400)
        
        data = await resp.json()
        self.assertEqual(data["error"], "Validation failed")
        self.assertIn("details", data)
        
        # Invalid sense_type
        invalid_data = {
            "sense_type": "invalid/type",  # Contains invalid character
            "description": "Test",
            "priority": "normal"
        }
        
        resp = await self.client.request("POST", "/spike", json=invalid_data)
        self.assertEqual(resp.status, 400)
        
        # Description too long
        long_desc = "x" * 10001  # Over 10KB limit
        long_data = {
            "sense_type": "test",
            "description": long_desc,
            "priority": "normal"
        }
        
        resp = await self.client.request("POST", "/spike", json=long_data)
        self.assertEqual(resp.status, 400)
    
    @unittest_run_loop
    async def test_threat_spike_endpoint(self):
        """Test threat spike endpoint."""
        threat_data = {
            "description": "Suspicious process detected",
            "source": "security_scanner"
        }
        
        resp = await self.client.request("POST", "/spike/threat", json=threat_data)
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["priority"], "critical")
        
        # Verify brain was called with threat spike
        call = self.mock_brain.process_spike_calls[-1]
        self.assertEqual(call[0], "threat_api")
        self.assertIn("THREAT/security_scanner", call[1])
    
    @unittest_run_loop
    async def test_metric_spike_endpoint(self):
        """Test metric spike endpoint."""
        metric_data = {
            "metric": "cpu_usage",
            "value": 85.5,
            "unit": "%",
            "source": "monitoring",
            "threshold": 80.0
        }
        
        resp = await self.client.request("POST", "/spike/metric", json=metric_data)
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["metric"], "cpu_usage")
        self.assertEqual(data["value"], 85.5)
        
        # Verify brain was called with metric spike
        call = self.mock_brain.process_spike_calls[-1]
        self.assertEqual(call[0], "metric_api")
        self.assertIn("cpu_usage: 85.5%", call[1])
        self.assertIn("BREACHED", call[1])
    
    @unittest_run_loop
    async def test_status_endpoint(self):
        """Test system status endpoint."""
        resp = await self.client.request("GET", "/status")
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("uptime_seconds", data)
        self.assertIn("internal_state", data)
        self.assertIn("circadian_phase", data)
        self.assertIn("cognitive_load", data)
        self.assertIn("providers", data)
        self.assertIn("sensors", data)
        
        # Verify internal state structure
        internal_state = data["internal_state"]
        self.assertIn("ras_threshold", internal_state)
        self.assertIn("memory_count", internal_state)
        
        # Verify provider status
        providers = data["providers"]
        self.assertIn("openai", providers)
        self.assertIn("anthropic", providers)
    
    @unittest_run_loop
    async def test_skills_endpoint(self):
        """Test skills listing endpoint."""
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = [
                "auto_cpu_alert.py",
                "network_diagnostic.py",
                "__init__.py",
                "README.md"
            ]
            
            resp = await self.client.request("GET", "/skills")
            self.assertEqual(resp.status, 200)
            
            data = await resp.json()
            self.assertIn("python_skills", data)
            self.assertIn("ai_templates", data)
            self.assertIn("total", data)
            
            # Should filter out non-Python files
            python_skills = data["python_skills"]
            self.assertIn("auto_cpu_alert", python_skills)
            self.assertIn("network_diagnostic", python_skills)
            self.assertNotIn("__init__", python_skills)
            
            # Should include templates
            templates = data["ai_templates"]
            self.assertEqual(templates, ["classify_threat", "compose_alert", "explain_anomaly"])
    
    @unittest_run_loop
    async def test_skill_run_endpoint(self):
        """Test skill execution endpoint."""
        skill_data = {
            "skill": "test_skill",
            "data": {"param1": "value1"}
        }
        
        # Mock skill module
        mock_module = MagicMock()
        mock_module.run.return_value = "Skill executed successfully"
        
        with patch('importlib.import_module', return_value=mock_module):
            with patch('importlib.reload'):
                resp = await self.client.request("POST", "/skill/run", json=skill_data)
                self.assertEqual(resp.status, 200)
                
                data = await resp.json()
                self.assertEqual(data["status"], "executed")
                self.assertEqual(data["skill"], "test_skill")
                self.assertEqual(data["result"], "Skill executed successfully")
                
                # Verify skill was called with correct data
                mock_module.run.assert_called_once_with({"param1": "value1"})
    
    @unittest_run_loop
    async def test_skill_run_not_found(self):
        """Test skill execution with non-existent skill."""
        skill_data = {
            "skill": "nonexistent_skill",
            "data": {}
        }
        
        with patch('importlib.import_module', side_effect=ModuleNotFoundError):
            resp = await self.client.request("POST", "/skill/run", json=skill_data)
            self.assertEqual(resp.status, 404)
            
            data = await resp.json()
            self.assertIn("not found", data["error"])
    
    @unittest_run_loop
    async def test_sensor_endpoints(self):
        """Test sensor management endpoints."""
        # Get sensors
        resp = await self.client.request("GET", "/sensors")
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertIn("sensors", data)
        self.assertIn("summary", data)
        
        sensors = data["sensors"]
        self.assertIn("system_vitals", sensors)
        self.assertTrue(sensors["system_vitals"]["enabled"])
        
        # Toggle sensor
        toggle_data = {
            "sensor": "webhooks",
            "action": "enable"
        }
        
        resp = await self.client.request("POST", "/sensor/toggle", json=toggle_data)
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["sensor"], "webhooks")
        self.assertTrue(data["enabled"])
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        resp = await self.client.request("GET", "/health")
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("uptime", data)
        self.assertIn("dashboard_viewers", data)
    
    @unittest_run_loop
    async def test_goal_endpoints(self):
        """Test goal management endpoints."""
        # Get goals
        resp = await self.client.request("GET", "/goals")
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertIn("goals", data)
        self.assertIn("summary", data)
        
        # Create goal
        goal_data = {
            "objective": "Maintain low latency",
            "metric": "response_time",
            "operator": "<",
            "value": 100.0,
            "priority": "high"
        }
        
        resp = await self.client.request("POST", "/goal", json=goal_data)
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["status"], "created")
        self.assertIn("goal", data)
        
        goal = data["goal"]
        self.assertEqual(goal["objective"], "Maintain low latency")
        self.assertEqual(goal["metric"], "response_time")
    
    @unittest_run_loop
    async def test_prediction_endpoints(self):
        """Test prediction system endpoints."""
        # Get predictions
        resp = await self.client.request("GET", "/predictions")
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertIn("channels", data)
        self.assertIn("summary", data)
        self.assertIn("is_predicting", data)
        
        channels = data["channels"]
        self.assertIn("cpu", channels)
        self.assertIn("memory", channels)
        
        # Get prediction history
        resp = await self.client.request("GET", "/predictions/history?limit=5")
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertIn("phantoms", data)
        self.assertIn("count", data)
        self.assertLessEqual(len(data["phantoms"]), 5)
    
    @unittest_run_loop
    async def test_broca_chat_endpoint(self):
        """Test Broca's area chat endpoint."""
        chat_data = {
            "message": "What is the current system status?"
        }
        
        resp = await self.client.request("POST", "/broca/chat", json=chat_data)
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertIn("response", data)
        self.assertIn("confidence", data)
        self.assertIn("What is the current system status?", data["response"])
    
    @unittest_run_loop
    async def test_webhook_endpoint(self):
        """Test webhook ingestion endpoint."""
        webhook_data = {
            "action": "push",
            "repository": {"name": "test-repo"},
            "commits": [{"message": "Fix bug"}]
        }
        
        # Mock webhook receptor
        mock_receptor = MagicMock()
        mock_receptor.ingest_webhook = MagicMock()
        
        with patch.object(self.mock_sensor_mgr, 'get_sensor', return_value=mock_receptor):
            resp = await self.client.request("POST", "/webhook/github", json=webhook_data)
            self.assertEqual(resp.status, 200)
            
            data = await resp.json()
            self.assertEqual(data["status"], "received")
            self.assertEqual(data["source"], "github")
            
            # Verify webhook was ingested
            mock_receptor.ingest_webhook.assert_called_once_with("github", webhook_data)
    
    @unittest_run_loop
    async def test_concurrent_spike_processing(self):
        """Test concurrent spike processing."""
        spike_data = {
            "sense_type": "concurrent_test",
            "description": "Concurrent spike {}",
            "priority": "normal"
        }
        
        # Send multiple spikes concurrently
        tasks = []
        for i in range(5):
            data = spike_data.copy()
            data["description"] = data["description"].format(i)
            task = self.client.request("POST", "/spike", json=data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for resp in responses:
            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertEqual(data["status"], "processed")
        
        # Verify all spikes were processed
        self.assertEqual(len(self.mock_brain.process_spike_calls), 5)
    
    @unittest_run_loop
    async def test_error_handling(self):
        """Test API error handling."""
        # Invalid JSON
        resp = await self.client.request("POST", "/spike", data="invalid json")
        self.assertEqual(resp.status, 400)
        
        # Missing content-type
        resp = await self.client.request("POST", "/spike")
        self.assertEqual(resp.status, 400)
        
        # Simulate brain error
        original_process_spike = self.mock_brain.process_spike
        self.mock_brain.process_spike = AsyncMock(side_effect=Exception("Brain error"))
        
        spike_data = {
            "sense_type": "error_test",
            "description": "Error test spike",
            "priority": "normal"
        }
        
        resp = await self.client.request("POST", "/spike", json=spike_data)
        self.assertEqual(resp.status, 500)
        
        data = await resp.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Brain error", data["error"])
        
        # Restore original method
        self.mock_brain.process_spike = original_process_spike