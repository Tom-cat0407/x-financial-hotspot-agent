from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".audit",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "frontend/node_modules",
    "node_modules",
}
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]
SENSITIVE_FILENAMES = {
    ".env",
    "deepseek.txt",
    "火山方舟.txt",
}


def should_skip(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    if relative == ".env.example":
        return True
    return any(relative == item or relative.startswith(f"{item}/") for item in SKIP_DIRS)


def scan() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if path.name in SENSITIVE_FILENAMES:
            findings.append(path.relative_to(ROOT).as_posix())
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(path.relative_to(ROOT).as_posix())
                break
    return sorted(set(findings))


def main() -> int:
    findings = scan()
    if findings:
        print("Potential secrets found. Remove or sanitize these files before packaging:")
        for item in findings:
            print(f"- {item}")
        return 1
    print("Submission preflight passed: no obvious API keys found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
