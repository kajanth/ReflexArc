"""
🌐 NSA API Server — External Stimulus Receptor + Live Dashboard
Layer 0 — HTTP endpoint that external systems can poke
to inject events directly into the neural cascade.

Also serves the real-time web dashboard with MJPEG video streaming
and WebSocket-based live event feeds.

Endpoints:
    GET  /dashboard        — Live web dashboard
    GET  /stream/video     — MJPEG video stream from vision sensor
    GET  /ws/live          — WebSocket for real-time events
    GET  /stats            — Token spend & latency stats
    POST /spike            — Inject a sensory spike
    POST /spike/threat     — Inject a high-priority threat spike
    POST /spike/metric     — Inject a system metric observation
    GET  /status           — System health + provider status
    GET  /skills           — List available skills + templates
    GET  /memories/recent  — Last N memories from hippocampus
    POST /skill/run        — Manually trigger a skill
    GET  /health           — Health check
"""

import asyncio
import json
import os
import time
from aiohttp import web

from event_bus import event_bus


class NSAApiServer:
    """
    HTTP API server that acts as an external sensor + dashboard host.
    """

    def __init__(self, brain, host="0.0.0.0", port=8080, vision_sensor=None, sensor_mgr=None):
        """
        Args:
            brain: NSAOrchestrator instance.
            host: Bind address.
            port: Listen port.
            vision_sensor: OpenCVReflex instance for video streaming.
            sensor_mgr: SensorManager instance for sensor toggling.
        """
        self.brain = brain
        self.host = host
        self.port = port
        self.vision_sensor = vision_sensor
        self.sensor_mgr = sensor_mgr
        self.app = web.Application()
        self._setup_routes()
        self._spike_count = 0
        self._start_time = time.time()

    def _setup_routes(self):
        """Register all API routes."""
        # Dashboard
        self.app.router.add_get("/dashboard", self._handle_dashboard)
        self.app.router.add_get("/stream/video", self._handle_video_stream)
        self.app.router.add_get("/ws/live", self._handle_websocket)
        self.app.router.add_get("/stats", self._handle_stats)

        # Spike injection
        self.app.router.add_post("/spike", self._handle_spike)
        self.app.router.add_post("/spike/threat", self._handle_threat_spike)
        self.app.router.add_post("/spike/metric", self._handle_metric_spike)

        # Query
        self.app.router.add_get("/status", self._handle_status)
        self.app.router.add_get("/skills", self._handle_skills)
        self.app.router.add_get("/memories/recent", self._handle_memories)
        self.app.router.add_post("/skill/run", self._handle_run_skill)
        self.app.router.add_get("/health", self._handle_health)

        # Sensor Controls
        self.app.router.add_get("/sensors", self._handle_sensors)
        self.app.router.add_post("/sensor/toggle", self._handle_sensor_toggle)

        # Dream Cycle
        self.app.router.add_get("/dreams/recent", self._handle_dreams)
        self.app.router.add_get("/patterns", self._handle_patterns)
        self.app.router.add_post("/dream/trigger", self._handle_dream_trigger)

        # Goal System (Prefrontal Cortex)
        self.app.router.add_get("/goals", self._handle_goals)
        self.app.router.add_post("/goal", self._handle_create_goal)
        self.app.router.add_delete("/goal", self._handle_delete_goal)
        self.app.router.add_post("/goal/evaluate", self._handle_goal_evaluate)

        # Predictions (Predictive Cortex)
        self.app.router.add_get("/predictions", self._handle_predictions)
        self.app.router.add_get("/predictions/history", self._handle_prediction_history)

    # ──────────────────────────────────────────────
    # Dashboard Endpoints
    # ──────────────────────────────────────────────

    async def _handle_dashboard(self, request):
        """GET /dashboard — Serve the live dashboard HTML."""
        html_path = os.path.join(os.path.dirname(__file__), "web", "dashboard.html")
        if os.path.exists(html_path):
            return web.FileResponse(html_path)
        return web.Response(text="Dashboard HTML not found", status=404)

    async def _handle_video_stream(self, request):
        """GET /stream/video — MJPEG stream from vision sensor."""
        if not self.vision_sensor:
            return web.Response(text="No vision sensor available", status=503)

        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        await response.prepare(request)

        try:
            while True:
                frame = self.vision_sensor.get_frame()
                if frame is not None:
                    import cv2
                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    data = jpeg.tobytes()

                    await response.write(
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        b'Content-Length: ' + str(len(data)).encode() + b'\r\n'
                        b'\r\n' + data + b'\r\n'
                    )
                await asyncio.sleep(0.066)  # ~15 fps
        except (ConnectionResetError, asyncio.CancelledError):
            pass

        return response

    async def _handle_websocket(self, request):
        """GET /ws/live — WebSocket for real-time event streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Send event history to new connections
        history = event_bus.get_history(30)
        for event in history:
            try:
                await ws.send_json(event)
            except Exception:
                break

        # Subscribe to live events
        queue = event_bus.subscribe()
        try:
            while not ws.closed:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    await ws.send_json(event)
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await ws.ping()
                except Exception:
                    break
        finally:
            event_bus.unsubscribe(queue)

        return ws

    async def _handle_stats(self, request):
        """GET /stats — Token spend and latency stats."""
        try:
            with open("memory/stats.json", "r") as f:
                stats = json.load(f)
            return web.json_response(stats)
        except Exception:
            return web.json_response({"total_spent": 0, "calls": 0, "avg_latency": 0})

    # ──────────────────────────────────────────────
    # Spike Injection Endpoints
    # ──────────────────────────────────────────────

    async def _handle_spike(self, request):
        """POST /spike — Inject a generic sensory spike."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        description = data.get("description")
        if not description:
            return web.json_response({"error": "Missing required field: description"}, status=400)

        sense_type = data.get("sense_type", "api")
        priority = data.get("priority", "normal")
        tagged_desc = f"[API/{priority.upper()}] {description}"

        self._spike_count += 1
        event_bus.publish("spike", {
            "sense_type": sense_type,
            "description": tagged_desc,
            "priority": priority,
            "source": "api",
            "spike_id": self._spike_count,
        })

        try:
            result = await self.brain.process_spike(sense_type, tagged_desc)
            return web.json_response({
                "status": "processed",
                "sense_type": sense_type,
                "priority": priority,
                "result": str(result) if result else "Filtered by RAS (habituation)",
                "spike_id": self._spike_count,
            })
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    async def _handle_threat_spike(self, request):
        """POST /spike/threat — Inject a high-priority threat spike."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        description = data.get("description")
        if not description:
            return web.json_response({"error": "Missing required field: description"}, status=400)

        source = data.get("source", "external")
        tagged_desc = f"[THREAT/{source}] {description}"

        self._spike_count += 1
        event_bus.publish("spike", {
            "sense_type": "threat_api",
            "description": tagged_desc,
            "priority": "critical",
            "source": source,
            "spike_id": self._spike_count,
        })

        try:
            result = await self.brain.process_spike("threat_api", tagged_desc)
            return web.json_response({
                "status": "processed",
                "priority": "critical",
                "result": str(result) if result else "Filtered by RAS",
                "spike_id": self._spike_count,
            })
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    async def _handle_metric_spike(self, request):
        """POST /spike/metric — Inject a system metric observation."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        metric = data.get("metric")
        value = data.get("value")
        if not metric or value is None:
            return web.json_response({"error": "Missing required fields: metric, value"}, status=400)

        unit = data.get("unit", "")
        source = data.get("source", "external")
        threshold = data.get("threshold")

        description = f"[METRIC/{source}] {metric}: {value}{unit}"
        if threshold is not None:
            description += f" (threshold: {threshold}{unit}, BREACHED)"

        self._spike_count += 1
        event_bus.publish("spike", {
            "sense_type": "metric_api",
            "description": description,
            "metric": metric,
            "value": value,
            "source": source,
            "spike_id": self._spike_count,
        })

        try:
            result = await self.brain.process_spike("metric_api", description)
            return web.json_response({
                "status": "processed",
                "metric": metric,
                "value": value,
                "result": str(result) if result else "Filtered by RAS",
                "spike_id": self._spike_count,
            })
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    # ──────────────────────────────────────────────
    # Query Endpoints
    # ──────────────────────────────────────────────

    async def _handle_status(self, request):
        """GET /status — Full system status."""
        uptime = time.time() - self._start_time
        internal_state = self.brain._get_internal_state()
        router_status = self.brain.router.get_status()

        status = {
            "status": "online",
            "uptime_seconds": round(uptime, 1),
            "uptime_human": _format_uptime(uptime),
            "spikes_received": self._spike_count,
            "dashboard_viewers": event_bus.subscriber_count,
            "internal_state": internal_state,
            "circadian_phase": self.brain.circadian.get_phase(),
            "cognitive_load": self.brain.cognitive_load.get_metrics(),
            "providers": router_status,
        }

        if self.sensor_mgr:
            status["sensors"] = self.sensor_mgr.all_sensors()
            status["sensor_summary"] = self.sensor_mgr.get_status_summary()

        return web.json_response(status)

    async def _handle_skills(self, request):
        """GET /skills — List all available skills and templates."""
        skills = []
        for f in sorted(os.listdir("skills")):
            if f.endswith(".py") and f != "__init__.py":
                skills.append(f.replace(".py", ""))

        templates = self.brain.template_engine.get_available_templates()

        return web.json_response({
            "python_skills": skills,
            "ai_templates": templates,
            "total": len(skills) + len(templates),
        })

    async def _handle_memories(self, request):
        """GET /memories/recent?limit=10 — Recent memories."""
        limit = int(request.query.get("limit", "10"))
        limit = min(limit, 50)

        try:
            import sqlite3
            db_path = "memory/long_term_memory.db"
            if not os.path.exists(db_path):
                return web.json_response({"memories": [], "count": 0})

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, sense_type, description "
                "FROM memories ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()

            memories = [
                {"timestamp": r[0], "sense_type": r[1], "description": r[2]}
                for r in rows
            ]
            return web.json_response({"memories": memories, "count": len(memories)})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_run_skill(self, request):
        """POST /skill/run — Manually trigger a skill."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        skill_name = data.get("skill")
        if not skill_name:
            return web.json_response({"error": "Missing required field: skill"}, status=400)

        skill_data = data.get("data", "Triggered via API")

        try:
            import importlib
            module = importlib.import_module(f"skills.{skill_name}")
            importlib.reload(module)
            result = module.run(skill_data)

            event_bus.publish("reflex_exec", {
                "skill": skill_name,
                "result": str(result)[:200],
                "source": "api",
            })

            return web.json_response({
                "status": "executed",
                "skill": skill_name,
                "result": str(result),
            })
        except ModuleNotFoundError:
            return web.json_response({"error": f"Skill '{skill_name}' not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": f"Skill execution failed: {e}"}, status=500)

    async def _handle_health(self, request):
        """GET /health — Simple health check."""
        return web.json_response({
            "status": "healthy",
            "uptime": time.time() - self._start_time,
            "dashboard_viewers": event_bus.subscriber_count,
        })

    # ──────────────────────────────────────────────
    # Server Lifecycle
    # ──────────────────────────────────────────────

    async def start(self):
        """Start the API server as a background task."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"🌐 API Server listening on http://{self.host}:{self.port}")
        print(f"   Dashboard:  http://localhost:{self.port}/dashboard")
        print(f"   API:        POST /spike, /spike/threat, /spike/metric")
        print(f"   Sensors:    GET  /sensors  |  POST /sensor/toggle")
        print(f"   Query:      GET  /status, /skills, /memories/recent, /health")
        print(f"   Execute:    POST /skill/run")

    # ──────────────────────────────────────────────
    # Sensor Control Endpoints
    # ──────────────────────────────────────────────

    async def _handle_sensors(self, request):
        """GET /sensors — List all sensors with their enabled/disabled state."""
        if not self.sensor_mgr:
            return web.json_response({"error": "No sensor manager"}, status=503)

        return web.json_response({
            "sensors": self.sensor_mgr.all_sensors(),
            "summary": self.sensor_mgr.get_status_summary(),
        })

    async def _handle_sensor_toggle(self, request):
        """POST /sensor/toggle — Enable or disable a sensor."""
        if not self.sensor_mgr:
            return web.json_response({"error": "No sensor manager"}, status=503)

        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        sensor_name = data.get("sensor")
        if not sensor_name:
            return web.json_response({"error": "Missing required field: sensor"}, status=400)

        action = data.get("action", "toggle")  # "enable", "disable", or "toggle"

        if action == "enable":
            ok = self.sensor_mgr.enable(sensor_name)
        elif action == "disable":
            ok = self.sensor_mgr.disable(sensor_name)
        else:
            new_state = self.sensor_mgr.toggle(sensor_name)
            ok = new_state is not None

        if not ok:
            return web.json_response({"error": f"Sensor '{sensor_name}' not found"}, status=404)

        return web.json_response({
            "status": "ok",
            "sensor": sensor_name,
            "enabled": self.sensor_mgr.is_enabled(sensor_name),
            "sensors": self.sensor_mgr.all_sensors(),
        })

    # ──────────────────────────────────────────────
    # Dream Cycle Endpoints
    # ──────────────────────────────────────────────

    async def _handle_dreams(self, request):
        """GET /dreams/recent — Return recent dream journal entries."""
        limit = int(request.query.get("limit", "7"))
        journals = self.brain.dream_engine.get_recent_journals(limit)
        return web.json_response({
            "journals": journals,
            "count": len(journals),
            "is_dreaming": self.brain.dream_engine.is_dreaming,
        })

    async def _handle_patterns(self, request):
        """GET /patterns — Return all discovered memory patterns."""
        patterns = self.brain.dream_engine.get_patterns()
        return web.json_response({
            "patterns": patterns,
            "count": len(patterns),
        })

    async def _handle_dream_trigger(self, request):
        """POST /dream/trigger — Manually start a dream cycle."""
        if self.brain.dream_engine.is_dreaming:
            return web.json_response({"error": "Already dreaming"}, status=409)

        # Run dream cycle in background so we can respond immediately
        async def _run_dream():
            await self.brain.dream()

        asyncio.ensure_future(_run_dream())

        return web.json_response({
            "status": "dream_started",
            "message": "Dream cycle initiated. Watch /ws/live for progress.",
        })

    # ──────────────────────────────────────────────
    # Goal System Endpoints (Prefrontal Cortex)
    # ──────────────────────────────────────────────

    async def _handle_goals(self, request):
        """GET /goals — List all goals with current status."""
        pfc = self.brain.prefrontal_cortex
        goals = pfc.get_goals()
        summary = {
            "total": len(goals),
            "on_track": sum(1 for g in goals.values() if g.get("status") == "on_track"),
            "at_risk": sum(1 for g in goals.values() if g.get("status") == "at_risk"),
            "off_track": sum(1 for g in goals.values() if g.get("status") == "off_track"),
            "is_evaluating": pfc.is_evaluating,
        }
        return web.json_response({"goals": goals, "summary": summary})

    async def _handle_create_goal(self, request):
        """POST /goal — Create a new goal."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        objective = body.get("objective")
        metric = body.get("metric")
        operator = body.get("operator", "<")
        value = body.get("value")
        priority = body.get("priority", "medium")

        if not objective or not metric or value is None:
            return web.json_response(
                {"error": "Required fields: objective, metric, value"}, status=400
            )

        try:
            value = float(value)
        except (TypeError, ValueError):
            return web.json_response({"error": "value must be numeric"}, status=400)

        goal = self.brain.prefrontal_cortex.add_goal(
            objective=objective,
            metric=metric,
            operator=operator,
            value=value,
            priority=priority,
        )
        return web.json_response({"status": "created", "goal": goal})

    async def _handle_delete_goal(self, request):
        """DELETE /goal — Remove a goal by ID."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        goal_id = body.get("id")
        if not goal_id:
            return web.json_response({"error": "Required field: id"}, status=400)

        if self.brain.prefrontal_cortex.remove_goal(goal_id):
            return web.json_response({"status": "deleted", "id": goal_id})
        return web.json_response({"error": f"Goal '{goal_id}' not found"}, status=404)

    async def _handle_goal_evaluate(self, request):
        """POST /goal/evaluate — Force a goal evaluation cycle."""
        pfc = self.brain.prefrontal_cortex
        if pfc.is_evaluating:
            return web.json_response({"error": "Already evaluating"}, status=409)

        async def _run_eval():
            await pfc.evaluate_all()

        asyncio.ensure_future(_run_eval())
        return web.json_response({
            "status": "evaluation_started",
            "message": "Goal evaluation initiated. Watch /ws/live for progress.",
        })

    # ──────────────────────────────────────────────
    # Prediction Endpoints (Predictive Cortex)
    # ──────────────────────────────────────────────

    async def _handle_predictions(self, request):
        """GET /predictions — Current forecasts for all metric channels."""
        pred = self.brain.predictive_cortex
        return web.json_response({
            "channels": pred.get_predictions(),
            "summary": pred.get_summary(),
            "is_predicting": pred.is_predicting,
        })

    async def _handle_prediction_history(self, request):
        """GET /predictions/history — Recent phantom spike history."""
        limit = int(request.query.get("limit", "20"))
        pred = self.brain.predictive_cortex
        return web.json_response({
            "phantoms": pred.get_phantom_history(limit),
            "count": len(pred.phantom_history),
        })


def _format_uptime(seconds):
    """Convert seconds to human-readable uptime."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
