# Phase 3: Tool Calling & MCP Integration - Implementation Prompt

## Context
You are implementing Phase 3 of the AI Chat Integration for TripSage. Phase 1 (Chat API Endpoint Enhancement and Session Management) was completed in PR #118 and PR #122. Phase 2 (Authentication & BYOK Integration) has been completed in PR #123. The frontend chat interface is fully functional with Vercel AI SDK v4.3.16, the backend BYOK system is operational, and comprehensive authentication is in place.

## Your Task
Implement Phase 3: Tool Calling & MCP Integration as outlined in `tasks/TODO-INTEGRATION.md`. This phase connects the chat interface with TripSage's specialized agents and MCP servers to enable intelligent tool calling for travel planning tasks.

## Tool Usage Instructions

### 1. Start with Research
```
- Use Read tool to examine: tasks/TODO-INTEGRATION.md (lines 114-160)
- Use Read tool to examine: tripsage/agents/travel.py
- Use Read tool to examine: tripsage/agents/base.py
- Use Read tool to examine: tripsage/agents/handoffs/helper.py
- Use Read tool to examine: tripsage/mcp_abstraction/manager.py
- Use Read tool to examine: tripsage/tools/ directory structure
- Use Read tool to examine: frontend/src/components/features/chat/messages/message-tool-calls.tsx
```

### 2. Create TODO List
```
Use TodoWrite tool to create a comprehensive task list based on Phase 3 requirements
```

### 3. Implementation Order
1. Agent Integration (Section 3.1)
2. Tool Calling Interface (Section 3.2)
3. Frontend Tool Display (Section 3.3)
4. Testing & Optimization (Section 3.4)

### 4. Key Files to Modify
```
Backend:
- tripsage/agents/chat.py (new file - chat agent controller)
- tripsage/api/routers/chat.py (integrate tool calling)
- tripsage/api/models/chat.py (add tool call models)
- tripsage/agents/handoffs/helper.py (enhance agent routing)

Frontend:
- frontend/src/components/features/chat/messages/message-tool-calls.tsx
- frontend/src/types/chat.ts (add tool call types)
- frontend/src/hooks/use-chat-ai.ts (handle tool call responses)
- frontend/src/components/features/chat/chat-container.tsx (display tool calls)
```

### 5. Testing Approach
```
- Use Write tool to create: tests/agents/test_chat_agent.py
- Use Write tool to create: tests/integration/test_tool_calling_flow.py
- Use Write tool to create: frontend/src/components/features/chat/__tests__/tool-calls.test.tsx
- Run tests with: cd frontend && pnpm test
- Run backend tests with: cd /home/bjorn/repos/agents/openai/tripsage-ai && uv run pytest tests/agents/ tests/integration/
```

## Key Documentation References

### Agent Architecture
- **Base Agent**: `tripsage/agents/base.py` - Core agent functionality and patterns
- **Travel Agent**: `tripsage/agents/travel.py` - Main travel planning agent
- **Agent Handoffs**: `tripsage/agents/handoffs/helper.py` - Agent routing and delegation
- **Flight Agent**: `tripsage/agents/flight.py` - Specialized flight operations
- **Accommodation Agent**: `tripsage/agents/accommodation.py` - Hotel/lodging operations

### MCP Integration
- **MCP Manager**: `tripsage/mcp_abstraction/manager.py` - Central MCP coordination
- **MCP Registry**: `tripsage/mcp_abstraction/registry.py` - Service registration
- **Tool Schemas**: `tripsage/tools/schemas/` - Tool definitions and validation
- **Wrapper Implementations**: `tripsage/mcp_abstraction/wrappers/` - Service wrappers

### Frontend Components
- **Tool Calls Display**: `frontend/src/components/features/chat/messages/message-tool-calls.tsx`
- **Message Types**: `frontend/src/types/chat.ts` - Type definitions
- **Chat Interface**: `frontend/src/components/features/chat/chat-interface.tsx`

### Security Requirements
- Tool calls must respect user API key permissions
- Validate tool inputs and sanitize outputs
- Rate limiting for tool operations (5 tool calls/minute per user)
- Audit logging for all tool executions
- Error handling without sensitive information exposure

## Phase 3 Checklist

### 3.1 Agent Orchestration
- [ ] Create chat agent controller (`tripsage/agents/chat.py`)
- [ ] Implement agent routing based on user intent
- [ ] Integrate with existing agent handoff patterns
- [ ] Add tool call coordination between agents
- [ ] Implement agent context sharing and memory
- [ ] Create agent selection logic (flight vs accommodation vs general)

### 3.2 Tool Calling Interface
- [ ] Enhance chat API to support tool calls
- [ ] Integrate MCP servers (flights, accommodations, maps, weather)
- [ ] Add tool call validation and error handling
- [ ] Implement tool response formatting
- [ ] Add tool execution monitoring and logging
- [ ] Create tool call rate limiting per user

### 3.3 Frontend Tool Display
- [ ] Enhance MessageToolCalls component for rich display
- [ ] Add loading states for tool execution
- [ ] Display tool results in user-friendly format
- [ ] Add interactive elements for tool results (maps, bookings)
- [ ] Implement tool call error display
- [ ] Add tool execution progress indicators

### 3.4 Advanced Features
- [ ] Implement multi-step tool workflows
- [ ] Add tool call history and context
- [ ] Create tool call suggestions based on conversation
- [ ] Implement tool call cancellation
- [ ] Add tool preference management for users
- [ ] Create tool call analytics and optimization

## Code Patterns to Follow

### Agent Integration
```python
# In tripsage/agents/chat.py
class ChatAgent(BaseAgent):
    """Central chat agent that coordinates with specialized agents."""
    
    def __init__(self):
        super().__init__()
        self.flight_agent = FlightAgent()
        self.accommodation_agent = AccommodationAgent()
        self.travel_agent = TravelPlanningAgent()
    
    async def process_message(self, message: str, context: dict) -> dict:
        """Process user message and route to appropriate agent."""
        intent = await self.detect_intent(message)
        
        if intent == "flight_search":
            return await self.flight_agent.run(message, context)
        elif intent == "accommodation_search":
            return await self.accommodation_agent.run(message, context)
        else:
            return await self.travel_agent.run(message, context)
```

### Tool Call Integration
```python
# In chat router
@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: UserDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    api_key_valid: bool = Depends(verify_api_key),
):
    # Get chat agent
    chat_agent = get_chat_agent()
    
    # Process with tool calling
    response = await chat_agent.run_with_tools(
        message=last_message.content,
        context=context,
        available_tools=get_user_available_tools(current_user)
    )
    
    # Handle tool calls in response
    if response.get("tool_calls"):
        tool_results = await execute_tool_calls(
            response["tool_calls"], 
            current_user
        )
        response["tool_results"] = tool_results
```

### Frontend Tool Display
```typescript
// In MessageToolCalls component
interface ToolCall {
  id: string;
  name: string;
  parameters: Record<string, any>;
  status: 'pending' | 'executing' | 'completed' | 'error';
  result?: any;
  error?: string;
}

export function MessageToolCalls({ toolCalls }: { toolCalls: ToolCall[] }) {
  return (
    <div className="tool-calls-container">
      {toolCalls.map(call => (
        <ToolCallCard 
          key={call.id} 
          toolCall={call}
          onRetry={handleRetry}
        />
      ))}
    </div>
  );
}
```

## Testing Requirements
- Unit tests for all agent components
- Integration tests for tool calling flow
- E2E tests for complete chat experience with tools
- Performance tests for tool execution
- Security tests for tool access control
- Frontend tests for tool call UI components

## Success Criteria
1. Chat interface can execute travel-related tools (flights, hotels, maps)
2. Tool calls are properly authenticated and rate limited
3. Tool results are displayed in user-friendly format
4. Agent routing works correctly based on user intent
5. MCP integration functions seamlessly
6. Tool call error handling is robust
7. All tests pass with >90% coverage
8. Performance meets requirements (<2s for tool execution)

## Important Notes
- Follow KISS principle - don't over-engineer tool calling
- Use existing MCP patterns and abstractions
- Maintain compatibility with Vercel AI SDK
- Ensure mobile responsiveness for tool displays
- Run `ruff check --fix` and `ruff format .` on Python files
- Run `npx biome lint --apply` and `npx biome format --write` on TypeScript files

## MCP Server Integration Guide

### Available MCP Servers
- **Flights**: Search flights, get prices, booking assistance
- **Accommodations**: Find hotels, compare prices, availability
- **Google Maps**: Location search, directions, place details
- **Weather**: Current conditions, forecasts, travel weather
- **Time**: Timezone handling, scheduling assistance
- **WebCrawl**: Travel information gathering and research

### Tool Call Flow
1. User sends message with travel intent
2. Chat agent analyzes intent and selects appropriate tools
3. MCP manager executes tool calls via appropriate servers
4. Results are formatted and returned to user
5. Frontend displays results with interactive elements

### Error Handling
- Graceful degradation when MCP servers unavailable
- Clear error messages for tool failures
- Fallback to text responses when tools fail
- Retry mechanisms for transient failures

## References
- Phase 1: PR #118 (Chat API Endpoint) & PR #122 (Session Management)
- Phase 2: PR #123 (Authentication & BYOK Integration)
- Vercel AI SDK Tool Calling: https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#tool-calling
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- MCP Protocol: https://modelcontextprotocol.io/docs

Start by reading the TODO-INTEGRATION.md file to understand the full scope of Phase 3, then create a comprehensive TODO list before beginning implementation. Focus on creating a seamless tool calling experience that enhances the travel planning capabilities of TripSage.