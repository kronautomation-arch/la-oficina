"""
Reporter — Herramienta para que cada automatización reporte su estado al dashboard.

Uso desde cualquier automatización:
    import sys
    sys.path.insert(0, r"C:\\Users\\USER\\Documents\\CLAUDE CODE\\automation-dashboard")
    from tools.core.reporter import Reporter

    reporter = Reporter("mi-bot")
    reporter.clock_in(name="Mi Bot", description="Hace cosas", icon="🤖", schedule="10:00 diario")
    reporter.working("Procesando datos...")
    reporter.log_execution(tasks=50, errors=0, duration="1m 30s", summary="50/50 OK")
    reporter.idle("Próxima ejecución mañana 10:00")
    reporter.error("No se pudo conectar a API")
"""
import json
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

STATUS_FILE = Path(__file__).resolve().parent.parent.parent / "status.json"
_file_lock = Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load() -> dict:
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": _now(), "automations": []}


def _save(data: dict):
    data["last_updated"] = _now()
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Reporter:
    def __init__(self, automation_id: str):
        self.id = automation_id
        self._start_time = None

    def _get_automation(self, data: dict) -> dict | None:
        for a in data.get("automations", []):
            if a["id"] == self.id:
                return a
        return None

    def _update(self, updates: dict):
        with _file_lock:
            data = _load()
            auto = self._get_automation(data)
            if auto is None:
                auto = {
                    "id": self.id,
                    "name": self.id,
                    "description": "",
                    "icon": "🤖",
                    "status": "idle",
                    "schedule": "manual",
                    "current_task": "—",
                    "total_tasks": 0,
                    "total_executions": 0,
                    "history": [],
                    "metrics": {
                        "success_rate": 100.0,
                        "avg_duration": "0s",
                        "streak": 0,
                    },
                }
                data.setdefault("automations", []).append(auto)

            auto.update(updates)
            _save(data)

    def clock_in(self, name: str, description: str = "", icon: str = "🤖", schedule: str = "manual"):
        """Registra la automatización y marca como trabajando."""
        self._start_time = time.time()
        self._update({
            "name": name,
            "description": description,
            "icon": icon,
            "status": "working",
            "schedule": schedule,
            "current_task": "Iniciando...",
        })

    def working(self, task: str):
        """Actualiza la tarea actual."""
        self._update({"status": "working", "current_task": task})

    def idle(self, reason: str = "En espera"):
        """Marca como en espera."""
        self._update({"status": "idle", "current_task": reason})

    def error(self, message: str):
        """Marca como error."""
        self._update({"status": "error", "current_task": f"⚠️ {message}"})

    def offline(self, reason: str = "Desconectado"):
        """Marca como offline."""
        self._update({"status": "offline", "current_task": reason})

    def log_execution(self, tasks: int = 0, errors: int = 0, duration: str = None, summary: str = ""):
        """Registra una ejecución en el historial del día."""
        if duration is None and self._start_time:
            elapsed = time.time() - self._start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            duration = f"{mins}m {secs}s"

        status = "fail" if errors > 0 else "success"
        today = _today()

        with _file_lock:
            data = _load()
            auto = self._get_automation(data)
            if not auto:
                return

            # Update or add today's history entry
            history = auto.get("history", [])
            existing = None
            for h in history:
                if h["date"] == today:
                    existing = h
                    break

            entry = {
                "date": today,
                "status": status,
                "tasks": (existing["tasks"] if existing else 0) + tasks,
                "errors": (existing["errors"] if existing else 0) + errors,
                "duration": duration or "0s",
                "summary": summary,
            }

            if existing:
                history[history.index(existing)] = entry
            else:
                history.insert(0, entry)

            # Keep max 90 days
            auto["history"] = history[:90]

            # Update totals
            auto["total_tasks"] = auto.get("total_tasks", 0) + tasks
            auto["total_executions"] = auto.get("total_executions", 0) + 1

            # Recalc metrics
            recent = [h for h in history[:30]]
            successes = sum(1 for h in recent if h["status"] == "success")
            auto["metrics"]["success_rate"] = round(successes / len(recent) * 100, 1) if recent else 100

            # Streak
            streak = 0
            for h in history:
                if h["status"] == "success":
                    streak += 1
                else:
                    break
            auto["metrics"]["streak"] = streak

            # Avg duration
            durations = []
            for h in recent:
                d = h.get("duration", "")
                try:
                    parts = d.replace("s", "").split("m")
                    secs = int(parts[0].strip()) * 60 + int(parts[1].strip()) if len(parts) == 2 else int(parts[0].strip())
                    durations.append(secs)
                except (ValueError, IndexError):
                    pass
            if durations:
                avg = sum(durations) // len(durations)
                auto["metrics"]["avg_duration"] = f"{avg // 60}m {avg % 60}s"

            _save(data)

    # ── Backward compatibility with old API ──

    def complete_task(self):
        """Compatibility: incrementa contador (ahora se hace via log_execution)."""
        pass

    def log(self, message: str):
        """Compatibility: no-op (logs ahora van en history)."""
        pass

    def set_metric(self, key: str, value):
        """Compatibility: actualiza una métrica."""
        with _file_lock:
            data = _load()
            auto = self._get_automation(data)
            if auto:
                auto["metrics"][key] = value
                _save(data)

    def clock_out(self):
        """Marca como offline."""
        self.offline("Fuera de turno")
