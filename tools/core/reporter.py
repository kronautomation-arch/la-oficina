"""
Reporter — Herramienta para que cada automatización reporte su estado al dashboard.

Uso desde cualquier automatización:
    from tools.core.reporter import Reporter

    reporter = Reporter("bot-ventas")
    reporter.clock_in("Vendedor Estrella", "Ventas", "🤖")
    reporter.working("Enviando cotizaciones")
    reporter.log("Cotización #482 enviada")
    reporter.complete_task()
    reporter.idle("Esperando próximo ciclo")
    reporter.error("No se pudo conectar a API")
    reporter.sleeping("Próxima ejecución a las 14:00")
    reporter.clock_out()
"""
import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

STATUS_FILE = Path(__file__).resolve().parent.parent.parent / "status.json"
_file_lock = Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _time_short() -> str:
    return datetime.now().strftime("%H:%M")


def _load() -> dict:
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": _now(), "employees": []}


def _save(data: dict):
    data["last_updated"] = _now()
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Reporter:
    def __init__(self, employee_id: str):
        self.id = employee_id

    def _get_employee(self, data: dict) -> dict | None:
        for emp in data["employees"]:
            if emp["id"] == self.id:
                return emp
        return None

    def _update(self, updates: dict):
        with _file_lock:
            data = _load()
            emp = self._get_employee(data)
            if emp is None:
                emp = {
                    "id": self.id,
                    "name": self.id,
                    "role": "Empleado",
                    "department": "General",
                    "avatar_emoji": "🤖",
                    "status": "idle",
                    "mood": "neutral",
                    "current_task": "—",
                    "tasks_completed_today": 0,
                    "tasks_completed_total": 0,
                    "uptime_today": "0h 0m",
                    "last_activity": _now(),
                    "started_at": _now(),
                    "schedule": "manual",
                    "recent_logs": [],
                    "metrics": {
                        "success_rate": 100.0,
                        "avg_response_time": "0s",
                        "errors_today": 0,
                    },
                }
                data["employees"].append(emp)

            emp.update(updates)
            emp["last_activity"] = _now()

            # Calcular uptime
            try:
                started = datetime.fromisoformat(emp["started_at"])
                delta = datetime.now() - started
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                emp["uptime_today"] = f"{hours}h {minutes:02d}m"
            except (ValueError, KeyError):
                pass

            _save(data)

    def clock_in(self, name: str, department: str, emoji: str = "🤖", role: str = "Empleado", schedule: str = "manual"):
        """Registra un nuevo empleado o actualiza su info al iniciar."""
        self._update({
            "name": name,
            "role": role,
            "department": department,
            "avatar_emoji": emoji,
            "status": "working",
            "mood": "productive",
            "started_at": _now(),
            "schedule": schedule,
            "current_task": "Iniciando turno...",
        })
        self.log("Se conectó a la oficina ✅")

    def clock_out(self):
        """Marca al empleado como fuera de servicio."""
        self._update({"status": "sleeping", "mood": "resting", "current_task": "Fuera de turno"})
        self.log("Se desconectó de la oficina 👋")

    def working(self, task: str):
        self._update({"status": "working", "mood": "productive", "current_task": task})

    def idle(self, reason: str = "Esperando siguiente tarea"):
        self._update({"status": "idle", "mood": "relaxed", "current_task": reason})

    def sleeping(self, reason: str = "Fuera de horario"):
        self._update({"status": "sleeping", "mood": "resting", "current_task": reason})

    def error(self, message: str):
        with _file_lock:
            data = _load()
            emp = self._get_employee(data)
            if emp:
                emp["status"] = "error"
                emp["mood"] = "stressed"
                emp["current_task"] = f"⚠️ {message}"
                emp["metrics"]["errors_today"] = emp["metrics"].get("errors_today", 0) + 1
                emp["last_activity"] = _now()
                _save(data)
        self.log(f"ERROR: {message}")

    def complete_task(self):
        """Incrementa el contador de tareas completadas."""
        with _file_lock:
            data = _load()
            emp = self._get_employee(data)
            if emp:
                emp["tasks_completed_today"] = emp.get("tasks_completed_today", 0) + 1
                emp["tasks_completed_total"] = emp.get("tasks_completed_total", 0) + 1
                emp["last_activity"] = _now()
                _save(data)

    def log(self, message: str):
        """Agrega un mensaje al log del empleado (máx 10 entradas)."""
        with _file_lock:
            data = _load()
            emp = self._get_employee(data)
            if emp:
                logs = emp.get("recent_logs", [])
                logs.insert(0, {"time": _time_short(), "message": message})
                emp["recent_logs"] = logs[:10]
                emp["last_activity"] = _now()
                _save(data)

    def set_metric(self, key: str, value):
        """Actualiza una métrica específica."""
        with _file_lock:
            data = _load()
            emp = self._get_employee(data)
            if emp:
                emp["metrics"][key] = value
                _save(data)
