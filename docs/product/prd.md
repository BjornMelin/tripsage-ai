# Product Requirements Document (PRD)

## Product vision

TripSage AI is an AI-powered travel planning application that helps a user:

- define constraints and preferences
- build and iterate on itineraries
- save, organize, and share trip plans
- use chat and tools to explore options quickly

## Primary users

- Individual travelers planning a trip
- Small groups collaborating on an itinerary

## Core flows

1) Onboarding and auth

- Sign up / login
- Create first trip

2) Trip planning

- Create trip
- Add constraints (dates, budget, style)
- Search places and save candidates
- Build itinerary timeline

3) AI chat assistance

- Ask TripSage questions scoped to a trip
- Accept tool-driven itinerary edits (with approval where needed)
- Store results as notes and memories

4) Memory and attachments

- Upload confirmations or documents
- Auto-ingest into trip memory
- Use memory in chat responses

## Non-functional requirements

- Security baseline: OWASP ASVS L2 target
- Low-latency streaming AI responses
- Strong type safety: Zod v4 + strict TS
- Reliability: jobs idempotent, retries, audit logs
