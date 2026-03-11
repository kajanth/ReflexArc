"""
Unit tests for API request models.

Tests validation logic for all Pydantic models in api/models.py.
"""

import pytest
from pydantic import ValidationError
from api.models import (
    SpikeRequest, 
    GoalRequest, 
    SkillRunRequest, 
    SensorToggleRequest,
    ThreatSpikeRequest,
    MetricSpikeRequest,
    GoalDeleteRequest,
    BrocaChatRequest
)


class TestSpikeRequest:
    """Tests for SpikeRequest model."""
    
    def test_valid_spike_request(self):
        """Test valid spike request creation."""
        req = SpikeRequest(
            description="Test spike",
            sense_type="api",
            priority="normal"
        )
        assert req.description == "Test spike"
        assert req.sense_type == "api"
        assert req.priority == "normal"
    
    def test_spike_with_defaults(self):
        """Test spike request with default values."""
        req = SpikeRequest(description="Test spike")
        assert req.sense_type == "api"
        assert req.priority == "normal"
    
    def test_spike_description_too_long(self):
        """Test spike description exceeds 10KB limit."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeRequest(description="x" * 10241)
        assert "description" in str(exc_info.value)
    
    def test_spike_empty_description(self):
        """Test spike with empty description."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeRequest(description="")
        assert "description" in str(exc_info.value)
    
    def test_spike_whitespace_only_description(self):
        """Test spike with whitespace-only description."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeRequest(description="   ")
        assert "empty or whitespace only" in str(exc_info.value)
    
    def test_spike_invalid_sense_type(self):
        """Test spike with invalid sense_type characters."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeRequest(description="Test", sense_type="api/injection")
        assert "alphanumeric" in str(exc_info.value)
    
    def test_spike_invalid_priority(self):
        """Test spike with invalid priority value."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeRequest(description="Test", priority="invalid")
        assert "priority" in str(exc_info.value)


class TestGoalRequest:
    """Tests for GoalRequest model."""
    
    def test_valid_goal_request(self):
        """Test valid goal request creation."""
        req = GoalRequest(
            objective="Keep CPU low",
            metric="cpu_percent",
            operator="<",
            value=80.0,
            priority="medium"
        )
        assert req.objective == "Keep CPU low"
        assert req.metric == "cpu_percent"
        assert req.operator == "<"
        assert req.value == 80.0
        assert req.priority == "medium"
    
    def test_goal_with_defaults(self):
        """Test goal request with default values."""
        req = GoalRequest(
            objective="Test goal",
            metric="test_metric",
            value=100.0
        )
        assert req.operator == "<"
        assert req.priority == "medium"
    
    def test_goal_empty_objective(self):
        """Test goal with empty objective."""
        with pytest.raises(ValidationError) as exc_info:
            GoalRequest(objective="", metric="test", value=100.0)
        assert "objective" in str(exc_info.value)
    
    def test_goal_whitespace_only_objective(self):
        """Test goal with whitespace-only objective."""
        with pytest.raises(ValidationError) as exc_info:
            GoalRequest(objective="   ", metric="test", value=100.0)
        assert "empty or whitespace only" in str(exc_info.value)
    
    def test_goal_invalid_metric_name(self):
        """Test goal with invalid metric name (injection attempt)."""
        with pytest.raises(ValidationError) as exc_info:
            GoalRequest(
                objective="Test",
                metric="cpu; DROP TABLE goals;",
                value=100.0
            )
        assert "alphanumeric" in str(exc_info.value)
    
    def test_goal_valid_metric_with_dots(self):
        """Test goal with valid metric name containing dots."""
        req = GoalRequest(
            objective="Test",
            metric="system.cpu.percent",
            value=80.0
        )
        assert req.metric == "system.cpu.percent"
    
    def test_goal_invalid_operator(self):
        """Test goal with invalid operator."""
        with pytest.raises(ValidationError) as exc_info:
            GoalRequest(
                objective="Test",
                metric="test",
                operator="===",
                value=100.0
            )
        assert "operator" in str(exc_info.value)


class TestSkillRunRequest:
    """Tests for SkillRunRequest model."""
    
    def test_valid_skill_request(self):
        """Test valid skill run request."""
        req = SkillRunRequest(
            skill="system_health_check",
            data="Test data"
        )
        assert req.skill == "system_health_check"
        assert req.data == "Test data"
    
    def test_skill_with_default_data(self):
        """Test skill request with default data."""
        req = SkillRunRequest(skill="test_skill")
        assert req.data == "Triggered via API"
    
    def test_skill_directory_traversal_attempt(self):
        """Test skill name with directory traversal attempt."""
        with pytest.raises(ValidationError) as exc_info:
            SkillRunRequest(skill="../../../etc/passwd")
        assert "path separators" in str(exc_info.value)
    
    def test_skill_with_slash(self):
        """Test skill name with forward slash."""
        with pytest.raises(ValidationError) as exc_info:
            SkillRunRequest(skill="skills/malicious")
        assert "alphanumeric" in str(exc_info.value)
    
    def test_skill_with_backslash(self):
        """Test skill name with backslash."""
        with pytest.raises(ValidationError) as exc_info:
            SkillRunRequest(skill="skills\\malicious")
        assert "path separators" in str(exc_info.value)
    
    def test_skill_data_too_long(self):
        """Test skill data exceeds 10KB limit."""
        with pytest.raises(ValidationError) as exc_info:
            SkillRunRequest(skill="test", data="x" * 10241)
        assert "data" in str(exc_info.value)


class TestSensorToggleRequest:
    """Tests for SensorToggleRequest model."""
    
    def test_valid_sensor_toggle(self):
        """Test valid sensor toggle request."""
        req = SensorToggleRequest(
            sensor="vision",
            action="toggle"
        )
        assert req.sensor == "vision"
        assert req.action == "toggle"
    
    def test_sensor_with_default_action(self):
        """Test sensor toggle with default action."""
        req = SensorToggleRequest(sensor="audio")
        assert req.action == "toggle"
    
    def test_sensor_enable_action(self):
        """Test sensor enable action."""
        req = SensorToggleRequest(sensor="vision", action="enable")
        assert req.action == "enable"
    
    def test_sensor_disable_action(self):
        """Test sensor disable action."""
        req = SensorToggleRequest(sensor="vision", action="disable")
        assert req.action == "disable"
    
    def test_sensor_invalid_name(self):
        """Test sensor with invalid name characters."""
        with pytest.raises(ValidationError) as exc_info:
            SensorToggleRequest(sensor="vision/injection")
        assert "alphanumeric" in str(exc_info.value)
    
    def test_sensor_invalid_action(self):
        """Test sensor with invalid action."""
        with pytest.raises(ValidationError) as exc_info:
            SensorToggleRequest(sensor="vision", action="destroy")
        assert "action" in str(exc_info.value)



class TestThreatSpikeRequest:
    """Tests for ThreatSpikeRequest model."""
    
    def test_valid_threat_spike(self):
        """Test valid threat spike request."""
        req = ThreatSpikeRequest(
            description="Unauthorized access attempt",
            source="security_monitor"
        )
        assert req.description == "Unauthorized access attempt"
        assert req.source == "security_monitor"
    
    def test_threat_with_default_source(self):
        """Test threat spike with default source."""
        req = ThreatSpikeRequest(description="Test threat")
        assert req.source == "external"
    
    def test_threat_empty_description(self):
        """Test threat with empty description."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSpikeRequest(description="")
        assert "description" in str(exc_info.value)
    
    def test_threat_whitespace_only_description(self):
        """Test threat with whitespace-only description."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSpikeRequest(description="   ")
        assert "empty or whitespace only" in str(exc_info.value)
    
    def test_threat_description_too_long(self):
        """Test threat description exceeds 10KB limit."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSpikeRequest(description="x" * 10241)
        assert "description" in str(exc_info.value)
    
    def test_threat_invalid_source(self):
        """Test threat with invalid source characters."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatSpikeRequest(description="Test", source="source/injection")
        assert "alphanumeric" in str(exc_info.value)


class TestMetricSpikeRequest:
    """Tests for MetricSpikeRequest model."""
    
    def test_valid_metric_spike(self):
        """Test valid metric spike request."""
        req = MetricSpikeRequest(
            metric="cpu_percent",
            value=85.5,
            unit="%",
            source="system_monitor",
            threshold=80.0
        )
        assert req.metric == "cpu_percent"
        assert req.value == 85.5
        assert req.unit == "%"
        assert req.source == "system_monitor"
        assert req.threshold == 80.0
    
    def test_metric_with_defaults(self):
        """Test metric spike with default values."""
        req = MetricSpikeRequest(metric="test_metric", value=100.0)
        assert req.unit == ""
        assert req.source == "external"
        assert req.threshold is None
    
    def test_metric_invalid_name(self):
        """Test metric with invalid name (injection attempt)."""
        with pytest.raises(ValidationError) as exc_info:
            MetricSpikeRequest(metric="cpu; DROP TABLE metrics;", value=100.0)
        assert "alphanumeric" in str(exc_info.value)
    
    def test_metric_valid_name_with_dots(self):
        """Test metric with valid name containing dots."""
        req = MetricSpikeRequest(metric="system.cpu.percent", value=80.0)
        assert req.metric == "system.cpu.percent"
    
    def test_metric_invalid_source(self):
        """Test metric with invalid source characters."""
        with pytest.raises(ValidationError) as exc_info:
            MetricSpikeRequest(metric="test", value=100.0, source="source/injection")
        assert "alphanumeric" in str(exc_info.value)
    
    def test_metric_invalid_value(self):
        """Test metric with invalid value (infinity)."""
        with pytest.raises(ValidationError) as exc_info:
            MetricSpikeRequest(metric="test", value=float('inf'))
        assert "valid finite number" in str(exc_info.value)


class TestGoalDeleteRequest:
    """Tests for GoalDeleteRequest model."""
    
    def test_valid_goal_delete(self):
        """Test valid goal delete request."""
        req = GoalDeleteRequest(id="goal_12345")
        assert req.id == "goal_12345"
    
    def test_goal_delete_empty_id(self):
        """Test goal delete with empty ID."""
        with pytest.raises(ValidationError) as exc_info:
            GoalDeleteRequest(id="")
        assert "id" in str(exc_info.value)
    
    def test_goal_delete_whitespace_only_id(self):
        """Test goal delete with whitespace-only ID."""
        with pytest.raises(ValidationError) as exc_info:
            GoalDeleteRequest(id="   ")
        assert "empty or whitespace only" in str(exc_info.value)


class TestBrocaChatRequest:
    """Tests for BrocaChatRequest model."""
    
    def test_valid_chat_request(self):
        """Test valid chat request."""
        req = BrocaChatRequest(message="What is the current system status?")
        assert req.message == "What is the current system status?"
    
    def test_chat_empty_message(self):
        """Test chat with empty message."""
        with pytest.raises(ValidationError) as exc_info:
            BrocaChatRequest(message="")
        assert "message" in str(exc_info.value)
    
    def test_chat_whitespace_only_message(self):
        """Test chat with whitespace-only message."""
        with pytest.raises(ValidationError) as exc_info:
            BrocaChatRequest(message="   ")
        assert "empty or whitespace only" in str(exc_info.value)
    
    def test_chat_message_too_long(self):
        """Test chat message exceeds 10KB limit."""
        with pytest.raises(ValidationError) as exc_info:
            BrocaChatRequest(message="x" * 10241)
        assert "message" in str(exc_info.value)
