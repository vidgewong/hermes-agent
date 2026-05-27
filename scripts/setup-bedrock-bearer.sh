#!/bin/bash
# Hermes Agent: Bedrock Bearer Token Auth Setup
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/vidgewong/hermes-agent/setup-script/scripts/setup-bedrock-bearer.sh -o /tmp/setup.sh && bash /tmp/setup.sh
#
# Non-interactive:
#   export AWS_BEARER_TOKEN_BEDROCK=your-token
#   export ANTHROPIC_BEDROCK_BASE_URL=https://your-proxy.example.com
#   export HERMES_MODEL=claude-opus-4.6
#   curl -fsSL ... -o /tmp/setup.sh && bash /tmp/setup.sh

set -e

HERMES_DIR="${HOME}/.hermes/hermes-agent"

if [ ! -d "$HERMES_DIR" ]; then
  echo "Error: Hermes not installed at $HERMES_DIR"
  exit 1
fi

cd "$HERMES_DIR"

# Apply the patch (idempotent - skips if already applied)
PATCH_URL="https://github.com/vidgewong/hermes-agent/commit/4e7b21ac3.patch"
PATCH_FILE=$(mktemp)
curl -fsSL "$PATCH_URL" > "$PATCH_FILE"
if git apply --check "$PATCH_FILE" 2>/dev/null; then
  git apply "$PATCH_FILE"
  find agent/__pycache__ -name "anthropic_adapter*.pyc" -o -name "bedrock_adapter*.pyc" 2>/dev/null | xargs rm -f 2>/dev/null || true
  echo "✓ Patch applied"
else
  echo "✓ Patch already applied (skipping)"
fi
rm -f "$PATCH_FILE"

# Resolve token — env var or prompt
TOKEN="${AWS_BEARER_TOKEN_BEDROCK:-}"
if [ -z "$TOKEN" ]; then
  printf "AWS_BEARER_TOKEN_BEDROCK: " >/dev/tty
  read TOKEN </dev/tty
fi

# Resolve base URL — env var or prompt
BASE_URL="${ANTHROPIC_BEDROCK_BASE_URL:-}"
if [ -z "$BASE_URL" ]; then
  printf "ANTHROPIC_BEDROCK_BASE_URL: " >/dev/tty
  read BASE_URL </dev/tty
fi

# Resolve model — env var or prompt
MODEL="${HERMES_MODEL:-}"
if [ -z "$MODEL" ]; then
  printf "Model [claude-opus-4.6]: " >/dev/tty
  read MODEL </dev/tty
fi
MODEL="${MODEL:-claude-opus-4.6}"

# Write .env (replace if exists, append if not)
ENV_FILE="${HOME}/.hermes/.env"
touch "$ENV_FILE"
grep -v "^AWS_BEARER_TOKEN_BEDROCK=\|^ANTHROPIC_BEDROCK_BASE_URL=" "$ENV_FILE" > "${ENV_FILE}.tmp" || true
echo "AWS_BEARER_TOKEN_BEDROCK=${TOKEN}" >> "${ENV_FILE}.tmp"
echo "ANTHROPIC_BEDROCK_BASE_URL=${BASE_URL}" >> "${ENV_FILE}.tmp"
mv "${ENV_FILE}.tmp" "$ENV_FILE"

# Configure config.yaml
CONFIG_FILE="${HOME}/.hermes/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
  sed -i.bak 's/^  provider:.*/  provider: bedrock/' "$CONFIG_FILE"
  sed -i.bak '/^  base_url:/d' "$CONFIG_FILE"
  sed -i.bak '/^  api_key:/d' "$CONFIG_FILE"
  sed -i.bak '/^  api_mode:/d' "$CONFIG_FILE"
  sed -i.bak "s/^  default:.*/  default: ${MODEL}/" "$CONFIG_FILE"
  rm -f "${CONFIG_FILE}.bak"
fi

echo "✓ Done (provider: bedrock, model: ${MODEL})"
echo "  Restart gateway: hermes gateway restart"
