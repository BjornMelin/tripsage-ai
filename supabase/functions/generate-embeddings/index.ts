/**
 * @fileoverview Supabase Edge Function for generating embeddings.
 *
 * Generates embeddings using @xenova/transformers and Supabase/gte-small model.
 * Accepts text input and returns 384-dimensional embedding vector.
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.43.4";

// Initialize Supabase client
const supabaseUrl = Deno.env.get("SUPABASE_URL");
const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY");

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing Supabase environment variables");
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

/**
 * Generate embedding using @xenova/transformers.
 *
 * Uses Supabase/gte-small model (384 dimensions) for semantic search.
 */
async function generateEmbedding(text: string): Promise<number[]> {
  // Dynamic import for Deno compatibility
  const { pipeline } = await import(
    "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1"
  );

  // Use singleton pattern for the pipeline
  class EmbeddingPipeline {
    static task = "feature-extraction";
    static model = "Supabase/gte-small";
    static instance: Awaited<
      ReturnType<typeof pipeline>
    > | null = null;

    static async getInstance() {
      if (this.instance === null) {
        this.instance = await pipeline(this.task, this.model, {
          quantized: true, // Use quantized model for faster loading
        });
      }
      return this.instance;
    }
  }

  const generateEmbeddingPipeline = await EmbeddingPipeline.getInstance();
  const output = await generateEmbeddingPipeline(text, {
    pooling: "mean",
    normalize: true,
  });

  const embedding = Array.from(output.data) as number[];

  if (embedding.length !== 384) {
    throw new Error(
      `Expected 384 dimensions, got ${embedding.length}`
    );
  }

  return embedding;
}

serve(async (req) => {
  try {
    // Handle CORS preflight
    if (req.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "authorization, content-type",
        },
      });
    }

    if (req.method !== "POST") {
      return new Response(
        JSON.stringify({ error: "Method not allowed" }),
        { status: 405, headers: { "Content-Type": "application/json" } }
      );
    }

    const { text, property } = await req.json();

    // Support both direct text embedding and property object embedding
    let textToEmbed: string;
    if (property) {
      // Combine property fields for richer embedding
      const name = property.name || "";
      const description = property.description || "";
      const amenities = Array.isArray(property.amenities)
        ? property.amenities.join(", ")
        : property.amenities || "";
      textToEmbed = `${name}. Description: ${description}. Amenities: ${amenities}`;
    } else if (text) {
      textToEmbed = text;
    } else {
      return new Response(
        JSON.stringify({ error: 'Missing "text" or "property" in request body' }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    if (!textToEmbed || textToEmbed.trim().length === 0) {
      return new Response(
        JSON.stringify({ error: "Text cannot be empty" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Generate embedding
    const embedding = await generateEmbedding(textToEmbed);

    // If property object provided, optionally upsert to accommodations table
    if (property && property.id) {
      try {
        const { error: upsertError } = await supabase
          .from("accommodations")
          .upsert({
            id: property.id,
            source: property.source || property.type || "hotel",
            name: property.name,
            description: property.description,
            amenities: Array.isArray(property.amenities)
              ? property.amenities.join(", ")
              : property.amenities,
            embedding: embedding,
            updated_at: new Date().toISOString(),
          })
          .select();

        if (upsertError) {
          console.error("Failed to upsert accommodation:", upsertError);
          // Continue even if upsert fails - return embedding anyway
        }
      } catch (upsertErr) {
        console.error("Upsert error:", upsertErr);
        // Continue even if upsert fails
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        embedding,
        ...(property?.id ? { id: property.id } : {}),
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    console.error("Embedding generation error:", errorMessage);
    return new Response(
      JSON.stringify({ error: errorMessage }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  }
});

