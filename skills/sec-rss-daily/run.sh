#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

python3 "$SKILL_DIR/scripts/generate_sec_daily.py" \
  --config "$SKILL_DIR/skill.yaml" \
  --system-prompt "$SKILL_DIR/prompts/ai_enrich_system.md" \
  "$@"
