# Embedding Model Configuration

## Overview

The ReflexArc NSA system uses a shared embedding model for semantic similarity operations in the RAS (Reticular Activating System) and Hippocampus (memory) layers. The embedding model is now configurable, allowing you to customize the model, caching behavior, and device placement.

## Benefits

- **Memory Efficiency**: Single shared model instance reduces memory footprint by ~50%
- **Performance**: Lazy loading avoids impacting startup time
- **Flexibility**: Choose different models based on your needs
- **Device Control**: Run on CPU, GPU (CUDA), or Apple Silicon (MPS)
- **Cost Optimization**: Maintains the $0.50/day operational cost target

## Configuration

### In Brain Configuration File

Add the `embedding_model` section under `brain` in your configuration file (`config/brain.yaml` or `config/brain.json`):

#### YAML Format

```yaml
brain:
  name: "DevOps Brain"
  description: "Infrastructure monitoring and autonomous incident response"
  heartbeat_interval: 30
  prediction_interval: 120
  goal_eval_interval: 300
  
  # Embedding model caching configuration
  embedding_model:
    model_name: "all-MiniLM-L6-v2"      # SentenceTransformer model name or path
    cache_enabled: true                  # Enable in-memory model caching
    device: null                         # Device: cpu, cuda, mps, or null for auto
```

#### JSON Format

```json
{
  "brain": {
    "name": "DevOps Brain",
    "description": "Infrastructure monitoring and autonomous incident response",
    "heartbeat_interval": 30,
    "prediction_interval": 120,
    "goal_eval_interval": 300,
    "embedding_model": {
      "model_name": "all-MiniLM-L6-v2",
      "cache_enabled": true,
      "device": null
    }
  }
}
```

### Configuration Parameters

| Parameter | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `model_name` | string | `"all-MiniLM-L6-v2"` | Any SentenceTransformer model | Model name from Hugging Face or local path |
| `cache_enabled` | boolean | `true` | `true`, `false` | Enable in-memory model caching |
| `device` | string or null | `null` | `"cpu"`, `"cuda"`, `"mps"`, `null` | Device to run model on (null = auto-detect) |

### Validation Rules

- `model_name` must be a valid SentenceTransformer model name or path
- `cache_enabled` must be a boolean value
- `device` must be one of: `"cpu"`, `"cuda"`, `"mps"`, or `null`

If these rules are violated, the system will fail at startup with a clear error message.

## How It Works

### Model Lifecycle

1. **Configuration**: Model settings are loaded from brain configuration at startup
2. **Lazy Loading**: Model is not loaded until first use (preserves fast startup)
3. **Caching**: If `cache_enabled=true`, model is kept in memory for reuse
4. **Sharing**: Single model instance is shared across RAS and Hippocampus layers
5. **Cleanup**: Model is released during shutdown to free memory

### Caching Behavior

#### With Caching Enabled (Default)

```python
# First call loads the model
model1 = get_embedding_model()  # Loads model into memory

# Subsequent calls reuse the cached model
model2 = get_embedding_model()  # Returns cached model (same instance)
```

#### With Caching Disabled

```python
# Each call creates a new model instance
model1 = get_embedding_model()  # Creates new model
model2 = get_embedding_model()  # Creates another new model
```

**Note**: Disabling caching increases memory usage and is generally not recommended unless you have specific requirements.

## Usage Examples

### Default Configuration (Recommended)

Uses the lightweight `all-MiniLM-L6-v2` model with caching enabled:

```yaml
embedding_model:
  model_name: "all-MiniLM-L6-v2"
  cache_enabled: true
  device: null  # Auto-detect best device
```

**Best for**: Most use cases, balances speed and accuracy.

### High-Accuracy Model

Use a larger, more accurate model:

```yaml
embedding_model:
  model_name: "all-mpnet-base-v2"
  cache_enabled: true
  device: null
```

**Best for**: When semantic accuracy is critical.
**Trade-off**: Larger memory footprint (~420MB vs ~80MB), slower inference.

### GPU Acceleration

Force model to run on CUDA GPU:

```yaml
embedding_model:
  model_name: "all-MiniLM-L6-v2"
  cache_enabled: true
  device: "cuda"
```

**Best for**: Systems with NVIDIA GPU, high-throughput scenarios.
**Requirements**: CUDA-capable GPU, PyTorch with CUDA support.

### Apple Silicon Optimization

Use Metal Performance Shaders on Apple Silicon:

```yaml
embedding_model:
  model_name: "all-MiniLM-L6-v2"
  cache_enabled: true
  device: "mps"
```

**Best for**: M1/M2/M3 Mac systems.
**Requirements**: PyTorch with MPS support.

### CPU-Only Mode

Force CPU execution (useful for debugging or resource-constrained environments):

```yaml
embedding_model:
  model_name: "all-MiniLM-L6-v2"
  cache_enabled: true
  device: "cpu"
```

**Best for**: Systems without GPU, debugging, or when GPU is reserved for other tasks.

### Custom Local Model

Use a custom fine-tuned model:

```yaml
embedding_model:
  model_name: "/path/to/custom/model"
  cache_enabled: true
  device: null
```

**Best for**: Domain-specific applications with custom-trained models.

## Model Selection Guide

### Available Models

Popular SentenceTransformer models (from Hugging Face):

| Model | Size | Dimensions | Speed | Accuracy | Use Case |
|-------|------|------------|-------|----------|----------|
| `all-MiniLM-L6-v2` | 80MB | 384 | Fast | Good | Default, general purpose |
| `all-MiniLM-L12-v2` | 120MB | 384 | Medium | Better | Balanced accuracy/speed |
| `all-mpnet-base-v2` | 420MB | 768 | Slow | Best | High accuracy needed |
| `paraphrase-MiniLM-L6-v2` | 80MB | 384 | Fast | Good | Paraphrase detection |
| `multi-qa-MiniLM-L6-cos-v1` | 80MB | 384 | Fast | Good | Question answering |

### Selection Criteria

**Choose `all-MiniLM-L6-v2` (default) if:**
- You want fast startup and low memory usage
- General-purpose semantic similarity is sufficient
- You're optimizing for cost ($0.50/day target)

**Choose `all-mpnet-base-v2` if:**
- Semantic accuracy is critical
- You have sufficient memory (>2GB available)
- Slightly slower inference is acceptable

**Choose domain-specific models if:**
- You have specialized use cases (QA, paraphrase, etc.)
- You've fine-tuned a model for your domain

## Device Selection Guide

### Auto-Detection (Recommended)

```yaml
device: null
```

The system will automatically select the best available device:
1. CUDA GPU (if available)
2. MPS (Apple Silicon, if available)
3. CPU (fallback)

### Manual Device Selection

**Use `"cuda"` when:**
- You have an NVIDIA GPU
- You want maximum throughput
- Multiple models are running (dedicate GPU to embeddings)

**Use `"mps"` when:**
- You're on Apple Silicon (M1/M2/M3)
- You want GPU acceleration on Mac

**Use `"cpu"` when:**
- No GPU is available
- GPU is reserved for other tasks
- Debugging or testing

## Monitoring

### Logging

The embedding model logs important events:

```
[info] embedding_model_configured - Configuration applied
[info] loading_embedding_model - Model loading started
[info] cleaning_up_embedding_model - Model cleanup during shutdown
[warning] embedding_model_already_loaded - Configuration changed after model loaded
```

### Memory Usage

Monitor memory usage to ensure the model fits in available RAM:

```bash
# Check memory usage on Linux
ps aux | grep python

# Check memory usage on macOS
top -pid $(pgrep -f "python.*main.py")
```

Expected memory usage:
- `all-MiniLM-L6-v2`: ~80-100MB
- `all-mpnet-base-v2`: ~420-450MB

## Performance Tuning

### Startup Time

The embedding model uses lazy loading, so it doesn't impact startup time. The model is loaded on first use (typically when the first spike is processed).

### Inference Speed

Typical inference times (per encoding):

| Device | Model | Time per Encoding |
|--------|-------|-------------------|
| CPU (Intel i7) | all-MiniLM-L6-v2 | ~10-20ms |
| CPU (Apple M1) | all-MiniLM-L6-v2 | ~5-10ms |
| CUDA (RTX 3080) | all-MiniLM-L6-v2 | ~2-5ms |
| MPS (M1 Pro) | all-MiniLM-L6-v2 | ~3-8ms |

### Batch Processing

For high-throughput scenarios, consider batching embeddings:

```python
# Instead of encoding one at a time
embeddings = [model.encode(text) for text in texts]

# Batch encode for better performance
embeddings = model.encode(texts)  # Processes all at once
```

## Troubleshooting

### Issue: Model not found

**Error**: `OSError: Can't load model 'model-name'`

**Solution**: 
- Verify model name is correct (check [Hugging Face](https://huggingface.co/models?library=sentence-transformers))
- Ensure internet connection for first download
- Check local path if using custom model

### Issue: CUDA out of memory

**Error**: `RuntimeError: CUDA out of memory`

**Solution**:
- Switch to CPU: `device: "cpu"`
- Use smaller model: `model_name: "all-MiniLM-L6-v2"`
- Close other GPU applications

### Issue: MPS not available

**Error**: `RuntimeError: MPS device not available`

**Solution**:
- Verify you're on Apple Silicon (M1/M2/M3)
- Update PyTorch to version with MPS support
- Use auto-detection: `device: null`

### Issue: Slow inference on CPU

**Symptom**: Embeddings take >100ms per encoding

**Solution**:
- Enable GPU if available: `device: "cuda"` or `device: "mps"`
- Use smaller model: `model_name: "all-MiniLM-L6-v2"`
- Ensure caching is enabled: `cache_enabled: true`

### Issue: Configuration not taking effect

**Symptom**: Model still uses old configuration

**Solution**:
- Restart the application (configuration is loaded at startup)
- Check for typos in configuration file
- Verify configuration file is being loaded (check logs)

## Backward Compatibility

The embedding model configuration is fully backward compatible:

- If no `embedding_model` section is specified, defaults are used
- Existing code works without modification
- The model is still shared across components

## Implementation Details

### Architecture

The shared embedding model is implemented in `utils/embeddings.py`:

- `configure_embedding_model()`: Sets model configuration
- `get_embedding_model()`: Returns shared model instance (lazy loading)
- `cleanup_embedding_model()`: Releases model during shutdown

### Used By

The embedding model is used by:

1. **RAS Layer** (`brain_core.py`): Novelty detection via semantic similarity
2. **Hippocampus** (`memory/hippocampus.py`): Memory storage and retrieval

### Thread Safety

The embedding model is thread-safe for inference:
- SentenceTransformer models are read-only after loading
- Multiple async operations can use the model concurrently
- No locking is required for inference

## Future Enhancements

Potential improvements for future versions:

- Model warm-up on startup (optional)
- Automatic model selection based on available resources
- Model quantization for reduced memory usage
- Support for custom embedding dimensions
- Metrics export (inference time, cache hits)

## References

- [SentenceTransformers Documentation](https://www.sbert.net/)
- [Hugging Face Model Hub](https://huggingface.co/models?library=sentence-transformers)
- [PyTorch Device Management](https://pytorch.org/docs/stable/tensor_attributes.html#torch.device)
- [Apple MPS Backend](https://pytorch.org/docs/stable/notes/mps.html)
