#!/usr/bin/env node

/**
 * Test script to verify WebSocket connection between frontend and backend
 * 
 * Usage: node scripts/test-websocket.js
 */

const WebSocket = require('ws');

// Configuration
const WS_URL = 'ws://localhost:8000/api/ws/chat/test-session-123';
const TEST_TOKEN = 'test-jwt-token-123';

console.log('🔧 Testing WebSocket Connection...');
console.log(`📍 URL: ${WS_URL}`);
console.log(`🔑 Token: ${TEST_TOKEN.substring(0, 20)}...`);

// Create WebSocket connection
const ws = new WebSocket(WS_URL, {
  headers: {
    'Authorization': `Bearer ${TEST_TOKEN}`,
  }
});

// Handle connection events
ws.on('open', () => {
  console.log('✅ WebSocket connected successfully!');
  
  // Send test message
  const testMessage = {
    type: 'chat_message',
    content: 'Hello from test script!',
    sessionId: 'test-session-123',
  };
  
  console.log('📤 Sending test message:', testMessage);
  ws.send(JSON.stringify(testMessage));
  
  // Close connection after 5 seconds
  setTimeout(() => {
    console.log('🔌 Closing connection...');
    ws.close();
  }, 5000);
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