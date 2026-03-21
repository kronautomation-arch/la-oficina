# Automation Dashboard — "La Oficina"

## WAT Framework
- TOOLS: `tools/core/reporter.py` — reporter que cada automatización usa para reportar estado
- AGENT: N/A (no hay agente AI, es un dashboard estático)
- WORKFLOWS: Cada automatización importa Reporter y reporta su estado

## Arquitectura
- `index.html` — Dashboard single-file (HTML+CSS+JS) para GitHub Pages
- `status.json` — Estado actual de todos los "empleados" (automatizaciones)
- `tools/core/reporter.py` — Clase Reporter para actualizar status.json
- `.github/workflows/deploy.yml` — Auto-deploy a GitHub Pages
- `.github/workflows/update-status.yml` — Auto-commit de status.json cada 5 min

## Cómo agregar una automatización
```python
import sys
sys.path.insert(0, "ruta/a/automation-dashboard")
from tools.core.reporter import Reporter

reporter = Reporter("mi-bot")
reporter.clock_in("Nombre Bot", "Departamento", "🤖", role="Mi Rol", schedule="09:00 - 18:00")
reporter.working("Haciendo algo...")
reporter.log("Detalle de lo que hizo")
reporter.complete_task()
reporter.clock_out()
```

## Push workflow
1. Automatización actualiza status.json via Reporter
2. Script de sync hace git commit + push
3. GitHub Actions deploys to Pages
