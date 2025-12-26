/**
 * @fileoverview RAG (Retrieval-Augmented Generation) schemas. Includes document indexing, hybrid search, and reranking validation.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for RAG operations

/**
 * Supported namespaces for document organization.
 * Each namespace creates a logical partition of documents.
 */
export const ragNamespaceSchema = z.enum([
  "default",
  "accommodations",
  "destinations",
  "activities",
  "travel_tips",
  "user_content",
]);

/** TypeScript type for RAG namespaces. */
export type RagNamespace = z.infer<typeof ragNamespaceSchema>;

/**
 * Zod schema for document metadata.
 * Arbitrary key-value pairs for filtering and context.
 */
export const ragMetadataSchema = z.looseRecord(z.string(), z.unknown()).default({});

/** TypeScript type for document metadata. */
export type RagMetadata = z.infer<typeof ragMetadataSchema>;

/**
 * Zod schema for a single document to be indexed.
 * Contains content, optional ID, and metadata for filtering.
 */
export const ragDocumentSchema = z.object({
  content: z.string().min(1, { error: "Document content cannot be empty" }),
  id: primitiveSchemas.uuid.optional(),
  metadata: ragMetadataSchema.optional(),
  sourceId: z.string().optional(),
});

/** TypeScript type for documents to be indexed. */
export type RagDocument = z.infer<typeof ragDocumentSchema>;

/**
 * Zod schema for a document chunk with embedding.
 * Represents a processed chunk ready for storage.
 */
export const ragChunkSchema = z.object({
  chunkIndex: z.number().int().nonnegative(),
  content: z.string().min(1),
  embedding: z
    .array(z.number())
    .length(1536, { error: "Embedding must be 1536 dimensions" }),
  id: primitiveSchemas.uuid,
  metadata: ragMetadataSchema,
  namespace: ragNamespaceSchema,
  sourceId: z.string().nullable(),
});

/** TypeScript type for document chunks. */
export type RagChunk = z.infer<typeof ragChunkSchema>;

/**
 * Zod schema for search results before reranking.
 * Includes hybrid search scores.
 */
export const ragSearchResultSchema = z.object({
  chunkIndex: z.number().int().nonnegative(),
  combinedScore: z.number().min(0),
  content: z.string(),
  id: primitiveSchemas.uuid,
  keywordRank: z.number().nonnegative(),
  metadata: ragMetadataSchema,
  namespace: ragNamespaceSchema,
  rerankScore: z.number().min(0).max(1).optional(),
  similarity: z.number().min(0).max(1),
  sourceId: z.string().nullable(),
});

/** TypeScript type for search results. */
export type RagSearchResult = z.infer<typeof ragSearchResultSchema>;

// ===== API REQUEST SCHEMAS =====
// Request schemas for RAG API endpoints

/**
 * Zod schema for POST /api/rag/index request body.
 * Validates batch document indexing parameters.
 */
export const ragIndexRequestSchema = z.object({
  chunkOverlap: z.number().int().min(0).max(500).default(100),
  chunkSize: z.number().int().min(100).max(2000).default(512),
  documents: z.array(ragDocumentSchema).min(1).max(100, {
    error: "Maximum 100 documents per batch",
  }),
  namespace: ragNamespaceSchema.default("default"),
});

/** TypeScript type for index requests. */
export type RagIndexRequest = z.infer<typeof ragIndexRequestSchema>;

/**
 * Zod schema for POST /api/rag/search request body.
 * Validates hybrid search with optional reranking.
 *
 * `keywordWeight` and `semanticWeight` are independent multipliers used directly
 * by the hybrid ranking function. Defaults are 0.3 and 0.7 respectively; they
 * do not need to sum to 1.0.
 */
export const ragSearchRequestSchema = z.object({
  keywordWeight: z.number().min(0).max(1).default(0.3),
  limit: z.number().int().min(1).max(50).default(10),
  namespace: ragNamespaceSchema.optional(),
  query: z.string().min(1, { error: "Search query cannot be empty" }),
  semanticWeight: z.number().min(0).max(1).default(0.7),
  threshold: z.number().min(0).max(1).default(0.7),
  useReranking: z.boolean().default(true),
});

/** TypeScript type for search requests. */
export type RagSearchRequest = z.infer<typeof ragSearchRequestSchema>;

// ===== API RESPONSE SCHEMAS =====
// Response schemas for RAG API endpoints

/**
 * Zod schema for failed document in index response.
 * Tracks which documents failed and why.
 */
export const ragIndexFailedDocSchema = z.object({
  error: z.string(),
  index: z.number().int().nonnegative(),
});

/** TypeScript type for failed documents. */
export type RagIndexFailedDoc = z.infer<typeof ragIndexFailedDocSchema>;

/**
 * Zod schema for POST /api/rag/index response.
 * Includes counts and failed document details.
 */
export const ragIndexResponseSchema = z.object({
  chunksCreated: z.number().int().nonnegative(),
  failed: z.array(ragIndexFailedDocSchema),
  indexed: z.number().int().nonnegative(),
  namespace: ragNamespaceSchema,
  success: z.boolean(),
  total: z.number().int().nonnegative(),
});

/** TypeScript type for index responses. */
export type RagIndexResponse = z.infer<typeof ragIndexResponseSchema>;

/**
 * Zod schema for POST /api/rag/search response.
 * Includes results and performance metadata.
 */
export const ragSearchResponseSchema = z.object({
  latencyMs: z.number().nonnegative(),
  query: z.string(),
  rerankingApplied: z.boolean(),
  results: z.array(ragSearchResultSchema),
  success: z.boolean(),
  total: z.number().int().nonnegative(),
});

/** TypeScript type for search responses. */
export type RagSearchResponse = z.infer<typeof ragSearchResponseSchema>;

// ===== TOOL INPUT SCHEMAS =====
// Schemas for RAG tool input validation

/**
 * Schema for ragSearch tool input.
 * Validates RAG search parameters for AI tools.
 */
export const ragSearchInputSchema = z.object({
  limit: z.number().int().min(1).max(20).default(5),
  namespace: ragNamespaceSchema.optional(),
  query: z.string().min(1, { error: "Query is required" }),
  threshold: z.number().min(0).max(1).default(0.7),
});

/** TypeScript type for RAG search tool input. */
export type RagSearchInput = z.infer<typeof ragSearchInputSchema>;

// ===== TOOL OUTPUT SCHEMAS =====
// Schemas for RAG tool output validation

export const ragSearchToolResultSchema = z.object({
  chunkIndex: z.number().int().nonnegative(),
  content: z.string(),
  metadata: ragMetadataSchema,
  namespace: ragNamespaceSchema,
  score: z.number().min(0).max(1),
  sourceId: z.string().nullable(),
});

export const ragSearchToolOutputSchema = z.object({
  latencyMs: z.number().nonnegative(),
  results: z.array(ragSearchToolResultSchema),
  total: z.number().int().nonnegative(),
});

export type RagSearchToolOutput = z.infer<typeof ragSearchToolOutputSchema>;

// ===== INTERNAL SCHEMAS =====
// Schemas for internal RAG operations

/**
 * Zod schema for reranker configuration.
 * Used to configure the pluggable reranker.
 */
export const rerankerConfigSchema = z.object({
  maxRetries: z.number().int().min(0).max(3).default(2),
  provider: z.enum(["together", "noop"]).default("together"),
  timeout: z.number().int().min(100).max(5000).default(700),
  topN: z.number().int().min(1).max(50).default(10),
});

/** TypeScript type for reranker configuration. */
export type RerankerConfig = z.infer<typeof rerankerConfigSchema>;

/**
 * Zod schema for rerank result.
 * Output from the reranking operation.
 */
export const rerankResultSchema = z.object({
  index: z.number().int().nonnegative(),
  relevanceScore: z.number().min(0).max(1),
});

/** TypeScript type for rerank results. */
export type RerankResult = z.infer<typeof rerankResultSchema>;

/**
 * Zod schema for indexer configuration.
 * Used to configure document chunking and embedding.
 */
export const indexerConfigSchema = z.object({
  batchSize: z.number().int().min(1).max(100).default(10),
  chunkOverlap: z.number().int().min(0).max(500).default(100),
  chunkSize: z.number().int().min(100).max(2000).default(512),
  namespace: ragNamespaceSchema.default("default"),
});

/** TypeScript type for indexer configuration. */
export type IndexerConfig = z.infer<typeof indexerConfigSchema>;

/**
 * Zod schema for retriever configuration.
 * Used to configure hybrid search behavior.
 */
export const retrieverConfigSchema = z.object({
  keywordWeight: z.number().min(0).max(1).default(0.3),
  limit: z.number().int().min(1).max(100).default(10),
  namespace: ragNamespaceSchema.optional(),
  semanticWeight: z.number().min(0).max(1).default(0.7),
  threshold: z.number().min(0).max(1).default(0.7),
  useReranking: z.boolean().default(true),
});

/** TypeScript type for retriever configuration. */
export type RetrieverConfig = z.infer<typeof retrieverConfigSchema>;
