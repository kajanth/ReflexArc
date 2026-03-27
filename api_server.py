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
from pydantic import ValidationError

# Local Imports
from event_bus import event_bus
from utils.rate_limiter import rate_limit_middleware
from utils.content_validation import content_type_middleware, cors_middleware
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
        
        # Give Broca's Area access to sensors if it exists
        if hasattr(self.brain, "brocas_area"):
            self.brain.brocas_area.sensor_mgr = sensor_mgr
            
        self.app = web.Application(middlewares=[
            cors_middleware,
            content_type_middleware, 
            rate_limit_middleware
        ])
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
        self.app.router.add_get("/graph/data", self._handle_graph_data)

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
        self.app.router.add_get("/ready", self._handle_ready)
        self.app.router.add_get("/live", self._handle_live)

        # Sensor Controls
        self.app.router.add_get("/sensors", self._handle_sensors)
        self.app.router.add_post("/sensor/toggle", self._handle_sensor_toggle)

        # Dream Cycle
        self.app.router.add_get("/dreams/recent", self._handle_dreams)
        self.app.router.add_get("/patterns", self._handle_patterns)
        self.app.router.add_post("/dream/trigger", self._handle_dream_trigger)

        # Proposal Queue & Error Whitelist
        self.app.router.add_get("/proposals/queue", self._handle_proposal_queue)
        self.app.router.add_post("/errors/whitelist", self._handle_whitelist_error)
        self.app.router.add_post("/errors/dismiss", self._handle_dismiss_error)
        self.app.router.add_get("/errors/whitelist", self._handle_get_whitelist)

        # Agent Log Readers (dashboard)
        self.app.router.add_get("/agent_logs/changes", self._handle_changes_log)
        self.app.router.add_get("/agent_logs/activity", self._handle_activity_log)


        # Goal System (Prefrontal Cortex)
        self.app.router.add_get("/goals", self._handle_goals)
        self.app.router.add_post("/goal", self._handle_create_goal)
        self.app.router.add_delete("/goal", self._handle_delete_goal)
        self.app.router.add_post("/goal/evaluate", self._handle_goal_evaluate)

        # Predictions (Predictive Cortex)
        self.app.router.add_get("/predictions", self._handle_predictions)
        self.app.router.add_get("/predictions/history", self._handle_prediction_history)

        # MCP (Model Context Protocol)
        self.app.router.add_get("/mcp/servers", self._handle_mcp_servers)
        self.app.router.add_get("/mcp/tools", self._handle_mcp_tools)

        # Broca's Area (Natural Language Interface)
        self.app.router.add_post("/broca/chat", self._handle_broca_chat)

        # External Webhooks
        self.app.router.add_post("/webhook/{source}", self._handle_webhook)

        # OpenAPI Documentation
        self.app.router.add_get("/openapi.yaml", self._handle_openapi_yaml)
        self.app.router.add_get("/docs", self._handle_swagger_docs)

    # ──────────────────────────────────────────────
    # Dashboard Endpoints
    # ──────────────────────────────────────────────

    async def _handle_dashboard(self, request):
        """GET /dashboard — Serve the live dashboard HTML."""
        html_path = os.path.join(os.path.dirname(__file__), "web", "dashboard.html")
        if os.path.exists(html_path):
            return web.FileResponse(html_path)
        return web.Response(text="Dashboard HTML not found", status=404)

    async def _handle_graph_data(self, request):
        """GET /graph/data — Serve nodes/edges for the Cognitive Map."""
        # Core Architecture Nodes
        nodes = [
            {"id": "Sensors", "label": "Peripheral Senses\n(Layer 0)", "group": "sensor", "level": 1},
            {"id": "RAS", "label": "RAS / Attention\n(Layer 1)", "group": "core", "level": 2},
            {"id": "Hippocampus", "label": "Hippocampus\n(Layer 3)", "group": "memory", "level": 2},
            {"id": "Thalamus", "label": "Thalamus Switch\n(Layer 2)", "group": "core", "level": 3},
            {"id": "Cerebellum", "label": "Cerebellum\n(Layer 5)", "group": "action", "level": 4},
            {"id": "Cortex", "label": "Cortex\n(Layer 4)", "group": "reasoning", "level": 4},
            {"id": "PFC", "label": "Prefrontal\n(Goals)", "group": "executive", "level": 4},
            {"id": "BasalGanglia", "label": "Basal Ganglia\n(Habits)", "group": "action", "level": 5},
            {"id": "Action", "label": "System Response", "group": "output", "level": 6},
        ]
        
        # Structural Edges
        edges = [
            {"from": "Sensors", "to": "RAS"},
            {"from": "RAS", "to": "Hippocampus", "dashes": True},
            {"from": "RAS", "to": "Thalamus"},
            {"from": "Thalamus", "to": "Cerebellum", "label": "REFLEX"},
            {"from": "Thalamus", "to": "Cortex", "label": "COMPLEX"},
            {"from": "PFC", "to": "Thalamus", "dashes": True, "label": "Proactive"},
            {"from": "Cerebellum", "to": "BasalGanglia", "dashes": True},
            {"from": "Cerebellum", "to": "Action"},
            {"from": "Cortex", "to": "Action"}
        ]
        
        # Dynamically append recent memories
        try:
            recent_memories = event_bus.get_history(50)
            mem_count = 0
            for event in recent_memories:
                if event['type'] == 'spike':
                    mem_id = f"mem_{mem_count}"
                    nodes.append({"id": mem_id, "label": "Spike", "group": "spike", "level": 0, "size": 10})
                    edges.append({"from": mem_id, "to": "Sensors", "dashes": True})
                    mem_count += 1
        except Exception:
            pass

        return web.json_response({"nodes": nodes, "edges": edges})

    async def _handle_openapi_yaml(self, request):
        """GET /openapi.yaml — Serve the OpenAPI specification."""
        path = os.path.join(os.path.dirname(__file__), "openapi.yaml")
        if os.path.exists(path):
            return web.FileResponse(path)
        return web.Response(text="openapi.yaml not found", status=404)

    async def _handle_swagger_docs(self, request):
        """GET /docs — Serve the Swagger UI."""
        path = os.path.join(os.path.dirname(__file__), "web", "docs.html")
        if os.path.exists(path):
            return web.FileResponse(path)
        return web.Response(text="Swagger UI template not found", status=404)

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
        def _read_stats():
            with open("memory/stats.json", "r") as f:
                return json.load(f)

        try:
            # ⚡ Bolt: Offload synchronous file I/O to a background thread
            # Impact: Prevents blocking the asyncio event loop during disk reads
            stats = await asyncio.to_thread(_read_stats)
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

        # Validate using Pydantic model
        try:
            spike_req = SpikeRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        tagged_desc = f"[API/{spike_req.priority.upper()}] {spike_req.description}"

        self._spike_count += 1
        event_bus.publish("spike", {
            "sense_type": spike_req.sense_type,
            "description": tagged_desc,
            "priority": spike_req.priority,
            "source": "api",
            "spike_id": self._spike_count,
        })

        try:
            result = await self.brain.process_spike(spike_req.sense_type, tagged_desc)
            return web.json_response({
                "status": "processed",
                "sense_type": spike_req.sense_type,
                "priority": spike_req.priority,
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

        # Validate using Pydantic model
        try:
            threat_req = ThreatSpikeRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        tagged_desc = f"[THREAT/{threat_req.source}] {threat_req.description}"

        self._spike_count += 1
        event_bus.publish("spike", {
            "sense_type": "threat_api",
            "description": tagged_desc,
            "priority": "critical",
            "source": threat_req.source,
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

        # Validate using Pydantic model
        try:
            metric_req = MetricSpikeRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        description = f"[METRIC/{metric_req.source}] {metric_req.metric}: {metric_req.value}{metric_req.unit}"
        if metric_req.threshold is not None:
            description += f" (threshold: {metric_req.threshold}{metric_req.unit}, BREACHED)"

        self._spike_count += 1
        event_bus.publish("spike", {
            "sense_type": "metric_api",
            "description": description,
            "metric": metric_req.metric,
            "value": metric_req.value,
            "source": metric_req.source,
            "spike_id": self._spike_count,
        })

        try:
            result = await self.brain.process_spike("metric_api", description)
            return web.json_response({
                "status": "processed",
                "metric": metric_req.metric,
                "value": metric_req.value,
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
        # ⚡ Bolt: Offload synchronous os.listdir to a background thread
        # Impact: Reduces blocking on disk I/O when reading the directory contents
        skill_files = await asyncio.to_thread(os.listdir, "skills")
        for f in sorted(skill_files):
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
        try:
            limit = int(request.query.get("limit", "10"))
        except ValueError:
            return web.json_response({"error": "Invalid limit parameter"}, status=400)
        limit = min(limit, 50)

        def _fetch_memories(limit_val):
            import sqlite3
            db_path = "memory/long_term_memory.db"
            if not os.path.exists(db_path):
                return []

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, sense_type, description "
                "FROM memories ORDER BY timestamp DESC LIMIT ?",
                (limit_val,)
            )
            rows = cursor.fetchall()
            conn.close()
            return rows

        try:
            # ⚡ Bolt: Offload synchronous SQLite operations to a background thread
            # Impact: Prevents database query latencies from stalling the asyncio event loop
            rows = await asyncio.to_thread(_fetch_memories, limit)

        try:
            rows = await asyncio.to_thread(_fetch_memories)
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

        # Validate using Pydantic model
        try:
            skill_req = SkillRunRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        try:
            import importlib
            module = importlib.import_module(f"skills.{skill_req.skill}")
            importlib.reload(module)
            result = module.run(skill_req.data)

            event_bus.publish("reflex_exec", {
                "skill": skill_req.skill,
                "result": str(result)[:200],
                "source": "api",
            })

            return web.json_response({
                "status": "executed",
                "skill": skill_req.skill,
                "result": str(result),
            })
        except ModuleNotFoundError:
            return web.json_response({"error": f"Skill '{skill_req.skill}' not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": f"Skill execution failed: {e}"}, status=500)

    async def _handle_health(self, request):
        """GET /health — Comprehensive health check with detailed component status."""
        from utils.health_checker import HealthChecker
        
        # Create health checker with brain and sensor manager references
        health_checker = HealthChecker(brain=self.brain, sensor_mgr=self.sensor_mgr)
        
        # Perform comprehensive health check
        health_result = await health_checker.check_full_health()
        
        # Determine HTTP status code based on health
        if health_result["status"] == "healthy":
            status_code = 200
        elif health_result["status"] == "degraded":
            status_code = 200  # Still operational but with warnings
        else:  # unhealthy
            status_code = 503  # Service Unavailable
        
        return web.json_response(health_result, status=status_code)

    async def _handle_ready(self, request):
        """GET /ready — Kubernetes readiness probe."""
        from utils.health_checker import HealthChecker
        
        health_checker = HealthChecker(brain=self.brain, sensor_mgr=self.sensor_mgr)
        readiness_result = await health_checker.check_readiness()
        
        status_code = 200 if readiness_result["ready"] else 503
        return web.json_response(readiness_result, status=status_code)

    async def _handle_live(self, request):
        """GET /live — Kubernetes liveness probe.""" 
        from utils.health_checker import HealthChecker
        
        health_checker = HealthChecker(brain=self.brain, sensor_mgr=self.sensor_mgr)
        liveness_result = await health_checker.check_liveness()
        
        status_code = 200 if liveness_result["alive"] else 503
        return web.json_response(liveness_result, status=status_code)

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

        # Validate using Pydantic model
        try:
            sensor_req = SensorToggleRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        if sensor_req.action == "enable":
            ok = self.sensor_mgr.enable(sensor_req.sensor)
        elif sensor_req.action == "disable":
            ok = self.sensor_mgr.disable(sensor_req.sensor)
        else:
            new_state = self.sensor_mgr.toggle(sensor_req.sensor)
            ok = new_state is not None

        if not ok:
            return web.json_response({"error": f"Sensor '{sensor_req.sensor}' not found"}, status=404)

        return web.json_response({
            "status": "ok",
            "sensor": sensor_req.sensor,
            "enabled": self.sensor_mgr.is_enabled(sensor_req.sensor),
            "sensors": self.sensor_mgr.all_sensors(),
        })

    # ──────────────────────────────────────────────
    # Dream Cycle Endpoints
    # ──────────────────────────────────────────────

    async def _handle_dreams(self, request):
        """GET /dreams/recent — Return recent dream journal entries."""
        try:
            limit = int(request.query.get("limit", "7"))
        except ValueError:
            return web.json_response({"error": "Invalid limit parameter"}, status=400)
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

        # Validate using Pydantic model
        try:
            goal_req = GoalRequest(**body)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        goal = self.brain.prefrontal_cortex.add_goal(
            objective=goal_req.objective,
            metric=goal_req.metric,
            operator=goal_req.operator,
            value=goal_req.value,
            priority=goal_req.priority,
        )
        return web.json_response({"status": "created", "goal": goal})

    async def _handle_delete_goal(self, request):
        """DELETE /goal — Remove a goal by ID."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        # Validate using Pydantic model
        try:
            delete_req = GoalDeleteRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)

        if self.brain.prefrontal_cortex.remove_goal(delete_req.id):
            return web.json_response({"status": "deleted", "id": delete_req.id})
        return web.json_response({"error": f"Goal '{delete_req.id}' not found"}, status=404)

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
        try:
            limit = int(request.query.get("limit", "20"))
        except ValueError:
            return web.json_response({"error": "Invalid limit parameter"}, status=400)
        pred = self.brain.predictive_cortex
        return web.json_response({
            "phantoms": pred.get_phantom_history(limit),
            "count": len(pred.phantom_history),
        })

    # ──────────────────────────────────────────────
    # MCP Endpoints (Model Context Protocol)
    # ──────────────────────────────────────────────
    
    async def _handle_mcp_servers(self, request):
        """GET /mcp/servers — List active MCP servers."""
        mcp_manager = getattr(self.brain, "mcp_manager", None)
        if not mcp_manager:
            return web.json_response({"servers": {}})
            
        servers_status = {}
        for name, client in mcp_manager.servers.items():
            status = "connected" if client.is_initialized else "disconnected"
            error = None
            if not client.is_initialized and client.process and client.process.returncode is not None:
                error = f"Process exited with code {client.process.returncode}"
                
            servers_status[name] = {
                "status": status,
                "error": error
            }
            
        return web.json_response({
            "servers": servers_status
        })
        
    async def _handle_mcp_tools(self, request):
        """GET /mcp/tools — List all available tools across connected MCP servers."""
        mcp_manager = getattr(self.brain, "mcp_manager", None)
        if not mcp_manager:
            return web.json_response({"tools": []})
            
        return web.json_response({
            "tools": mcp_manager.get_all_tools()
        })
        
    async def _handle_broca_chat(self, request):
        """POST /broca/chat — Chat with the brain's natural language interface."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        # Validate using Pydantic model
        try:
            chat_req = BrocaChatRequest(**data)
        except ValidationError as e:
            return web.json_response({
                "error": "Validation failed",
                "details": e.errors()
            }, status=400)
                
        if not hasattr(self.brain, "brocas_area"):
            return web.json_response({"error": "Broca's Area not initialized"}, status=501)
                
        try:
            response = await self.brain.brocas_area.chat(chat_req.message)
            return web.json_response(response)
        except Exception as e:
            print(f"[ApiServer] Error in Broca chat: {e}")
            return web.json_response({"error": str(e)}, status=500)
            
    async def _handle_webhook(self, request):
        """POST /webhook/{source} — Ingest arbitrary webhook payloads."""
        source = request.match_info.get("source", "unknown").lower()
        try:
            # First try JSON
            if request.content_type == "application/json":
                payload = await request.json()
            # Then try form data (e.g., Stripe, older webhooks)
            elif request.content_type == "application/x-www-form-urlencoded":
                form_data = await request.post()
                payload = dict(form_data)
            # Otherwise just grab plain text
            else:
                raw_text = await request.text()
                payload = {"raw_text": raw_text}
                
            # Find the webhook receptor in the sensor manager
            receptor = None
            if hasattr(self, "sensor_mgr") and self.sensor_mgr:
                receptor = self.sensor_mgr.get_sensor("webhooks")
                
                if not receptor:
                    for sensor_id, sensor_obj in self.sensor_mgr.active_sensors():
                        if hasattr(sensor_obj, "ingest_webhook"):
                            receptor = sensor_obj
                            break
            
            if not receptor:
                return web.json_response({"error": "Webhook Receiver sensor not enabled in brain config"}, status=501)
                
            receptor.ingest_webhook(source, payload)
            return web.json_response({"status": "received", "source": source})
            
        except Exception as e:
            print(f"[ApiServer] Error processing webhook from '{source}': {e}")
            return web.json_response({"error": f"Invalid payload: {e}"}, status=400)

    async def _handle_proposal_queue(self, request):
        """GET /proposals/queue — View the proposal backlog with optional ?status= filter."""
        def _get_queue_data(status_filter):
            from utils.proposal_queue import load_queue, queue_stats
            queue = load_queue()
            if status_filter:
                queue = [p for p in queue if p.get("status") == status_filter]
            return {
                "stats": queue_stats(),
                "proposals": queue[-50:],
            }

        status_filter = request.rel_url.query.get("status")
        # ⚡ Bolt: Offload synchronous file operations to a background thread
        data = await asyncio.to_thread(_get_queue_data, status_filter)
        return web.json_response(data)

    async def _handle_whitelist_error(self, request):
        """POST /errors/whitelist — Suppress future alerts for a recurring error."""
        try:
            data = await request.json()
        except Exception:
            data = {}
        error_key = data.get("error_key", "")
        if not error_key:
            return web.json_response({"error": "error_key is required"}, status=400)

        def _whitelist_and_review(key):
            from utils.error_whitelist import whitelist_error, mark_errors_reviewed
            whitelist_error(key, reason="user_whitelisted_via_dashboard")
            mark_errors_reviewed(key)

        # ⚡ Bolt: Offload synchronous file operations to a background thread
        await asyncio.to_thread(_whitelist_and_review, error_key)
        return web.json_response({
            "status": "whitelisted",
            "error_key": error_key,
            "message": f"This error will no longer generate alerts.",
        })

    async def _handle_dismiss_error(self, request):
        """POST /errors/dismiss — Mark errors reviewed without whitelisting."""
        try:
            data = await request.json()
        except Exception:
            data = {}
        error_key = data.get("error_key", "")
        if not error_key:
            return web.json_response({"error": "error_key is required"}, status=400)

        def _mark_reviewed(key):
            from utils.error_whitelist import mark_errors_reviewed
            mark_errors_reviewed(key)

        # ⚡ Bolt: Offload synchronous file operations to a background thread
        await asyncio.to_thread(_mark_reviewed, error_key)
        return web.json_response({
            "status": "dismissed",
            "error_key": error_key,
            "message": "Errors marked as reviewed — will re-alert if they recur.",
        })

    async def _handle_get_whitelist(self, request):
        """GET /errors/whitelist — View the current error whitelist."""
        def _get_whitelist_data():
            from utils.error_whitelist import load_whitelist
            return load_whitelist()

        # ⚡ Bolt: Offload synchronous file operations to a background thread
        data = await asyncio.to_thread(_get_whitelist_data)
        return web.json_response(data)

    async def _handle_changes_log(self, request):
        """GET /agent_logs/changes — Return recent changes log entries as JSON."""
        def _read_changes_log(limit_val):
            import json as _json
            from pathlib import Path
            log_path = Path("memory/agent_logs/changes_log.jsonl")
            entries = []
            if log_path.exists():
                try:
                    with open(log_path, "r") as f:
                        for line in f:
                            try:
                                entries.append(_json.loads(line.strip()))
                            except _json.JSONDecodeError:
                                pass
                except IOError:
                    pass
            return entries[-limit_val:], len(entries)

        try:
            limit = int(request.rel_url.query.get("limit", 50))
        except ValueError:
            return web.json_response({"error": "Invalid limit parameter"}, status=400)
        # ⚡ Bolt: Offload synchronous file operations to a background thread
        recent_entries, total_count = await asyncio.to_thread(_read_changes_log, limit)
        return web.json_response({"entries": recent_entries, "total": total_count})

    async def _handle_activity_log(self, request):
        """GET /agent_logs/activity — Return recent agent activity log entries as JSON."""
        def _read_activity_log(limit_val):
            import json as _json
            from pathlib import Path
            log_path = Path("memory/agent_logs/agent_activity.jsonl")
            entries = []
            if log_path.exists():
                try:
                    with open(log_path, "r") as f:
                        for line in f:
                            try:
                                entries.append(_json.loads(line.strip()))
                            except _json.JSONDecodeError:
                                pass
                except IOError:
                    pass
            return entries[-limit_val:], len(entries)

        try:
            limit = int(request.rel_url.query.get("limit", 30))
        except ValueError:
            return web.json_response({"error": "Invalid limit parameter"}, status=400)
        # ⚡ Bolt: Offload synchronous file operations to a background thread
        recent_entries, total_count = await asyncio.to_thread(_read_activity_log, limit)
        return web.json_response({"entries": recent_entries, "total": total_count})





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
