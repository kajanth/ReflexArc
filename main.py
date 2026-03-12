import asyncio
import signal
import sys
import os

# Local Imports
from brain_core import NSAOrchestrator
from api_server import NSAApiServer
from sensor_manager import SensorManager
from plugin_loader import BrainConfig
from event_bus import event_bus
from utils.logging_config import get_logger
from utils.secrets_manager import validate_startup_secrets

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

logger = get_logger(__name__)

async def shutdown(sig, loop, sensor_mgr, brain=None, heart=None, mcp_manager=None, adk_process=None):
    """Cleanup all sensory hardware and sub-processes on exit."""
    logger.info("shutdown_initiated", signal=sig.name)
    
    # Stop event bus cleanup
    event_bus.stop_cleanup()
    
    # Stop basal ganglia flush and do final save
    if brain and brain.basal_ganglia:
        await brain.basal_ganglia.stop_periodic_flush()
    
    if heart:
        heart.stop()
    if mcp_manager:
        await mcp_manager.stop_all()
    if brain and brain.memory:
        await brain.memory.close()
        logger.info("hippocampus_closed")
    
    # Cleanup SentenceTransformer models
    if brain:
        brain.cleanup_models()
    
    # Cleanup shared embedding models
    from utils.embeddings import cleanup_embedding_model
    from dream_engine import cleanup_dream_model
    cleanup_embedding_model()
    cleanup_dream_model()
    logger.info("embedding_models_cleaned_up")
    
    if adk_process:
        try:
            adk_process.terminate()
            logger.info("adk_ui_terminated")
        except Exception as e:
            logger.warning("adk_ui_terminate_failed", error=str(e))
            
    sensor_mgr.release_all()
    logger.info("sensors_released")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logger.info("shutdown_complete", message="All senses deactivated")
    loop.stop()

async def _legacy_register_sensors(sensor_mgr, brain):
    """Fallback: hardcoded sensor registration (backward compatible)."""
    from sensors.vision import OpenCVReflex
    from sensors.auditory import AudioSensor
    from sensors.system_vitals import SystemVitalsSensor
    from sensors.filesystem import FileSystemSensor
    from sensors.network_probe import NetworkProbeSensor
    from sensors.threat_detection import ThreatDetectionSensor

    sensor_mgr.register("vision", OpenCVReflex(sensitivity=20000),
                         emoji="👀", label="Vision", sensor_type="peripheral")
    sensor_mgr.register("auditory", AudioSensor(rms_threshold=500),
                         emoji="👂", label="Auditory", sensor_type="peripheral")
    sensor_mgr.register("system_vitals", SystemVitalsSensor(),
                         emoji="📡", label="System Vitals", sensor_type="peripheral")
    sensor_mgr.register("filesystem", FileSystemSensor(watch_paths=["skills/", "memory/"]),
                         emoji="📂", label="Filesystem", sensor_type="peripheral")
    sensor_mgr.register("network_probe", NetworkProbeSensor(),
                         emoji="🌐", label="Network Probe", sensor_type="peripheral")
    sensor_mgr.register("threat_detection", ThreatDetectionSensor(),
                         emoji="🛡️", label="Threat Detection", sensor_type="security")
    sensor_mgr.register("circadian", brain.circadian,
                         emoji="⏰", label="Circadian Rhythm", sensor_type="internal")
    sensor_mgr.register("cognitive_load", brain.cognitive_load,
                         emoji="📊", label="Cognitive Load", sensor_type="internal")

async def main():
    # 0. Validate API keys and secrets
    if not validate_startup_secrets():
        sys.exit(1)
    
    # 1. Load Brain Config
    config = BrainConfig()
    logger.info("brain_profile_loaded", name=config.name)

    # 2. Configure embedding model before first use
    from utils.embeddings import configure_embedding_model
    embedding_config = config.config.get("brain", {}).get("embedding_model", {})
    if embedding_config:
        configure_embedding_model(
            model_name=embedding_config.get("model_name", "all-MiniLM-L6-v2"),
            cache_enabled=embedding_config.get("cache_enabled", True),
            device=embedding_config.get("device")
        )
        logger.info("embedding_model_configured",
                   model_name=embedding_config.get("model_name", "all-MiniLM-L6-v2"),
                   cache_enabled=embedding_config.get("cache_enabled", True),
                   device=embedding_config.get("device", "auto"))

    # 2. Initialize the Nervous System with database configuration
    logger.info("initializing_orchestrator")
    
    # Extract database config from brain config
    db_config = config.config.get("brain", {}).get("database", {})
    db_path = db_config.get("path", "memory/long_term_memory.db")
    min_pool_size = db_config.get("min_pool_size", 1)
    max_pool_size = db_config.get("max_pool_size", 5)
    
    # Extract MCP tool timeout from brain config
    mcp_tool_timeout = config.mcp_tool_timeout
    
    brain = NSAOrchestrator(
        db_path=db_path,
        min_pool_size=min_pool_size,
        max_pool_size=max_pool_size,
        mcp_tool_timeout=mcp_tool_timeout
    )
    
    # Initialize Hippocampus async connection
    await brain.memory._ensure_initialized()
    
    # Log database pool configuration
    pool_stats = brain.memory.get_pool_stats()
    logger.info("database_pool_configured",
               db_path=db_path,
               pool_stats=pool_stats)

    # Apply config intervals
    brain.heart.interval = config.heartbeat_interval
    brain.prefrontal_cortex.eval_interval = config.goal_eval_interval
    brain.predictive_cortex.prediction_interval = config.prediction_interval

    # Show available providers
    available = brain.router.get_available_providers()
    if not available:
        logger.error("no_providers_configured",
                    message="Set at least one API key")
        return
    logger.info("providers_online",
               providers=available,
               strategy=brain.router._config.get('strategy', 'cheapest'))
    
    # 2. Initialize Sensor Manager (config-driven or legacy)
    logger.info("initializing_sensors")
    sensor_mgr = SensorManager()

    if config.config.get("sensors"):
        config.build_sensors(brain, sensor_mgr)
    else:
        logger.warning("no_sensor_config", message="Using legacy hardcoded registration")
        await _legacy_register_sensors(sensor_mgr, brain)

    # 2.5 Apply custom prediction channels (if configured)
    custom_channels = config.build_prediction_channels()
    if custom_channels:
        brain.predictive_cortex.channels = custom_channels
        logger.info("prediction_channels_loaded", count=len(custom_channels))

    # 2.6 Apply custom measurers for goals (if configured)
    custom_measurers = config.build_custom_measurers()
    if custom_measurers:
        from prefrontal_cortex import MEASURERS
        MEASURERS.update(custom_measurers)
        logger.info("custom_measurers_loaded", count=len(custom_measurers))

    status = sensor_mgr.get_status_summary()
    logger.info("sensors_registered",
               total=status['total'],
               active=status['active'],
               disabled=status['disabled'])

    # 3. Start API Server (External Stimulus Receptor + Dashboard)
    api_port = int(os.environ.get("NSA_API_PORT", "8080"))
    vision_sensor = sensor_mgr.get_sensor("vision")
    
    # Suppress noisy aiohttp access logs if quiet_web_logs is enabled
    brain_cfg = config.config.get("brain", {})
    quiet_web_logs = brain_cfg.get("quiet_web_logs", False)
    if quiet_web_logs:
        import logging
        logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
        logger.info("quiet_web_logs_enabled", message="HTTP access log suppressed")

    api = NSAApiServer(brain=brain, port=api_port,
                       vision_sensor=vision_sensor, sensor_mgr=sensor_mgr)
    await api.start()

    # 4. Start Digital Heart (Periodic Maintenance Pulse)
    heart = brain.heart
    heart_task = asyncio.create_task(heart.pulse(brain))

    # 5. Start Prefrontal Cortex (Goal Evaluation Loop)
    pfc = brain.prefrontal_cortex
    pfc_task = asyncio.create_task(pfc.evaluate_loop())

    # 6. Start Predictive Cortex (Anticipatory Sensing Loop)
    pred = brain.predictive_cortex
    pred_task = asyncio.create_task(pred.prediction_loop())

    # 7. Start MCP Servers (if configured)
    mcp_manager, mcp_start_coro = config.build_mcp_servers()
    if mcp_start_coro:
        await mcp_start_coro
    brain.mcp_manager = mcp_manager  # Attach to brain so Cortex can access it

    # 8. Start Event Bus Cleanup (Periodic Memory Management)
    event_bus.start_cleanup()
    logger.info("event_bus_cleanup_started",
               retention_seconds=event_bus._retention_seconds,
               history_max=event_bus._history.maxlen)

    # 9. Start Basal Ganglia Periodic Flush (Write-Behind Caching)
    await brain.basal_ganglia.start_periodic_flush()

    # 10. Start Daytime Evolution Loop (if configured)
    evolve_task = None
    if brain_cfg.get("enable_daytime_evolution", False):
        evolve_task = asyncio.create_task(brain.dream_engine.daytime_evolution_loop(interval_seconds=1200)) # Default 20 mins

    adk_process = None
    # Check both brain.yaml config and env var (env var takes precedence)
    enable_adk_ui = brain_cfg.get("enable_adk_ui", False)
    enable_adk_ui = enable_adk_ui or os.environ.get("NSA_ENABLE_ADK_UI", "").lower() == "true"
    if enable_adk_ui:
        logger.info("starting_adk_ui", message="Attempting to start local ADK Developer Server via 'adk web'")
        import subprocess
        try:
            adk_agents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adk_agents")
            adk_session_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", ".adk", "session.db")
            adk_session_uri = f"sqlite:///{adk_session_db}"
            adk_process = subprocess.Popen(
                [
                    "adk", "web", adk_agents_dir,
                    "--session_service_uri", adk_session_uri,
                    "--reload_agents",
                ], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            logger.info("adk_ui_started", url="http://localhost:8000",
                        agents_dir=adk_agents_dir, session_db=adk_session_db)
        except Exception as e:
            logger.warning("adk_ui_startup_failed", error=str(e), message="Is google-adk installed and 'adk' in PATH?")

    # Handle graceful shutdowns (Ctrl+C)
    loop = asyncio.get_running_loop()
    for sig_type in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig_type, lambda s=sig_type: asyncio.create_task(
                shutdown(s, loop, sensor_mgr, brain, heart, mcp_manager, adk_process)
            )
        )

    logger.info("system_online",
               heartbeat_interval=heart.interval,
               pfc_eval_interval=pfc.eval_interval,
               predictive_interval=pred.prediction_interval,
               mcp_servers=len(mcp_manager.servers) if mcp_manager.servers else 0,
               status="zero_token_idle")

    try:
        while True:
            # --- LAYER 0: PERIPHERAL MONITORING ($0) ---
            # Monitor all enabled sensors in parallel
            
            results = await sensor_mgr.monitor_all_parallel()
            
            for sense_name, spiked, description in results:
                if spiked:
                    brain.circadian.record_spike()
                    
                    logger.info("spike_detected",
                               sense_type=sense_name,
                               description_preview=description[:100])
                    result = await brain.process_spike(sense_name, description)
                    
                    if result:
                        logger.info("system_outcome",
                                   result_preview=result[:200])
            
            # Prevent CPU from redlining during the sense loop
            await asyncio.sleep(0.1)

    except Exception as e:
        logger.critical("system_crash", error=str(e), exc_info=True)
    finally:
        heart.stop()
        heart_task.cancel()
        pfc_task.cancel()
        pred_task.cancel()
        if evolve_task:
            evolve_task.cancel()
        sensor_mgr.release_all()
        await brain.memory.close()
        await mcp_manager.stop_all()
        
        # Cleanup SentenceTransformer models
        brain.cleanup_models()
        from utils.embeddings import cleanup_embedding_model
        from dream_engine import cleanup_dream_model
        cleanup_embedding_model()
        cleanup_dream_model()
        logger.info("embedding_models_cleaned_up")

if __name__ == "__main__":
    asyncio.run(main())