#!/usr/bin/env node

/**
 * Test script to verify WebSocket connection between frontend and backend
 * 
 * Usage: node scripts/test-websocket.js
 */

const WebSocket = require('ws');

// Configuration
const WS_URL = 'ws://localhost:8000/api/ws/chat/550e8400-e29b-41d4-a716-446655440000'; // Valid UUID
const TEST_TOKEN = 'test-jwt-token-123';

console.log('🔧 Testing WebSocket Connection...');
console.log(`📍 URL: ${WS_URL}`);
console.log(`🔑 Token: ${TEST_TOKEN.substring(0, 20)}...`);

// Create WebSocket connection
const ws = new WebSocket(WS_URL);

// Handle connection events
ws.on('open', () => {
  console.log('✅ WebSocket connected successfully!');
  
  // Send authentication message first (backend expects this)
  const authMessage = {
    token: TEST_TOKEN,
    session_id: '550e8400-e29b-41d4-a716-446655440000',
    channels: ['session:550e8400-e29b-41d4-a716-446655440000'],
  };
  
  console.log('🔐 Sending authentication:', authMessage);
  ws.send(JSON.stringify(authMessage));
});

// State to track if we're authenticated
let isAuthenticated = false;

ws.on('message', (data) => {
  try {
    const message = JSON.parse(data.toString());
    console.log('📥 Received message:', message);
    
    // Check if this is the auth response
    if (message.success !== undefined && !isAuthenticated) {
      if (message.success) {
        console.log('✅ Authentication successful!');
        isAuthenticated = true;
        
        // Now send a test chat message
        const testMessage = {
          type: 'chat_message',
          payload: {
            content: 'Hello from test script!',
          },
        };
        
        console.log('📤 Sending test message:', testMessage);
        ws.send(JSON.stringify(testMessage));
        
        // Close connection after 3 seconds
        setTimeout(() => {
          console.log('🔌 Closing connection...');
          ws.close();
        }, 3000);
      } else {
        console.error('❌ Authentication failed:', message.error);
        ws.close();
      }
    }
  } catch (error) {
    console.log('📥 Received raw message:', data.toString());
  }
});

ws.on('message', (data) => {
  try {
    const message = JSON.parse(data.toString());
    console.log('📥 Received message:', message);
  } catch (error) {
    console.log('📥 Received raw message:', data.toString());
  }
});

ws.on('error', (error) => {
  console.error('❌ WebSocket error:', error.message);
});

ws.on('close', (code, reason) => {
  console.log(`🔌 WebSocket closed - Code: ${code}, Reason: ${reason || 'None'}`);
  process.exit(0);
});

// Handle script termination
process.on('SIGINT', () => {
  console.log('\n⚠️  Interrupted, closing connection...');
  ws.close();
  process.exit(0);
});