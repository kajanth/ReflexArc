import asyncio
import signal
import sys
import os

from sensors.vision import OpenCVReflex
from sensors.auditory import AudioSensor
from sensors.system_vitals import SystemVitalsSensor
from sensors.circadian import CircadianSensor
from sensors.filesystem import FileSystemSensor
from sensors.network_probe import NetworkProbeSensor
from sensors.threat_detection import ThreatDetectionSensor
from sensors.cognitive_load import CognitiveLoadSensor
from brain_core import NSAOrchestrator
from api_server import NSAApiServer
from sensor_manager import SensorManager

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

async def shutdown(sig, loop, sensor_mgr, heart=None):
    """Cleanup all sensory hardware on exit."""
    print(f"\n[!] Received exit signal {sig.name}...")
    if heart:
        heart.stop()
    sensor_mgr.release_all()
    print("  [✓] All sensors released.")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    print("[!] All senses deactivated. System offline.")
    loop.stop()

async def main():
    # 1. Initialize the Nervous System
    print("🧠 Initializing NSA Orchestrator...")
    brain = NSAOrchestrator()
    
    # Show available providers
    available = brain.router.get_available_providers()
    if not available:
        print("[!] Error: No AI providers configured. Set at least one API key:")
        print("    OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or AWS credentials")
        return
    print(f"   Providers online: {', '.join(available)}")
    print(f"   Strategy: {brain.router._config.get('strategy', 'cheapest')}")
    
    # 2. Initialize Sensor Manager (Layer 0: Peripheral + Internal)
    print("\n--- Initializing Sensory Array ---")
    
    sensor_mgr = SensorManager()
    
    # Peripheral Senses (External World)
    print("👀 Vision (OpenCV)...")
    sensor_mgr.register("vision", OpenCVReflex(sensitivity=20000),
                         emoji="👀", label="Vision", sensor_type="peripheral")
    
    print("👂 Auditory (PyAudio)...")
    sensor_mgr.register("auditory", AudioSensor(rms_threshold=500),
                         emoji="👂", label="Auditory", sensor_type="peripheral")
    
    print("📡 System Vitals (Nociceptors)...")
    sensor_mgr.register("system_vitals", SystemVitalsSensor(),
                         emoji="📡", label="System Vitals", sensor_type="peripheral")
    
    print("📂 Filesystem (Proprioception)...")
    sensor_mgr.register("filesystem", FileSystemSensor(watch_paths=["skills/", "memory/"]),
                         emoji="📂", label="Filesystem", sensor_type="peripheral")
    
    print("🌐 Network Probe (Chemoreceptors)...")
    sensor_mgr.register("network_probe", NetworkProbeSensor(),
                         emoji="🌐", label="Network Probe", sensor_type="peripheral")
    
    # Security Senses
    print("🛡️  Threat Detection (Amygdala)...")
    sensor_mgr.register("threat_detection", ThreatDetectionSensor(),
                         emoji="🛡️", label="Threat Detection", sensor_type="security")
    
    # Internal Senses
    sensor_mgr.register("circadian", brain.circadian,
                         emoji="⏰", label="Circadian Rhythm", sensor_type="internal")
    sensor_mgr.register("cognitive_load", brain.cognitive_load,
                         emoji="📊", label="Cognitive Load", sensor_type="internal")

    status = sensor_mgr.get_status_summary()
    print(f"\n--- {status['total']} Sensors Registered ({status['active']} active, {status['disabled']} disabled) ---")

    # 3. Start API Server (External Stimulus Receptor + Dashboard)
    api_port = int(os.environ.get("NSA_API_PORT", "8080"))
    vision_sensor = sensor_mgr.get_sensor("vision")
    api = NSAApiServer(brain=brain, port=api_port,
                       vision_sensor=vision_sensor, sensor_mgr=sensor_mgr)
    await api.start()

    # 4. Start Digital Heart (Periodic Maintenance Pulse)
    heart = brain.heart
    heart_task = asyncio.create_task(heart.pulse(brain))

    # Handle graceful shutdowns (Ctrl+C)
    loop = asyncio.get_running_loop()
    for sig_type in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig_type, lambda s=sig_type: asyncio.create_task(shutdown(s, loop, sensor_mgr, heart))
        )

    print("\n🚀 NSA SYSTEM ONLINE: Monitoring environment...")
    print(f"❤️  Heartbeat: {heart.interval}s interval")
    print("Status: Zero-Token Idle active.\n")

    try:
        while True:
            # --- LAYER 0: PERIPHERAL MONITORING ($0) ---
            # Only poll ENABLED sensors. Disabled sensors are skipped.
            
            for sense_name, sensor in sensor_mgr.active_sensors():
                try:
                    spiked, description = await sensor.monitor()
                except Exception as e:
                    print(f"[!] Sensor '{sense_name}' error: {e}")
                    continue

                if spiked:
                    brain.circadian.record_spike()
                    
                    print(f"\n⚡ [{sense_name.upper()}] SPIKE: {description}")
                    result = await brain.process_spike(sense_name, description)
                    
                    if result:
                        print(f"[System Outcome]: {result}")
            
            # Prevent CPU from redlining during the sense loop
            await asyncio.sleep(0.1)

    except Exception as e:
        print(f"[!!!] System Crash: {e}")
    finally:
        heart.stop()
        heart_task.cancel()
        sensor_mgr.release_all()

if __name__ == "__main__":
    asyncio.run(main())