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
	@echo "  make supa.functions.deploy-all PROJECT_REF=...  # Deploy all Edge Functions"
	@echo "  make supa.fn.deploy FN=<name> PROJECT_REF=...   # Deploy one Edge Function"
	@echo "  make supa.fn.logs   FN=<name> PROJECT_REF=...   # Tail logs for one function"

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

# Helper: rename Deno v5 lockfiles so the CLI bundler (older Deno) doesn't error
.PHONY: supa.functions.prepare-locks
supa.functions.prepare-locks:
	@set -e; for d in supabase/functions/*; do \
		if [ -f "$$d/deno.lock" ]; then mv "$$d/deno.lock" "$$d/deno.lock.v5"; fi; \
	done

.PHONY: supa.fn.deploy
supa.fn.deploy: supa.functions.prepare-locks
	@if [ -z "$(PROJECT_REF)" ] || [ -z "$(FN)" ]; then echo "PROJECT_REF and FN required"; exit 1; fi
	$(SUPABASE_CLI) functions deploy $(FN) --project-ref $(PROJECT_REF) --debug

.PHONY: supa.functions.deploy-all
supa.functions.deploy-all: supa.functions.prepare-locks
	@if [ -z "$(PROJECT_REF)" ]; then echo "PROJECT_REF is required"; exit 1; fi
	$(SUPABASE_CLI) functions deploy trip-notifications --project-ref $(PROJECT_REF) --debug
	$(SUPABASE_CLI) functions deploy file-processing    --project-ref $(PROJECT_REF) --debug
	$(SUPABASE_CLI) functions deploy cache-invalidation --project-ref $(PROJECT_REF) --debug
	$(SUPABASE_CLI) functions deploy file-processor     --project-ref $(PROJECT_REF) --debug

.PHONY: supa.fn.logs
supa.fn.logs:
	@if [ -z "$(PROJECT_REF)" ] || [ -z "$(FN)" ]; then echo "PROJECT_REF and FN required"; exit 1; fi
	$(SUPABASE_CLI) functions logs $(FN) --project-ref $(PROJECT_REF) --tail
