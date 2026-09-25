"""P3 (Nakul): golden-output check, called by the loop after every candidate patch.

Runs sales-report's own golden.py (brief section 23.8) in the NEW environment.
Returns True until sales-report has a golden.py, so the loop works from minute one.
"""
import pathlib
import subprocess


def golden_ok(repo, venv):
    script = pathlib.Path(repo) / "golden.py"
    if not script.exists():
        return True
    r = subprocess.run([f"{venv}/bin/python", "golden.py", "check"], cwd=repo, capture_output=True)
    return r.returncode == 0
