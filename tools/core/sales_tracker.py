"""
Sales Tracker — Rastrea ventas de la campaña cruzando contactos enviados con tag COMPRÓ en Pancake.

Solo cuenta como venta de la campaña si:
  1. El contacto recibió un mensaje de la campaña (está en progress.csv como enviado)
  2. La etiqueta COMPRÓ fue agregada DESPUÉS de la fecha de envío

Uso:
    python tools/core/sales_tracker.py              # Actualiza status.json con ventas
    python tools/core/sales_tracker.py --report     # Solo muestra reporte en consola

Setup:
    Requiere en .env:
        PANCAKE_API_TOKEN=eyJ...
        PANCAKE_PAGE_ID=waba_888351991026266
"""
import csv
import json
import os
import sys
import io
import requests
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    for env_path in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

# ── Config ──
PANCAKE_TOKEN = os.getenv("PANCAKE_API_TOKEN", "")
PAGE_ID = os.getenv("PANCAKE_PAGE_ID", os.getenv("PAGE_ID", "waba_888351991026266"))
TAG_COMPRO_ID = 43
CAMPAIGN_PROGRESS = Path(__file__).resolve().parent.parent.parent.parent / "campana-tenis" / "data" / "progress.csv"
STATUS_FILE = Path(__file__).resolve().parent.parent.parent / "status.json"
AUTOMATION_ID = "campana-tenis"


def normalize_phone(phone: str) -> str:
    """Normaliza teléfono a formato 52XXXXXXXXXX (12 dígitos)."""
    p = ''.join(c for c in str(phone) if c.isdigit())
    if len(p) == 13 and p.startswith('521'):
        p = '52' + p[3:]
    elif len(p) == 10:
        p = '52' + p
    return p


def load_sent_contacts() -> dict:
    """Carga contactos enviados del progress.csv."""
    sent = {}
    with open(CAMPAIGN_PROGRESS, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('enviado') == 'True':
                phone = normalize_phone(row['telefono'])
                sent[phone] = {
                    'nombre': row['nombre'],
                    'fecha_envio': row.get('fecha_envio', '')[:10],
                }
    return sent


def get_compro_conversations() -> list:
    """Obtiene todas las conversaciones con tag COMPRÓ de Pancake."""
    all_convos = []
    last_id = None

    while True:
        params = {'page_access_token': PANCAKE_TOKEN, 'tags': str(TAG_COMPRO_ID)}
        if last_id:
            params['last_conversation_id'] = last_id

        r = requests.get(
            f'https://pages.fm/api/public_api/v2/pages/{PAGE_ID}/conversations',
            params=params, timeout=15
        )
        convos = r.json().get('conversations', [])
        if not convos:
            break
        all_convos.extend(convos)
        last_id = convos[-1]['id']
        if len(convos) < 60:
            break

    return all_convos


def track_sales() -> dict:
    """Cruza contactos enviados con tag COMPRÓ y retorna ventas atribuibles."""
    sent = load_sent_contacts()
    compro_convos = get_compro_conversations()

    ventas = []
    ventas_previas = 0  # ya compraron antes del envío

    for c in compro_convos:
        raw_phone = c['id'].replace(f'{PAGE_ID}_', '')
        norm_phone = normalize_phone(raw_phone)

        if norm_phone not in sent:
            continue

        # Buscar fecha del tag COMPRÓ
        fecha_compro = None
        for th in c.get('tag_histories', []):
            payload = th.get('payload', {})
            tag = payload.get('tag', {})
            if tag.get('id') == TAG_COMPRO_ID and payload.get('action') == 'add':
                fecha_compro = th.get('inserted_at', '')[:10]
                break

        if not fecha_compro:
            continue

        fecha_envio = sent[norm_phone]['fecha_envio']

        # Solo contar si compraron DESPUÉS o EL MISMO DÍA del envío
        if fecha_compro >= fecha_envio:
            ventas.append({
                'phone': norm_phone,
                'nombre': c.get('page_customer', {}).get('name', sent[norm_phone]['nombre']),
                'fecha_envio': fecha_envio,
                'fecha_compro': fecha_compro,
            })
        else:
            ventas_previas += 1

    # Agrupar por fecha de compra
    por_fecha = Counter(v['fecha_compro'] for v in ventas)

    return {
        'total_ventas': len(ventas),
        'total_enviados': len(sent),
        'conversion_rate': round(len(ventas) / len(sent) * 100, 1) if sent else 0,
        'ventas_previas': ventas_previas,
        'ventas_por_fecha': dict(sorted(por_fecha.items())),
        'detalle': ventas,
    }


def update_dashboard(sales_data: dict):
    """Actualiza status.json con datos de ventas."""
    if not STATUS_FILE.exists():
        return

    with open(STATUS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for auto in data.get('automations', []):
        if auto['id'] == AUTOMATION_ID:
            auto['sales'] = {
                'total': sales_data['total_ventas'],
                'conversion_rate': sales_data['conversion_rate'],
                'by_date': sales_data['ventas_por_fecha'],
                'last_checked': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            }

            # También agregar ventas al historial diario
            for h in auto.get('history', []):
                date = h['date']
                h['sales'] = sales_data['ventas_por_fecha'].get(date, 0)

            break

    data['last_updated'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def print_report(sales_data: dict):
    """Imprime reporte en consola."""
    print("=" * 50)
    print("REPORTE DE VENTAS — CAMPANA TENIS")
    print("=" * 50)
    print(f"Contactos enviados:     {sales_data['total_enviados']}")
    print(f"Ventas de la campana:   {sales_data['total_ventas']}")
    print(f"Tasa de conversion:     {sales_data['conversion_rate']}%")
    print(f"Ya habian comprado:     {sales_data['ventas_previas']} (no se cuentan)")
    print()
    print("Ventas por dia:")
    for fecha, count in sales_data['ventas_por_fecha'].items():
        print(f"  {fecha}: {count} ventas")
    print()
    print("Detalle:")
    for v in sales_data['detalle']:
        print(f"  {v['fecha_envio']} -> {v['fecha_compro']} | {v['nombre']}")


if __name__ == '__main__':
    if not PANCAKE_TOKEN:
        print("ERROR: PANCAKE_API_TOKEN no encontrado en .env")
        sys.exit(1)

    report_only = '--report' in sys.argv

    sales = track_sales()
    print_report(sales)

    if not report_only:
        update_dashboard(sales)
        print()
        print("Dashboard actualizado con datos de ventas.")
