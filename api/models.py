"""
🌐 NSA API Request/Response Models

Pydantic models for validating API endpoint inputs.
Ensures all user input is properly validated before processing.
"""

import re
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class SpikeRequest(BaseModel):
    """
    Request model for POST /spike endpoint.
    
    Validates sensory spike injection requests.
    """
    
    description: str = Field(
        ...,
        min_length=1,
        max_length=10240,  # 10KB limit (FR-005.3)
        description="Spike description text"
    )
    sense_type: str = Field(
        "api",
        min_length=1,
        max_length=50,
        description="Type of sensory input (e.g., api, vision, audio)"
    )
    priority: Literal["low", "normal", "high", "critical"] = Field(
        "normal",
        description="Spike priority level"
    )
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")
        return v
    
    @field_validator('sense_type')
    @classmethod
    def validate_sense_type(cls, v: str) -> str:
        """Validate sense_type contains only allowed characters (alphanumeric, underscore, hyphen)."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "sense_type must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "User reported system slowdown",
                "sense_type": "api",
                "priority": "normal"
            }
        }


class GoalRequest(BaseModel):
    """
    Request model for POST /goal endpoint.
    
    Validates goal creation requests for the Prefrontal Cortex.
    """
    
    objective: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Goal objective description"
    )
    metric: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Metric name to track"
    )
    operator: Literal["<", ">", "<=", ">=", "==", "!="] = Field(
        "<",
        description="Comparison operator for goal evaluation"
    )
    value: float = Field(
        ...,
        description="Target value for the metric"
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        "medium",
        description="Goal priority level"
    )
    
    @field_validator('objective')
    @classmethod
    def validate_objective(cls, v: str) -> str:
        """Ensure objective is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("Objective cannot be empty or whitespace only")
        return v
    
    @field_validator('metric')
    @classmethod
    def validate_metric(cls, v: str) -> str:
        """
        Validate metric name contains only allowed characters (FR-005.5).
        Prevents injection attacks by restricting to alphanumeric, underscore, hyphen, and dot.
        """
        # Strip whitespace
        v = v.strip()
        
        # Check for basic pattern (alphanumeric, underscore, hyphen, dot)
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError(
                "metric must contain only alphanumeric characters, underscores, hyphens, and dots"
            )
        
        # Prevent common injection patterns
        dangerous_patterns = [
            r'__',  # Double underscore (Python special methods)
            r'\.\.',  # Directory traversal
            r'^\.',  # Hidden files
            r'\.$',  # Ending with dot
            r'--',  # SQL comment
            r';',   # Command separator
            r'\|',  # Pipe
            r'&',   # Command separator
            r'\$',  # Variable expansion
            r'`',   # Command substitution
            r'eval', # Code evaluation
            r'exec', # Code execution
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"metric name contains potentially dangerous pattern: {pattern}")
        
        # Must start with letter or underscore
        if not re.match(r'^[a-zA-Z_]', v):
            raise ValueError("metric name must start with a letter or underscore")
            
        return v
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Ensure value is a valid number (not NaN or infinity)."""
        if not (-1e308 <= v <= 1e308):  # Reasonable float range
            raise ValueError("value must be a valid finite number")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "objective": "Keep CPU usage under control",
                "metric": "cpu_percent",
                "operator": "<",
                "value": 80.0,
                "priority": "medium"
            }
        }


class SkillRunRequest(BaseModel):
    """
    Request model for POST /skill/run endpoint.
    
    Validates manual skill execution requests.
    """
    
    skill: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Skill name to execute"
    )
    data: str = Field(
        "Triggered via API",
        max_length=10240,  # 10KB limit
        description="Data to pass to the skill"
    )
    
    @field_validator('skill')
    @classmethod
    def validate_skill(cls, v: str) -> str:
        """
        Validate skill name to prevent directory traversal (FR-005.4).
        Only allow alphanumeric characters, underscores, and hyphens.
        """
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "skill name must contain only alphanumeric characters, underscores, and hyphens"
            )
        
        # Prevent directory traversal attempts
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError("skill name cannot contain path separators or parent directory references")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill": "system_health_check",
                "data": "Triggered via API"
            }
        }


class SensorToggleRequest(BaseModel):
    """
    Request model for POST /sensor/toggle endpoint.
    
    Validates sensor enable/disable requests.
    """
    
    sensor: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Sensor name to toggle"
    )
    action: Literal["enable", "disable", "toggle"] = Field(
        "toggle",
        description="Action to perform on the sensor"
    )
    
    @field_validator('sensor')
    @classmethod
    def validate_sensor(cls, v: str) -> str:
        """
        Validate sensor name contains only allowed characters.
        Prevents injection by restricting to alphanumeric, underscore, and hyphen.
        """
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "sensor name must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "sensor": "vision",
                "action": "toggle"
            }
        }


class ThreatSpikeRequest(BaseModel):
    """
    Request model for POST /spike/threat endpoint.
    
    Validates high-priority threat spike injection requests.
    """
    
    description: str = Field(
        ...,
        min_length=1,
        max_length=10240,  # 10KB limit (FR-005.3)
        description="Threat description text"
    )
    source: str = Field(
        "external",
        min_length=1,
        max_length=50,
        description="Source of the threat"
    )
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")
        return v
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source contains only allowed characters."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "source must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Unauthorized access attempt detected",
                "source": "security_monitor"
            }
        }


class MetricSpikeRequest(BaseModel):
    """
    Request model for POST /spike/metric endpoint.
    
    Validates system metric observation spike injection requests.
    """
    
    metric: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Metric name"
    )
    value: float = Field(
        ...,
        description="Metric value"
    )
    unit: str = Field(
        "",
        max_length=20,
        description="Unit of measurement (optional)"
    )
    source: str = Field(
        "external",
        min_length=1,
        max_length=50,
        description="Source of the metric"
    )
    threshold: Optional[float] = Field(
        None,
        description="Threshold value if breached (optional)"
    )
    
    @field_validator('metric')
    @classmethod
    def validate_metric(cls, v: str) -> str:
        """
        Validate metric name contains only allowed characters (FR-005.5).
        Prevents injection attacks.
        """
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError(
                "metric must contain only alphanumeric characters, underscores, hyphens, and dots"
            )
        return v
    
    @field_validator('value', 'threshold')
    @classmethod
    def validate_numeric(cls, v: Optional[float]) -> Optional[float]:
        """Ensure value is a valid number (not NaN or infinity)."""
        if v is not None and not (-1e308 <= v <= 1e308):
            raise ValueError("value must be a valid finite number")
        return v
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source contains only allowed characters."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "source must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric": "cpu_percent",
                "value": 85.5,
                "unit": "%",
                "source": "system_monitor",
                "threshold": 80.0
            }
        }


class GoalDeleteRequest(BaseModel):
    """
    Request model for DELETE /goal endpoint.
    
    Validates goal deletion requests.
    """
    
    id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Goal ID to delete"
    )
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure ID is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("ID cannot be empty or whitespace only")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "goal_12345"
            }
        }


class BrocaChatRequest(BaseModel):
    """
    Request model for POST /broca/chat endpoint.
    
    Validates natural language chat requests.
    """
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=10240,  # 10KB limit
        description="Chat message text"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Ensure message is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is the current system status?"
            }
        }
