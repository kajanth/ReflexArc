"""
🧠 Shared Embedding Model Utility

Provides a singleton embedding model instance shared across all components
to reduce memory footprint and improve performance.
"""

import os
from sentence_transformers import SentenceTransformer
from typing import Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Configure HuggingFace cache directory
# This ensures models are cached locally and not re-downloaded
HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")
os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
os.environ.setdefault("TRANSFORMERS_CACHE", HF_CACHE_DIR)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", HF_CACHE_DIR)

# Shared embedding model (loaded lazily)
_embedding_model: Optional[SentenceTransformer] = None
_model_config: dict = {
    "model_name": "all-MiniLM-L6-v2",
    "cache_enabled": True,
    "device": None
}


def configure_embedding_model(model_name: str = "all-MiniLM-L6-v2", 
                              cache_enabled: bool = True,
                              device: Optional[str] = None) -> None:
    """
    Configure the embedding model settings.
    
    Must be called before first use of get_embedding_model() to take effect.
    If called after model is loaded, will log a warning.
    
    Args:
        model_name: SentenceTransformer model name or path
        cache_enabled: Whether to cache the model in memory
        device: Device to run model on (cpu, cuda, mps, or None for auto)
    """
    global _model_config, _embedding_model
    
    if _embedding_model is not None:
        logger.warning("embedding_model_already_loaded",
                      message="Configuration change will not affect already loaded model",
                      current_model=_model_config["model_name"],
                      new_model=model_name)
    
    _model_config = {
        "model_name": model_name,
        "cache_enabled": cache_enabled,
        "device": device
    }
    
    logger.info("embedding_model_configured",
               model_name=model_name,
               cache_enabled=cache_enabled,
               device=device or "auto")


def get_embedding_model() -> SentenceTransformer:
    """
    Get or create the shared embedding model.
    
    Uses lazy loading to avoid impacting startup time. The model is loaded
    on first use and cached for subsequent calls (if caching is enabled).
    
    Models are cached to ~/.cache/huggingface/hub to avoid re-downloading.
    
    Returns:
        Shared SentenceTransformer model instance
    """
    global _embedding_model, _model_config
    
    # If caching is disabled, always create a new model
    if not _model_config["cache_enabled"]:
        logger.info("loading_embedding_model_no_cache",
                   model=_model_config["model_name"],
                   device=_model_config["device"] or "auto",
                   cache_dir=HF_CACHE_DIR)
        return SentenceTransformer(
            _model_config["model_name"], 
            device=_model_config["device"],
            cache_folder=HF_CACHE_DIR
        )
    
    # Otherwise use cached model
    if _embedding_model is None:
        logger.info("loading_embedding_model", 
                   model=_model_config["model_name"],
                   device=_model_config["device"] or "auto",
                   purpose="shared_singleton",
                   cache_dir=HF_CACHE_DIR)
        _embedding_model = SentenceTransformer(
            _model_config["model_name"],
            device=_model_config["device"],
            cache_folder=HF_CACHE_DIR
        )
    return _embedding_model


def cleanup_embedding_model() -> None:
    """
    Release the shared embedding model resources.
    
    Called during shutdown to free memory and ensure clean exit.
    Should be called once during application shutdown.
    """
    global _embedding_model
    if _embedding_model is not None:
        logger.info("cleaning_up_embedding_model", 
                   model=_model_config["model_name"])
        del _embedding_model
        _embedding_model = None
