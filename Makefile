# TripSage Supabase Ops
# Usage examples:
#   make supa.link PROJECT_REF=<PROJECT_REF>
#   make supa.secrets-min SUPABASE_URL=https://<PROJECT_REF>.supabase.co SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=...
#   make supa.db.push
#   make supa.functions.deploy-all PROJECT_REF=<PROJECT_REF>
#   make supa.fn.logs FN=cache-invalidation PROJECT_REF=<PROJECT_REF>
#   make supa.migration.repair VERSION=20251027 STATUS=reverted

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

SUPABASE_CLI ?= npx supabase@2.53.6
PROJECT_REF   ?=

.PHONY: help
help:
	@echo "Supabase operations"
	@echo "  make supa.link PROJECT_REF=<ref>                 # Link repo to hosted project"
	@echo "  make supa.secrets-min SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=..."
	@echo "  make supa.secrets-upstash UPSTASH_REDIS_REST_URL=... UPSTASH_REDIS_REST_TOKEN=..."
	@echo "  make supa.secrets-webhooks WEBHOOK_SECRET=...    # Optional function/webhook secret"
	@echo "  make supa.secrets-from-env ENV=.env               # Load common keys from a dotenv file"
	@echo "  make supa.db.push                               # Apply DB migrations to remote"
	@echo "  make supa.migration.list                        # Inspect remote migration history"
	@echo "  make supa.migration.repair VERSION=... STATUS=applied|reverted"
	@echo "  make webhooks.setup WEBHOOK_TRIPS_URL=... WEBHOOK_CACHE_URL=... HMAC_SECRET=... DATABASE_URL=..."
	@echo "  make webhooks.test   WEBHOOK_URL=... HMAC_SECRET=... PAYLOAD='{}'"

.PHONY: supa.link
supa.link:
	@if [ -z "$(PROJECT_REF)" ]; then echo "PROJECT_REF is required"; exit 1; fi
	$(SUPABASE_CLI) link --project-ref $(PROJECT_REF) --debug

.PHONY: supa.secrets-min
supa.secrets-min:
	@if [ -z "$$SUPABASE_URL" ] || [ -z "$$SUPABASE_ANON_KEY" ] || [ -z "$$SUPABASE_SERVICE_ROLE_KEY" ]; then \
		echo "Set SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY (env)"; exit 1; fi
	$(SUPABASE_CLI) secrets set \
		SUPABASE_URL="$$SUPABASE_URL" \
		SUPABASE_ANON_KEY="$$SUPABASE_ANON_KEY" \
		SUPABASE_SERVICE_ROLE_KEY="$$SUPABASE_SERVICE_ROLE_KEY"

.PHONY: supa.secrets-upstash
supa.secrets-upstash:
	@if [ -z "$$UPSTASH_REDIS_REST_URL" ] || [ -z "$$UPSTASH_REDIS_REST_TOKEN" ]; then \
		echo "Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN (env)"; exit 1; fi
	$(SUPABASE_CLI) secrets set \
		UPSTASH_REDIS_REST_URL="$$UPSTASH_REDIS_REST_URL" \
		UPSTASH_REDIS_REST_TOKEN="$$UPSTASH_REDIS_REST_TOKEN"

.PHONY: supa.secrets-webhooks
supa.secrets-webhooks:
	@if [ -z "$$WEBHOOK_SECRET" ]; then echo "Set WEBHOOK_SECRET (env)"; exit 1; fi
	$(SUPABASE_CLI) secrets set WEBHOOK_SECRET="$$WEBHOOK_SECRET"

.PHONY: supa.secrets-from-env
supa.secrets-from-env:
	@if [ -z "$(ENV)" ]; then echo "Usage: make supa.secrets-from-env ENV=.env"; exit 1; fi
	./scripts/supabase/secrets_from_env.sh $(ENV)

.PHONY: supa.db.push
supa.db.push:
	$(SUPABASE_CLI) db push --yes --debug

.PHONY: supa.migration.list
supa.migration.list:
	$(SUPABASE_CLI) migration list --debug

.PHONY: supa.migration.repair
supa.migration.repair:
	@if [ -z "$(VERSION)" ] || [ -z "$(STATUS)" ]; then \
		echo "Usage: make supa.migration.repair VERSION=20251027 STATUS=applied|reverted"; exit 1; fi
	$(SUPABASE_CLI) migration repair --status $(STATUS) $(VERSION) --debug

# Removed Supabase Edge Function deploy/log targets — superseded by Database Webhooks to Vercel
# Webhook setup using operator script
.PHONY: webhooks.setup
webhooks.setup:
	@if [ -z "$$WEBHOOK_TRIPS_URL" ] || [ -z "$$WEBHOOK_CACHE_URL" ] || [ -z "$$HMAC_SECRET" ] || [ -z "$$DATABASE_URL" ]; then \
		echo "Usage: make webhooks.setup WEBHOOK_TRIPS_URL=... WEBHOOK_CACHE_URL=... HMAC_SECRET=... DATABASE_URL=..."; exit 1; fi
	WEBHOOK_TRIPS_URL="$$WEBHOOK_TRIPS_URL" \
	WEBHOOK_CACHE_URL="$$WEBHOOK_CACHE_URL" \
	HMAC_SECRET="$$HMAC_SECRET" \
	DATABASE_URL="$$DATABASE_URL" \
	bash scripts/operators/setup_webhooks.sh

# Quick HMAC test against a webhook URL
.PHONY: webhooks.test
webhooks.test:
	@if [ -z "$$WEBHOOK_URL" ] || [ -z "$$HMAC_SECRET" ] || [ -z "$$PAYLOAD" ]; then \
		echo "Usage: make webhooks.test WEBHOOK_URL=... HMAC_SECRET=... PAYLOAD='{""type"":""INSERT"",""table"":""trip_collaborators""}'"; exit 1; fi
	@sig=$$(printf "%s" "$$PAYLOAD" | openssl dgst -sha256 -hmac "$$HMAC_SECRET" -hex | sed 's/^.* //'); \
	echo "Signature: $$sig"; \
	curl -i -H 'Content-Type: application/json' -H "X-Signature-HMAC: $$sig" -d "$$PAYLOAD" "$$WEBHOOK_URL"
