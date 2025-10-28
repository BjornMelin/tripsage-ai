#!/usr/bin/env bash
set -euo pipefail

# Load selected keys from a dotenv file and set them as Supabase project secrets via CLI.
#
# Usage:
#   scripts/supabase/secrets_from_env.sh path/to/.env
#
# Required:
#   - Supabase CLI available (npx supabase@2.53.6)

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

# Keys to load if present in the dotenv file
KEYS=(
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
  RESEND_API_KEY
  WEBHOOK_SECRET
)

declare -A KV
while IFS='=' read -r k v; do
  # Skip comments/empty lines
  [[ "$k" =~ ^\s*# ]] && continue
  [[ -z "$k" ]] && continue
  # Strip export and whitespace
  k="${k#export }"; k="${k%% *}"
  # Normalize quotes
  v="${v%\r}"; v="${v%\n}"; v="${v%\r}\n"; v="${v}"; v="${v%\n}"
  v="${v#\"}"; v="${v%\"}"
  v="${v#\'}"; v="${v%\'}"
  KV["$k"]="$v"
done < <(grep -E '^[A-Za-z_][A-Za-z0-9_]*\s*=\s*.*' "$ENV_FILE" || true)

SET_ARGS=()
for key in "${KEYS[@]}"; do
  if [[ -n "${KV[$key]:-}" ]]; then
    SET_ARGS+=("$key=${KV[$key]}")
  fi
done

if [[ ${#SET_ARGS[@]} -eq 0 ]]; then
  echo "No recognized keys found in $ENV_FILE" >&2
  exit 0
fi

echo "Setting ${#SET_ARGS[@]} Supabase secrets from $ENV_FILE" >&2
npx supabase@2.53.6 secrets set "${SET_ARGS[@]}"

