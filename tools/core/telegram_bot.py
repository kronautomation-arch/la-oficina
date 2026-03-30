"""
Telegram Bot Interactivo — Responde preguntas sobre el estado de las automatizaciones.

Comandos:
    /status     — Resumen rápido de todas las automatizaciones
    /detalle    — Detalle completo con historial reciente
    /hoy        — ¿Qué se ejecutó hoy?
    /errores    — Muestra solo las que tienen errores
    /help       — Lista de comandos

También responde a mensajes naturales como:
    "¿ya corrieron las automatizaciones?"
    "¿cómo va la campaña?"
    "resumen"

Uso:
    python tools/core/telegram_bot.py

Setup:
    pip install requests
    Requiere .env con TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID
"""
import json
import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# ── Config ──
try:
    from dotenv import load_dotenv
    for env_path in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STATUS_FILE = Path(__file__).resolve().parent.parent.parent / "status.json"
API = f"https://api.telegram.org/bot{TOKEN}"


def load_status() -> dict:
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"automations": []}


def send_message(text: str, chat_id: str = None):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id or CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }, timeout=10)


# ── Respuestas ──

def cmd_status() -> str:
    data = load_status()
    autos = data.get("automations", [])
    if not autos:
        return "⚙️ No hay automatizaciones registradas."

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        f"⚙️ <b>KRON — Reporte de Estado</b>",
        f"📅 {now}",
        f"━━━━━━━━━━━━━━━━━━",
        "",
    ]

    total_ok = 0
    total_fail = 0
    total_pending = 0

    for a in autos:
        status_icon = {
            "working": "🟢",
            "idle": "🔵",
            "error": "🔴",
            "offline": "⚫",
        }.get(a.get("status"), "⚪")

        status_label = {
            "working": "Operando",
            "idle": "En Espera",
            "error": "Error",
            "offline": "Desconectado",
        }.get(a.get("status"), "Desconocido")

        # Check today's execution
        today_exec = None
        for h in a.get("history", []):
            if h["date"] == today:
                today_exec = h
                break

        if today_exec:
            if today_exec["status"] == "success":
                today_line = f"✅ Hoy: {today_exec['tasks']} tareas OK ({today_exec['duration']})"
                total_ok += 1
            else:
                today_line = f"❌ Hoy: {today_exec['errors']} errores"
                total_fail += 1
        else:
            today_line = "⏳ Hoy: Pendiente de ejecución"
            total_pending += 1

        lines.append(f"{status_icon} <b>{a['name']}</b>")
        lines.append(f"   {a.get('icon', '🤖')} {status_label} | {a.get('schedule', '—')}")
        lines.append(f"   {today_line}")
        lines.append(f"   📊 Racha: {a.get('metrics', {}).get('streak', 0)} días | Éxito: {a.get('metrics', {}).get('success_rate', 0)}%")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 <b>Resumen:</b> ✅{total_ok} ok | ❌{total_fail} fallos | ⏳{total_pending} pendientes")

    return "\n".join(lines)


def cmd_hoy() -> str:
    data = load_status()
    autos = data.get("automations", [])
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        f"📅 <b>Ejecuciones de Hoy</b> — {now}",
        f"━━━━━━━━━━━━━━━━━━",
        "",
    ]

    any_today = False
    for a in autos:
        for h in a.get("history", []):
            if h["date"] == today:
                any_today = True
                icon = "✅" if h["status"] == "success" else "❌"
                lines.append(f"{icon} <b>{a['name']}</b>")
                lines.append(f"   Tareas: {h['tasks']} | Errores: {h['errors']}")
                lines.append(f"   Duración: {h['duration']}")
                if h.get("summary"):
                    lines.append(f"   📝 {h['summary']}")
                lines.append("")
                break

    if not any_today:
        lines.append("⏳ Ninguna automatización se ha ejecutado hoy.")
        lines.append("")
        lines.append("Automatizaciones pendientes:")
        for a in autos:
            lines.append(f"   🔹 {a['name']} — {a.get('schedule', '—')}")

    return "\n".join(lines)


def cmd_detalle() -> str:
    data = load_status()
    autos = data.get("automations", [])
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        f"📋 <b>KRON — Detalle Completo</b>",
        f"📅 {now}",
        f"━━━━━━━━━━━━━━━━━━",
    ]

    for a in autos:
        metrics = a.get("metrics", {})
        history = a.get("history", [])[:7]

        lines.append("")
        lines.append(f"🤖 <b>{a['name']}</b>")
        lines.append(f"   {a.get('description', '—')}")
        lines.append(f"   Horario: {a.get('schedule', '—')}")
        lines.append(f"   Éxito: {metrics.get('success_rate', 0)}% | Racha: {metrics.get('streak', 0)} días")
        lines.append(f"   Total: {a.get('total_executions', 0)} ejecuciones, {a.get('total_tasks', 0)} tareas")
        lines.append("")
        lines.append("   <b>Últimos 7 días:</b>")

        for h in history:
            icon = "✅" if h["status"] == "success" else "❌"
            lines.append(f"   {icon} {h['date']} — {h.get('tasks', 0)} tareas, {h.get('duration', '—')}")

    return "\n".join(lines)


def cmd_errores() -> str:
    data = load_status()
    autos = data.get("automations", [])

    lines = [
        f"🔴 <b>Reporte de Errores</b>",
        f"━━━━━━━━━━━━━━━━━━",
        "",
    ]

    any_errors = False
    for a in autos:
        if a.get("status") == "error":
            any_errors = True
            lines.append(f"🔴 <b>{a['name']}</b> — EN ERROR")
            lines.append(f"   {a.get('current_task', '—')}")
            lines.append("")

        for h in a.get("history", [])[:7]:
            if h["status"] == "fail":
                any_errors = True
                lines.append(f"❌ <b>{a['name']}</b> — {h['date']}")
                lines.append(f"   Errores: {h['errors']} | {h.get('summary', '—')}")
                lines.append("")

    if not any_errors:
        lines.append("✅ <b>Sin errores</b> — Todo funcionando correctamente en los últimos 7 días.")

    return "\n".join(lines)


def cmd_help() -> str:
    return (
        "🤖 <b>KRON Bot — Comandos</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "/status — Resumen rápido de todas las automatizaciones\n"
        "/hoy — ¿Qué se ejecutó hoy?\n"
        "/detalle — Historial completo de los últimos 7 días\n"
        "/errores — Muestra solo errores recientes\n"
        "/help — Esta lista de comandos\n\n"
        "También puedes preguntarme con texto normal:\n"
        "• <i>\"¿ya corrieron?\"</i>\n"
        "• <i>\"resumen\"</i>\n"
        "• <i>\"¿cómo va la campaña?\"</i>\n"
        "• <i>\"¿hay errores?\"</i>"
    )


def handle_message(text: str) -> str:
    """Procesa un mensaje y devuelve la respuesta apropiada."""
    text = text.strip().lower()

    # Comandos directos
    if text.startswith("/status") or text.startswith("/start"):
        return cmd_status()
    if text.startswith("/hoy"):
        return cmd_hoy()
    if text.startswith("/detalle"):
        return cmd_detalle()
    if text.startswith("/errores"):
        return cmd_errores()
    if text.startswith("/help") or text.startswith("/ayuda"):
        return cmd_help()

    # Lenguaje natural
    keywords_status = ["status", "estado", "resumen", "reporte", "corrieron", "corrió", "ejecutaron", "ejecutó", "cómo va", "como va", "qué tal", "que tal", "funcionando", "activas", "automatizaciones"]
    keywords_today = ["hoy", "today", "ahorita", "esta vez"]
    keywords_errors = ["error", "fallo", "falló", "problema", "rojo", "mal"]
    keywords_detail = ["detalle", "historial", "últimos", "dias", "días", "completo"]
    keywords_greeting = ["hola", "hey", "buenas", "qué onda", "que onda", "hello", "hi"]

    if any(k in text for k in keywords_errors):
        return cmd_errores()
    if any(k in text for k in keywords_detail):
        return cmd_detalle()
    if any(k in text for k in keywords_today):
        return cmd_hoy()
    if any(k in text for k in keywords_status):
        return cmd_status()
    if any(k in text for k in keywords_greeting):
        return "👋 ¡Hola! Soy el bot de <b>KRON</b>.\n\nEscribe /status para ver el estado de tus automatizaciones o /help para ver todos los comandos."

    # Default
    return cmd_status()


# ── Polling Loop ──

def poll():
    """Long-polling loop para escuchar mensajes."""
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print("KRON Bot iniciado - escuchando mensajes...")
    print(f"   Token: {TOKEN[:20]}...")
    print(f"   Status file: {STATUS_FILE}")

    offset = None

    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            resp = requests.get(f"{API}/getUpdates", params=params, timeout=35)
            data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))
                user = msg.get("from", {}).get("first_name", "?")

                if not text:
                    continue

                print(f"[MSG] {user}: {text}")
                response = handle_message(text)
                send_message(response, chat_id)
                print(f"[OK] Respondido")

        except requests.exceptions.Timeout:
            continue
        except KeyboardInterrupt:
            print("\nBot detenido.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN no encontrado en .env")
        sys.exit(1)
    poll()
