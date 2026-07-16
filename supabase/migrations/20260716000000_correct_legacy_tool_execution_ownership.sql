-- AI SDK v6 marked every terminal app tool result as provider-executed even
-- though TripSage exposed only locally executed tools. AI SDK v7 uses this bit
-- to choose the provider continuation protocol, so repair the legacy rows
-- before deploying the v7 runtime.

UPDATE public.chat_tool_calls
SET provider_executed = false
WHERE provider_executed = true
  AND status IN ('completed', 'failed');
