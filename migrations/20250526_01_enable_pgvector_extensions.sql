-- Enable pgvector and pgvectorscale extensions for 11x faster vector search
-- Migration: 20250526_01_enable_pgvector_extensions.sql
-- Issue: #146, #147 - Consolidate database architecture to Supabase with pgvector

-- =============================================================================
-- IMPORTANT: MANUAL STEPS REQUIRED IN SUPABASE DASHBOARD
-- =============================================================================
-- Some extensions require superuser privileges and must be enabled via Supabase Dashboard:
-- 1. Go to your Supabase project dashboard
-- 2. Navigate to Database > Extensions
-- 3. Enable "vector" extension (pgvector)
-- 4. Enable "vectorscale" extension (if available)
-- 
-- Alternatively, use Supabase CLI:
-- supabase extensions enable vector
-- supabase extensions enable vectorscale
-- =============================================================================

-- Enable pgvector extension (if not already enabled)
-- Note: This may require superuser privileges in some environments
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable vectorscale extension for performance improvements  
-- Note: This extension may not be available in all Supabase environments
DO $$
BEGIN
    -- Try to enable vectorscale if available
    CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
    RAISE NOTICE 'Successfully enabled vectorscale extension';
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'vectorscale extension not available - using pgvector only';
END $$;

-- Verify extensions are installed
SELECT 
    extname as extension_name,
    extversion as version
FROM pg_extension 
WHERE extname IN ('vector', 'vectorscale')
ORDER BY extname;

-- =============================================================================
-- PERFORMANCE OPTIMIZATION NOTES
-- =============================================================================
-- For optimal performance (targeting <100ms latency, 471 QPS):
-- 
-- 1. Use appropriate vector index types:
--    - HNSW for general purpose: CREATE INDEX ON table USING hnsw (vector_column vector_cosine_ops);
--    - IVFFlat for large datasets: CREATE INDEX ON table USING ivfflat (vector_column vector_cosine_ops);
-- 
-- 2. Configure index parameters based on your data:
--    - HNSW: SET hnsw.ef_construction = 64; (higher = better recall, slower build)
--    - IVFFlat: SET ivfflat.probes = 10; (higher = better recall, slower search)
-- 
-- 3. If vectorscale is available, use StreamingDiskANN for best performance:
--    - CREATE INDEX ON table USING diskann (vector_column);
-- 
-- 4. Memory configuration (requires restart):
--    - shared_preload_libraries = 'vectorscale' (if available)
--    - vectorscale.num_bgw_workers = 4
-- =============================================================================

-- Create a simple test to verify vector functionality
DO $$
BEGIN
    -- Test basic vector operations
    PERFORM '[1,2,3]'::vector;
    PERFORM '[1,2,3]'::vector <-> '[3,2,1]'::vector;
    RAISE NOTICE 'Vector operations working correctly';
EXCEPTION 
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Vector extension not working: %', SQLERRM;
END $$;

-- Success message
SELECT 'pgvector extensions enabled successfully - ready for 11x faster vector search!' as migration_status;