# TripSage Supabase Ops (Next.js-only stack)

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
	@echo "  make supa.db.push                               # Apply DB migrations to remote"
	@echo "  make supa.migration.list                        # Inspect remote migration history"
	@echo "  make supa.migration.repair VERSION=... STATUS=applied|reverted"

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
