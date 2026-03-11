"""
🧠 NSA Configuration Schemas

Pydantic schemas for validating brain configuration files.
Ensures configs are valid before the system starts.
"""

from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class DatabaseConfigSchema(BaseModel):
    """Schema for database connection pooling configuration."""
    
    path: str = Field("memory/long_term_memory.db", description="Database file path")
    min_pool_size: int = Field(1, ge=1, le=10, description="Minimum connection pool size")
    max_pool_size: int = Field(5, ge=1, le=20, description="Maximum connection pool size")
    
    @model_validator(mode='after')
    def validate_pool_sizes(self) -> 'DatabaseConfigSchema':
        """Ensure min_pool_size <= max_pool_size."""
        if self.min_pool_size > self.max_pool_size:
            raise ValueError(f"min_pool_size ({self.min_pool_size}) cannot be greater than max_pool_size ({self.max_pool_size})")
        return self


class EmbeddingModelConfigSchema(BaseModel):
    """Schema for embedding model caching configuration."""
    
    model_name: str = Field("all-MiniLM-L6-v2", description="SentenceTransformer model name or path")
    cache_enabled: bool = Field(True, description="Enable in-memory model caching")
    device: Optional[str] = Field(None, description="Device to run model on (cpu, cuda, mps, or None for auto)")
    
    @field_validator('device')
    @classmethod
    def validate_device(cls, v: Optional[str]) -> Optional[str]:
        """Validate device string."""
        if v is not None and v not in ['cpu', 'cuda', 'mps']:
            raise ValueError(f"Device must be one of: cpu, cuda, mps, or None (got '{v}')")
        return v


class BrainConfigSchema(BaseModel):
    """Schema for the main brain configuration section."""
    
    name: str = Field(..., description="Brain profile name")
    description: Optional[str] = Field(None, description="Brain profile description")
    heartbeat_interval: int = Field(30, ge=1, le=300, description="Heartbeat interval in seconds")
    prediction_interval: int = Field(120, ge=10, le=600, description="Prediction interval in seconds")
    goal_eval_interval: int = Field(300, ge=30, le=1800, description="Goal evaluation interval in seconds")
    mcp_tool_timeout: float = Field(30.0, ge=1.0, le=300.0, description="Timeout for MCP tool execution in seconds")
    health_check_timeout: float = Field(5.0, ge=1.0, le=30.0, description="Timeout for health checks in seconds")
    database: Optional[DatabaseConfigSchema] = Field(default_factory=DatabaseConfigSchema, description="Database configuration")
    embedding_model: Optional[EmbeddingModelConfigSchema] = Field(default_factory=EmbeddingModelConfigSchema, description="Embedding model configuration")
    
    @field_validator('heartbeat_interval', 'prediction_interval', 'goal_eval_interval')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Interval must be positive")
        return v


class SensorConfigSchema(BaseModel):
    """Schema for sensor configuration."""
    
    name: str = Field(..., description="Sensor identifier")
    module: Optional[str] = Field(None, description="Python module path (e.g., sensors.vision.OpenCVReflex)")
    source: Optional[str] = Field(None, description="Internal source path (e.g., brain.circadian)")
    args: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Constructor arguments")
    emoji: str = Field("📡", description="Display emoji")
    label: str = Field(..., description="Human-readable label")
    type: Literal["peripheral", "internal", "security"] = Field("peripheral", description="Sensor type")
    
    @model_validator(mode='after')
    def validate_source_or_module(self) -> 'SensorConfigSchema':
        """Ensure either module or source is specified, but not both."""
        if self.module and self.source:
            raise ValueError(f"Sensor '{self.name}' cannot have both 'module' and 'source'")
        if not self.module and not self.source:
            raise ValueError(f"Sensor '{self.name}' must have either 'module' or 'source'")
        return self


class PredictionConfigSchema(BaseModel):
    """Schema for prediction channel configuration."""
    
    name: str = Field(..., description="Channel identifier")
    measurer: str = Field(..., description="Measurer function path (e.g., psutil.cpu_percent)")
    args: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Measurer arguments")
    attribute: Optional[str] = Field(None, description="Attribute to extract from result")
    threshold: float = Field(..., description="Threshold value for breach detection")
    direction: Literal["above", "below"] = Field("above", description="Breach direction")
    unit: str = Field("", description="Unit of measurement")
    description: str = Field(..., description="Human-readable description")
    
    @field_validator('threshold')
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Threshold must be non-negative")
        return v


class CustomMeasurerSchema(BaseModel):
    """Schema for custom measurer configuration."""
    
    name: str = Field(..., description="Measurer identifier")
    module: str = Field(..., description="Python module path to measurer function")
    
    @field_validator('module')
    @classmethod
    def validate_module_path(cls, v: str) -> str:
        if not v or '.' not in v:
            raise ValueError("Module path must be in format 'module.function'")
        return v


class MCPServerConfigSchema(BaseModel):
    """Schema for MCP server configuration."""
    
    name: str = Field(..., description="Server identifier")
    command: str = Field(..., description="Command to execute (e.g., uvx, npx)")
    args: List[str] = Field(..., description="Command arguments")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    
    @field_validator('command')
    @classmethod
    def validate_command(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Command cannot be empty")
        return v
    
    @field_validator('args')
    @classmethod
    def validate_args(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Args list cannot be empty")
        return v


class FullBrainConfigSchema(BaseModel):
    """Complete brain configuration schema."""
    
    brain: BrainConfigSchema
    sensors: Optional[List[SensorConfigSchema]] = Field(default_factory=list)
    predictions: Optional[List[PredictionConfigSchema]] = Field(default_factory=list)
    custom_measurers: Optional[List[CustomMeasurerSchema]] = Field(default_factory=list)
    mcp_servers: Optional[List[MCPServerConfigSchema]] = Field(default_factory=list)
    
    @field_validator('sensors')
    @classmethod
    def validate_unique_sensor_names(cls, v: List[SensorConfigSchema]) -> List[SensorConfigSchema]:
        """Ensure sensor names are unique."""
        names = [s.name for s in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate sensor names found: {set(duplicates)}")
        return v
    
    @field_validator('predictions')
    @classmethod
    def validate_unique_prediction_names(cls, v: List[PredictionConfigSchema]) -> List[PredictionConfigSchema]:
        """Ensure prediction channel names are unique."""
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate prediction names found: {set(duplicates)}")
        return v
    
    @field_validator('mcp_servers')
    @classmethod
    def validate_unique_mcp_names(cls, v: List[MCPServerConfigSchema]) -> List[MCPServerConfigSchema]:
        """Ensure MCP server names are unique."""
        names = [m.name for m in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate MCP server names found: {set(duplicates)}")
        return v
    
    class Config:
        extra = "forbid"  # Reject unknown fields
