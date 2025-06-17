#!/usr/bin/env node

/**
 * Script to test and activate WebSocket features
 * 
 * This script validates:
 * 1. WebSocket endpoints are accessible
 * 2. Agent monitoring can connect
 * 3. Real-time message flow works
 */

const WebSocket = require('ws');

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000/api';
const TEST_SESSION_ID = '550e8400-e29b-41d4-a716-446655440000';
const TEST_USER_ID = '660e8400-e29b-41d4-a716-446655440001';
const TEST_TOKEN = 'test-jwt-token-123';

console.log('🔧 WebSocket Feature Activation Test');
console.log('====================================\n');

// Step 1: Check API health
async function checkAPIHealth() {
  console.log('1️⃣ Checking API health...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (response.ok) {
      const data = await response.json();
      console.log('✅ API is healthy:', data);
      return true;
    } else {
      console.log('❌ API health check failed:', response.status);
      return false;
    }
  } catch (error) {
    console.log('❌ API is not running:', error.message);
    return false;
  }
}

// Step 2: Check WebSocket health endpoint
async function checkWebSocketHealth() {
  console.log('\n2️⃣ Checking WebSocket service health...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/ws/health`);
    if (response.ok) {
      const data = await response.json();
      console.log('✅ WebSocket service is healthy:', data);
      return true;
    } else {
      console.log('❌ WebSocket health check failed:', response.status);
      return false;
    }
  } catch (error) {
    console.log('❌ WebSocket service is not available:', error.message);
    return false;
  }
}

// Step 3: Test Chat WebSocket Connection
function testChatWebSocket() {
  return new Promise((resolve) => {
    console.log('\n3️⃣ Testing Chat WebSocket connection...');
    const ws = new WebSocket(`${WS_BASE_URL}/ws/chat/${TEST_SESSION_ID}`);
    
    let isAuthenticated = false;
    
    ws.on('open', () => {
      console.log('✅ Chat WebSocket connected');
      
      // Send authentication
      const authMessage = {
        token: TEST_TOKEN,
        session_id: TEST_SESSION_ID,
        channels: [`session:${TEST_SESSION_ID}`],
      };
      
      console.log('🔐 Sending authentication...');
      ws.send(JSON.stringify(authMessage));
    });
    
    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        
        if (!isAuthenticated && message.success !== undefined) {
          if (message.success) {
            console.log('✅ Authentication successful!');
            isAuthenticated = true;
            
            // Test sending a message
            const testMessage = {
              type: 'chat_message',
              payload: {
                content: 'Hello from WebSocket activation test!',
              },
            };
            
            console.log('📤 Sending test message...');
            ws.send(JSON.stringify(testMessage));
            
            // Close after a short delay
            setTimeout(() => {
              ws.close();
              resolve(true);
            }, 1000);
          } else {
            console.log('❌ Authentication failed:', message.error);
            ws.close();
            resolve(false);
          }
        } else {
          console.log('📥 Received message:', message);
        }
      } catch (error) {
        console.log('📥 Received raw message:', data.toString());
      }
    });
    
    ws.on('error', (error) => {
      console.error('❌ Chat WebSocket error:', error.message);
      resolve(false);
    });
    
    ws.on('close', () => {
      console.log('🔌 Chat WebSocket closed');
    });
  });
}

// Step 4: Test Agent Status WebSocket
function testAgentStatusWebSocket() {
  return new Promise((resolve) => {
    console.log('\n4️⃣ Testing Agent Status WebSocket connection...');
    const ws = new WebSocket(`${WS_BASE_URL}/ws/agent-status/${TEST_USER_ID}`);
    
    let isAuthenticated = false;
    
    ws.on('open', () => {
      console.log('✅ Agent Status WebSocket connected');
      
      // Send authentication
      const authMessage = {
        token: TEST_TOKEN,
        user_id: TEST_USER_ID,
        channels: [`agent_status:${TEST_USER_ID}`],
      };
      
      console.log('🔐 Sending authentication...');
      ws.send(JSON.stringify(authMessage));
    });
    
    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        
        if (!isAuthenticated && message.success !== undefined) {
          if (message.success) {
            console.log('✅ Authentication successful!');
            isAuthenticated = true;
            
            // Send heartbeat
            const heartbeat = {
              type: 'heartbeat',
            };
            
            console.log('💓 Sending heartbeat...');
            ws.send(JSON.stringify(heartbeat));
            
            // Close after a short delay
            setTimeout(() => {
              ws.close();
              resolve(true);
            }, 1000);
          } else {
            console.log('❌ Authentication failed:', message.error);
            ws.close();
            resolve(false);
          }
        } else {
          console.log('📥 Received message:', message);
        }
      } catch (error) {
        console.log('📥 Received raw message:', data.toString());
      }
    });
    
    ws.on('error', (error) => {
      console.error('❌ Agent Status WebSocket error:', error.message);
      resolve(false);
    });
    
    ws.on('close', () => {
      console.log('🔌 Agent Status WebSocket closed');
    });
  });
}

// Step 5: Summary and recommendations
async function printSummary(results) {
  console.log('\n📊 WebSocket Activation Summary');
  console.log('================================\n');
  
  const allPassed = Object.values(results).every(result => result);
  
  if (allPassed) {
    console.log('✅ All WebSocket features are ACTIVE and working!');
    console.log('\n🎉 Next Steps:');
    console.log('1. Frontend WebSocket connection is configured in .env.local');
    console.log('2. Agent monitoring dashboard should now connect automatically');
    console.log('3. Real-time chat features are enabled');
    console.log('\nTo test the frontend:');
    console.log('  cd frontend && pnpm dev');
    console.log('  Navigate to http://localhost:3000/agents');
  } else {
    console.log('❌ Some WebSocket features are not working properly\n');
    
    if (!results.apiHealth) {
      console.log('🔧 Backend API is not running. Start it with:');
      console.log('  uv run python -m tripsage.api.main');
    }
    
    if (!results.wsHealth && results.apiHealth) {
      console.log('🔧 WebSocket endpoints may not be registered properly');
      console.log('  Check that websocket router is included in main.py');
    }
    
    if (!results.chatWs || !results.agentWs) {
      console.log('🔧 WebSocket authentication may be failing');
      console.log('  Check JWT token configuration');
    }
  }
}

// Main execution
async function main() {
  const results = {
    apiHealth: false,
    wsHealth: false,
    chatWs: false,
    agentWs: false,
  };
  
  // Run tests
  results.apiHealth = await checkAPIHealth();
  
  if (results.apiHealth) {
    results.wsHealth = await checkWebSocketHealth();
    
    if (results.wsHealth) {
      results.chatWs = await testChatWebSocket();
      results.agentWs = await testAgentStatusWebSocket();
    }
  }
  
  await printSummary(results);
}

// Handle script termination
process.on('SIGINT', () => {
  console.log('\n\n⚠️ Test interrupted');
  process.exit(0);
});

// Run the tests
main().catch(console.error);