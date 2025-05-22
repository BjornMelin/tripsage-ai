import { StreamingTextResponse, AIStream, type AIStreamCallbacks } from 'ai';
import type { NextRequest } from 'next/server';

// This function simulates a streaming response from an AI model
// In production, this would connect to your API/LLM
function createSimulatedAIStream(prompt: string, callbacks?: AIStreamCallbacks) {
  // Sample chunks to simulate streaming
  const chunks = [
    { content: "I'm analyzing your travel query" },
    { content: " about" },
    { content: " " + prompt + "." },
    { content: " Here's what I found:" },
    { content: "\n\n" },
    { content: "TripSage can help you plan" },
    { content: " your perfect trip to " + prompt + "." },
    { content: " When would you like to travel?" },
  ];

  let lastContent = "";
  
  // Return a readable stream that emits chunks at intervals to simulate typing
  return new ReadableStream({
    async start(controller) {
      try {
        for (const chunk of chunks) {
          lastContent += chunk.content;
          const text = JSON.stringify({ content: lastContent });
          
          // Encode the text chunk
          const encoder = new TextEncoder();
          const encoded = encoder.encode(text);
          
          // Send chunk to stream
          controller.enqueue(encoded);
          
          // Simulate typing delay
          await new Promise(resolve => setTimeout(resolve, 300));
        }
      } catch (error) {
        // Handle errors
        controller.error(error);
      } finally {
        // Close the stream when finished
        controller.close();
      }
    }
  });
}

/**
 * POST handler for /api/chat
 * In production, this would connect to your TripSage AI backend
 */
export async function POST(req: NextRequest) {
  try {
    // Parse the request body
    const { messages, toolCalls } = await req.json();
    
    // Get the last user message
    const lastMessage = messages[messages.length - 1];
    
    // Simulate an AI stream based on the user's last message
    const stream = AIStream(
      createSimulatedAIStream(lastMessage.content),
      {
        onStart: async () => {
          console.log('Stream started');
        },
        onToken: async (token: string) => {
          // Process tokens if needed
        },
        onFinal: async (completion: string) => {
          console.log('Stream completed');
        },
      }
    );
    
    // Return the streaming response
    return new StreamingTextResponse(stream);
  } catch (error) {
    console.error('Error in chat API route:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to process chat request' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}