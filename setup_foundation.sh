#!/usr/bin/env bash
set -euo pipefail

mkdir -p \
  app/core \
  app/config \
  app/exchange \
  app/market \
  app/execution \
  app/risk \
  app/strategies \
  app/storage \
  app/monitoring \
  tests \
  data \
  logs

touch \
  app/__init__.py \
  app/core/__init__.py \
  app/config/__init__.py \
  app/exchange/__init__.py \
  app/market/__init__.py \
  app/execution/__init__.py \
  app/risk/__init__.py \
  app/strategies/__init__.py \
  app/storage/__init__.py \
  app/monitoring/__init__.py \
  tests/__init__.py

cat > .gitignore <<'EOF'
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.env
.env.*
!.env.example
data/*.db
data/*.sqlite*
logs/*.log
*.egg-info/
EOF

cat > requirements.txt <<'EOF'
pandas>=2.2,<3
numpy>=1.26,<3
pydantic>=2.7,<3
pydantic-settings>=2.2,<3
PyYAML>=6.0,<7
httpx>=0.27,<1
websockets>=12,<16
python-dotenv>=1.0,<2
SQLAlchemy>=2.0,<3
aiosqlite>=0.20,<1
tenacity>=8.2,<10
pytest>=8,<9
pytest-asyncio>=0.23,<1
ruff>=0.6,<1
EOF

cat > app/core/health.py <<'EOF'
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthStatus:
    ok: bool
    component: str
    message: str


def check() -> HealthStatus:
    return HealthStatus(
        ok=True,
        component="core",
        message="DONAL BOT V2 foundation OK",
    )
EOF

cat > tests/test_health.py <<'EOF'
from app.core.health import check


def test_core_health():
    status = check()

    assert status.ok is True
    assert status.component == "core"
    assert "foundation" in status.message.lower()
EOF

cat > pyproject.toml <<'EOF'
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 100
target-version = "py310"
EOF

echo
echo "=== FOUNDATION CREATED ==="
find app tests -type f | sort
