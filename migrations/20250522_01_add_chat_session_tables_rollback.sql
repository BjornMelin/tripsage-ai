-- Rollback Migration: Add Chat Session Tables
-- Description: Removes chat session management tables and related objects
-- Created: 2025-05-22

-- Drop triggers
DROP TRIGGER IF EXISTS audit_chat_sessions ON chat_sessions;
DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;

-- Drop views
DROP VIEW IF EXISTS active_chat_sessions;

-- Drop functions
DROP FUNCTION IF EXISTS audit_chat_session_changes();
DROP FUNCTION IF EXISTS expire_inactive_sessions(INTEGER);
DROP FUNCTION IF EXISTS cleanup_old_sessions(INTEGER);
DROP FUNCTION IF EXISTS get_recent_messages(UUID, INTEGER, INTEGER, INTEGER, INTEGER);

-- Drop tables (in reverse order of dependencies)
DROP TABLE IF EXISTS chat_session_audit CASCADE;
DROP TABLE IF EXISTS chat_tool_calls CASCADE;
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;

-- Drop indexes (if they weren't dropped with tables)
DROP INDEX IF EXISTS idx_chat_tool_calls_tool_name;
DROP INDEX IF EXISTS idx_chat_tool_calls_status;
DROP INDEX IF EXISTS idx_chat_tool_calls_message_id;
DROP INDEX IF EXISTS idx_chat_messages_role;
DROP INDEX IF EXISTS idx_chat_messages_created_at;
DROP INDEX IF EXISTS idx_chat_messages_session_id;
DROP INDEX IF EXISTS idx_chat_sessions_updated_at;
DROP INDEX IF EXISTS idx_chat_sessions_created_at;
DROP INDEX IF EXISTS idx_chat_sessions_user_id;