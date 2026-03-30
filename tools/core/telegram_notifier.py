"""
Telegram Notifier — Envía alertas cuando las automatizaciones ejecutan tareas o fallan.

Setup:
    1. Habla con @BotFather en Telegram → /newbot → copia el token
    2. Envía un mensaje a tu bot, luego ve a:
       https://api.telegram.org/bot<TOKEN>/getUpdates → copia tu chat_id
    3. Pon en tu .env:
       TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
       TELEGRAM_CHAT_ID=123456789

Uso:
    from tools.core.telegram_notifier import TelegramNotifier

    notifier = TelegramNotifier()  # Lee de .env
    notifier.task_started("Carlos Bot", "Enviando 50 mensajes")
    notifier.task_completed("Carlos Bot", "50 mensajes enviados", tasks=50, errors=0)
    notifier.task_failed("Carlos Bot", "API Botcake no responde")
    notifier.daily_summary(employees_data)
"""
import os
import requests
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Buscar .env en el proyecto que llama o en automation-dashboard
    for env_path in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass


class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)

    def _send(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def task_started(self, employee_name: str, task_description: str) -> bool:
        """Notifica que un empleado empezó una tarea."""
        now = datetime.now().strftime("%H:%M")
        msg = (
            f"⚡ <b>Tarea Iniciada</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>{employee_name}</b>\n"
            f"📋 {task_description}\n"
            f"🕐 {now}"
        )
        return self._send(msg)

    def task_completed(self, employee_name: str, summary: str, tasks: int = 0, errors: int = 0) -> bool:
        """Notifica que un empleado terminó su tarea."""
        now = datetime.now().strftime("%H:%M")
        error_line = f"\n⚠️ Errores: {errors}" if errors > 0 else ""
        msg = (
            f"✅ <b>Tarea Completada</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>{employee_name}</b>\n"
            f"📋 {summary}\n"
            f"📊 Tareas: {tasks}{error_line}\n"
            f"🕐 {now}"
        )
        return self._send(msg)

    def task_failed(self, employee_name: str, error_message: str) -> bool:
        """Notifica que algo falló."""
        now = datetime.now().strftime("%H:%M")
        msg = (
            f"🔴 <b>ERROR — Atención Requerida</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>{employee_name}</b>\n"
            f"❌ {error_message}\n"
            f"🕐 {now}\n\n"
            f"⚡ Revisa el dashboard para más detalles."
        )
        return self._send(msg)

    def daily_summary(self, employees: list[dict]) -> bool:
        """Envía resumen diario de todos los empleados."""
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        total_tasks = sum(e.get("tasks_completed_today", 0) for e in employees)
        total_errors = sum(e.get("metrics", {}).get("errors_today", 0) for e in employees)
        working = sum(1 for e in employees if e.get("status") == "working")

        lines = [
            f"📊 <b>Reporte Diario — La Oficina</b>",
            f"━━━━━━━━━━━━━━━",
            f"📅 {now}",
            f"👥 {len(employees)} empleados | {working} activos",
            f"✅ {total_tasks} tareas completadas",
            f"{'⚠️' if total_errors else '🟢'} {total_errors} errores",
            f"",
            f"<b>Detalle por empleado:</b>",
        ]

        for emp in employees:
            status_icon = {"working": "🟢", "idle": "🟡", "sleeping": "💤", "error": "🔴"}.get(emp.get("status"), "⚪")
            lines.append(
                f"{status_icon} <b>{emp.get('name', '?')}</b> — "
                f"{emp.get('tasks_completed_today', 0)} tareas"
            )

        return self._send("\n".join(lines))

    def custom(self, message: str) -> bool:
        """Envía un mensaje personalizado."""
        return self._send(message)
