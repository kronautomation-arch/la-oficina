"""
Sync status.json to GitHub — ejecutar como cron o al final de cada ciclo.

Uso:
    python tools/core/sync_to_github.py

Hace git add + commit + push del status.json actualizado.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    return result.returncode, result.stdout.strip() + result.stderr.strip()


def sync():
    # Stage status.json
    code, out = run(["git", "add", "status.json"])
    if code != 0:
        print(f"Error staging: {out}")
        return False

    # Check if there are changes
    code, out = run(["git", "diff", "--cached", "--quiet"])
    if code == 0:
        print("Sin cambios en status.json")
        return True

    # Commit
    now = datetime.now().strftime("%H:%M")
    code, out = run(["git", "commit", "-m", f"📊 Status update {now}"])
    if code != 0:
        print(f"Error commit: {out}")
        return False

    # Push
    code, out = run(["git", "push"])
    if code != 0:
        print(f"Error push: {out}")
        return False

    print(f"✅ Status sincronizado a GitHub ({now})")
    return True


if __name__ == "__main__":
    success = sync()
    sys.exit(0 if success else 1)
