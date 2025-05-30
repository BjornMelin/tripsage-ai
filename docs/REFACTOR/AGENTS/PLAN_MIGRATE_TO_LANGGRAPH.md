# LangGraph Migration Plan: Complete Implementation Blueprint

## Migration Overview

This document provides a comprehensive, actionable plan for migrating TripSage
AI's agent orchestration from OpenAI Agents SDK to LangGraph. The migration
will transform the current fragmented orchestration into a sophisticated
graph-based workflow system.

## Pre-Migration Setup

### Dependencies and Installation

```bash
# Core LangGraph dependencies
uv add langgraph langchain-core langchain-openai
uv add langsmith  # For monitoring and debugging
uv add pydantic>=2.0  # Already in project
uv add typing-extensions  # For TypedDict support
```

### Environment Configuration

```env
# Add to .env
LANGSMITH_API_KEY=your_langsmith_key  # For debugging and monitoring
LANGSMITH_PROJECT=tripsage-langgraph
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=${LANGSMITH_API_KEY}
LANGCHAIN_PROJECT=${LANGSMITH_PROJECT}
```

## Phase 1: Foundation Architecture (Weeks 1-2)

### 1.1 State Schema Design

**New File**: `tripsage/orchestration/state.py`

```python
from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import add_messages
from tripsage.models.base import TripSageModel

class TravelPlanningState(TypedDict):
    """Unified state schema for all travel planning workflows"""
    
    # Core conversation data
    messages: Annotated[List[dict], add_messages]
    user_id: str
    session_id: str
    
    # User context
    user_preferences: Optional[Dict]
    budget_constraints: Optional[Dict]
    travel_dates: Optional[Dict]
    destination_info: Optional[Dict]
    
    # Search and booking state
    flight_searches: List[Dict]
    accommodation_searches: List[Dict]
    activity_searches: List[Dict]
    booking_progress: Optional[Dict]
    
    # Agent coordination
    current_agent: Optional[str]
    agent_history: List[str]
    handoff_context: Optional[Dict]
    
    # Error handling
    error_count: int
    last_error: Optional[str]
    retry_attempts: Dict[str, int]
    
    # Tool call tracking
    active_tool_calls: List[Dict]
    completed_tool_calls: List[Dict]
```

### 1.2 Base Node Structure

**New File**: `tripsage/orchestration/nodes/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.utils.logging_utils import get_logger

class BaseAgentNode(ABC):
    """Base class for all LangGraph agent nodes"""
    
    def __init__(self, node_name: str, config: Dict[str, Any] = None):
        self.node_name = node_name
        self.config = config or {}
        self.logger = get_logger(f"orchestration.{node_name}")
        self._initialize_tools()
    
    @abstractmethod
    def _initialize_tools(self):
        """Initialize node-specific tools"""
        pass
    
    @abstractmethod
    def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process the current state and return updated state"""
        pass
    
    def __call__(self, state: TravelPlanningState) -> TravelPlanningState:
        """Main entry point for node execution"""
        try:
            self.logger.info(f"Executing {self.node_name} node")
            updated_state = self.process(state)
            updated_state["agent_history"].append(self.node_name)
            return updated_state
        except Exception as e:
            self.logger.error(f"Error in {self.node_name}: {str(e)}")
            return self._handle_error(state, e)
    
    def _handle_error(self, state: TravelPlanningState, error: Exception) -> TravelPlanningState:
        """Standardized error handling"""
        state["error_count"] += 1
        state["last_error"] = str(error)
        state["retry_attempts"][self.node_name] = state["retry_attempts"].get(self.node_name, 0) + 1
        return state
```

### 1.3 Core Orchestrator Graph

**New File**: `tripsage/orchestration/graph.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.nodes import *
from tripsage.orchestration.routing import RouterNode

class TripSageOrchestrator:
    """Main LangGraph orchestrator for TripSage AI"""
    
    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
    
    def _build_graph(self) -> StateGraph:
        """Construct the main orchestration graph"""
        graph = StateGraph(TravelPlanningState)
        
        # Core nodes
        graph.add_node("router", RouterNode())
        graph.add_node("flight_agent", FlightAgentNode())
        graph.add_node("accommodation_agent", AccommodationAgentNode())
        graph.add_node("budget_agent", BudgetAgentNode())
        graph.add_node("itinerary_agent", ItineraryAgentNode())
        graph.add_node("destination_agent", DestinationAgentNode())
        graph.add_node("travel_agent", TravelAgentNode())
        
        # Utility nodes
        graph.add_node("memory_update", MemoryUpdateNode())
        graph.add_node("error_recovery", ErrorRecoveryNode())
        graph.add_node("user_approval", UserApprovalNode())
        
        # Entry point
        graph.set_entry_point("router")
        
        # Conditional routing from router
        graph.add_conditional_edges(
            "router",
            self._route_to_agent,
            {
                "flight": "flight_agent",
                "accommodation": "accommodation_agent",
                "budget": "budget_agent",
                "itinerary": "itinerary_agent",
                "destination": "destination_agent",
                "travel": "travel_agent",
                "error": "error_recovery",
                "end": END
            }
        )
        
        # Agent completion flows
        for agent in ["flight_agent", "accommodation_agent", "budget_agent", 
                     "itinerary_agent", "destination_agent", "travel_agent"]:
            graph.add_conditional_edges(
                agent,
                self._determine_next_step,
                {
                    "continue": "router",
                    "approval": "user_approval",
                    "memory": "memory_update",
                    "error": "error_recovery",
                    "end": END
                }
            )
        
        # Utility node flows
        graph.add_edge("memory_update", "router")
        graph.add_edge("user_approval", "router")
        graph.add_conditional_edges(
            "error_recovery",
            self._handle_recovery,
            {
                "retry": "router",
                "escalate": END,
                "end": END
            }
        )
        
        return graph
    
    def _route_to_agent(self, state: TravelPlanningState) -> str:
        """Determine which agent should handle the current state"""
        # Implement semantic routing logic
        pass
    
    def _determine_next_step(self, state: TravelPlanningState) -> str:
        """Determine the next step after agent completion"""
        # Implement workflow logic
        pass
    
    def _handle_recovery(self, state: TravelPlanningState) -> str:
        """Handle error recovery decisions"""
        # Implement recovery logic
        pass
    
    async def process_message(self, user_id: str, message: str, session_id: str = None) -> dict:
        """Main entry point for processing user messages"""
        initial_state = {
            "messages": [{"role": "user", "content": message}],
            "user_id": user_id,
            "session_id": session_id or f"session_{user_id}_{int(time.time())}",
            "user_preferences": None,
            "budget_constraints": None,
            "travel_dates": None,
            "destination_info": None,
            "flight_searches": [],
            "accommodation_searches": [],
            "activity_searches": [],
            "booking_progress": None,
            "current_agent": None,
            "agent_history": [],
            "handoff_context": None,
            "error_count": 0,
            "last_error": None,
            "retry_attempts": {},
            "active_tool_calls": [],
            "completed_tool_calls": []
        }
        
        config = {"configurable": {"thread_id": session_id}}
        result = await self.compiled_graph.ainvoke(initial_state, config=config)
        
        return {
            "response": result["messages"][-1]["content"],
            "state": result,
            "session_id": session_id
        }
```

## Phase 2: Agent Node Migration (Weeks 3-4)

### 2.1 Router Node Implementation

**New File**: `tripsage/orchestration/routing.py`

```python
from typing import Dict, List
from langchain_openai import ChatOpenAI
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState

class RouterNode(BaseAgentNode):
    """Intelligent routing node using semantic analysis"""
    
    def __init__(self):
        super().__init__("router")
        self.classifier = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )
    
    def _initialize_tools(self):
        """Router doesn't need external tools"""
        pass
    
    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Analyze user intent and route to appropriate agent"""
        last_message = state["messages"][-1]["content"]
        
        # Enhanced semantic classification
        classification_prompt = f"""
        Analyze this travel-related message and classify the primary intent:
        
        Message: "{last_message}"
        
        Available agents:
        - flight: Flight search, booking, changes
        - accommodation: Hotels, rentals, lodging
        - budget: Budget planning, cost analysis
        - itinerary: Trip planning, scheduling, activities
        - destination: Destination research, recommendations
        - travel: General travel assistance, documentation
        
        Respond with JSON: {{"agent": "agent_name", "confidence": 0.9, "reasoning": "explanation"}}
        """
        
        response = await self.classifier.ainvoke([{"role": "user", "content": classification_prompt}])
        classification = json.loads(response.content)
        
        # Update state with routing decision
        state["current_agent"] = classification["agent"]
        state["handoff_context"] = {
            "routing_confidence": classification["confidence"],
            "routing_reasoning": classification["reasoning"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return state
```

### 2.2 Specialized Agent Nodes

**New File**: `tripsage/orchestration/nodes/flight_agent.py`

```python
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.tools.flight_tools import FlightSearchTools
from tripsage.mcp_abstraction.manager import MCPManager

class FlightAgentNode(BaseAgentNode):
    """Flight search and booking agent node"""
    
    def __init__(self):
        super().__init__("flight_agent")
        self.mcp_manager = MCPManager()
    
    def _initialize_tools(self):
        """Initialize flight-specific tools"""
        self.flight_tools = FlightSearchTools()
        # Register MCP tools
        self.mcp_manager.initialize_mcp()
    
    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process flight-related requests"""
        user_message = state["messages"][-1]["content"]
        
        # Extract flight search parameters
        search_params = await self._extract_search_parameters(user_message, state)
        
        if search_params:
            # Perform flight search using MCP integration
            search_results = await self.mcp_manager.invoke(
                "flights", 
                "search_flights", 
                search_params
            )
            
            # Update state with results
            state["flight_searches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "parameters": search_params,
                "results": search_results,
                "agent": "flight_agent"
            })
            
            # Generate response
            response_message = await self._generate_response(search_results, state)
            state["messages"].append({
                "role": "assistant",
                "content": response_message,
                "agent": "flight_agent"
            })
        
        return state
    
    async def _extract_search_parameters(self, message: str, state: TravelPlanningState) -> Dict:
        """Extract flight search parameters from user message"""
        # Implement parameter extraction logic
        pass
    
    async def _generate_response(self, results: Dict, state: TravelPlanningState) -> str:
        """Generate user-friendly response from search results"""
        # Implement response generation logic
        pass
```

### 2.3 Memory and Session Integration

**New File**: `tripsage/orchestration/nodes/memory_update.py`

```python
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage_core.utils.session_utils import initialize_session_memory, update_session_memory
from tripsage.mcp_abstraction.manager import MCPManager

class MemoryUpdateNode(BaseAgentNode):
    """Node for updating persistent memory and session state"""
    
    def __init__(self):
        super().__init__("memory_update")
        self.mcp_manager = MCPManager()
    
    def _initialize_tools(self):
        """Initialize memory management tools"""
        pass
    
    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Update memory with conversation insights"""
        
        # Extract learnable information from conversation
        insights = await self._extract_insights(state)
        
        if insights:
            # Update knowledge graph via Memory MCP
            await self.mcp_manager.invoke(
                "memory",
                "add_observations",
                {
                    "observations": [
                        {
                            "entityName": f"user:{state['user_id']}",
                            "contents": insights
                        }
                    ]
                }
            )
            
            # Update Supabase session data
            await self._update_session_data(state)
        
        return state
    
    async def _extract_insights(self, state: TravelPlanningState) -> List[str]:
        """Extract learnable insights from conversation state"""
        insights = []
        
        # Extract budget preferences
        if state.get("budget_constraints"):
            insights.append(f"Budget range: {state['budget_constraints']}")
        
        # Extract travel preferences
        if state.get("user_preferences"):
            for pref_type, value in state["user_preferences"].items():
                insights.append(f"Prefers {pref_type}: {value}")
        
        # Extract destination interests
        if state.get("destination_info"):
            insights.append(f"Interested in destination: {state['destination_info'].get('name')}")
        
        return insights
    
    async def _update_session_data(self, state: TravelPlanningState):
        """Update session data in Supabase"""
        # Implement session persistence logic
        pass
```

## Phase 3: Integration and Testing (Weeks 5-6)

### 3.1 MCP Tool Integration

**New File**: `tripsage/orchestration/tools/mcp_integration.py`

```python
from typing import Dict, Any, List
from langchain.tools import BaseTool
from tripsage.mcp_abstraction.manager import MCPManager

class MCPToolWrapper(BaseTool):
    """Wrapper to integrate MCP tools with LangGraph"""
    
    def __init__(self, service_name: str, method_name: str, description: str):
        super().__init__()
        self.name = f"{service_name}_{method_name}"
        self.description = description
        self.service_name = service_name
        self.method_name = method_name
        self.mcp_manager = MCPManager()
    
    def _run(self, **kwargs) -> str:
        """Execute MCP tool call"""
        try:
            result = self.mcp_manager.invoke(
                self.service_name,
                self.method_name,
                kwargs
            )
            return json.dumps(result)
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async execution of MCP tool call"""
        return self._run(**kwargs)

class MCPToolRegistry:
    """Registry for all MCP tools available to LangGraph"""
    
    def __init__(self):
        self.tools = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all MCP tools for LangGraph use"""
        
        # Flight tools
        self.tools["search_flights"] = MCPToolWrapper(
            "flights", "search_flights",
            "Search for flights between destinations with dates and preferences"
        )
        
        # Accommodation tools
        self.tools["search_accommodations"] = MCPToolWrapper(
            "accommodations", "search_stays",
            "Search for hotels, rentals, and accommodations"
        )
        
        # Maps tools
        self.tools["geocode_location"] = MCPToolWrapper(
            "google_maps", "geocode",
            "Convert address to coordinates or get location details"
        )
        
        # Weather tools
        self.tools["get_weather"] = MCPToolWrapper(
            "weather", "get_current_weather",
            "Get current weather conditions for a location"
        )
        
        # Memory tools
        self.tools["search_memory"] = MCPToolWrapper(
            "memory", "search_nodes",
            "Search user's travel history and preferences"
        )
        
        # Add more MCP tools as needed
    
    def get_tool(self, tool_name: str) -> MCPToolWrapper:
        """Get a specific tool by name"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> List[MCPToolWrapper]:
        """Get all available tools"""
        return list(self.tools.values())
    
    def get_tools_for_agent(self, agent_name: str) -> List[MCPToolWrapper]:
        """Get tools relevant to a specific agent"""
        agent_tool_mapping = {
            "flight_agent": ["search_flights", "geocode_location", "get_weather"],
            "accommodation_agent": ["search_accommodations", "geocode_location"],
            "destination_agent": ["geocode_location", "get_weather", "search_memory"],
            "budget_agent": ["search_memory"],
            "itinerary_agent": ["geocode_location", "get_weather", "search_memory"],
            "travel_agent": ["search_memory", "geocode_location"]
        }
        
        tool_names = agent_tool_mapping.get(agent_name, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
```

### 3.2 Error Recovery and Resilience

**New File**: `tripsage/orchestration/nodes/error_recovery.py`

```python
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState

class ErrorRecoveryNode(BaseAgentNode):
    """Sophisticated error handling and recovery"""
    
    def __init__(self):
        super().__init__("error_recovery")
        self.max_retries = 3
        self.escalation_threshold = 5
    
    def _initialize_tools(self):
        """No external tools needed for error recovery"""
        pass
    
    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Handle errors with intelligent recovery strategies"""
        
        error_count = state.get("error_count", 0)
        last_error = state.get("last_error", "")
        current_agent = state.get("current_agent", "")
        
        # Determine recovery strategy
        if error_count < self.max_retries:
            return await self._attempt_retry(state)
        elif error_count < self.escalation_threshold:
            return await self._attempt_fallback(state)
        else:
            return await self._escalate_to_human(state)
    
    async def _attempt_retry(self, state: TravelPlanningState) -> TravelPlanningState:
        """Retry with modified parameters"""
        
        # Clear the error and attempt retry
        state["last_error"] = None
        state["retry_attempts"][state["current_agent"]] = state["retry_attempts"].get(state["current_agent"], 0) + 1
        
        # Add retry message
        state["messages"].append({
            "role": "assistant",
            "content": "I encountered an issue. Let me try a different approach...",
            "agent": "error_recovery"
        })
        
        # Reset to router for retry
        state["current_agent"] = "router"
        
        return state
    
    async def _attempt_fallback(self, state: TravelPlanningState) -> TravelPlanningState:
        """Use fallback strategies"""
        
        # Implement fallback logic
        fallback_message = "I'm having trouble with that specific request. Let me help you with a simpler approach or try manual search options."
        
        state["messages"].append({
            "role": "assistant",
            "content": fallback_message,
            "agent": "error_recovery"
        })
        
        # Reset state for fallback
        state["current_agent"] = "travel_agent"  # Use general travel agent as fallback
        
        return state
    
    async def _escalate_to_human(self, state: TravelPlanningState) -> TravelPlanningState:
        """Escalate to human support"""
        
        escalation_message = """
        I apologize, but I'm experiencing technical difficulties that prevent me from completing your request. 
        A human travel specialist will be notified to assist you. In the meantime, you can:
        
        1. Try rephrasing your request
        2. Break down your request into smaller parts
        3. Contact our support team directly
        
        Your session has been saved and we'll follow up with you soon.
        """
        
        state["messages"].append({
            "role": "assistant",
            "content": escalation_message,
            "agent": "error_recovery"
        })
        
        # Log escalation for human review
        await self._log_escalation(state)
        
        return state
    
    async def _log_escalation(self, state: TravelPlanningState):
        """Log escalation for human support team"""
        # Implement escalation logging
        pass
```

### 3.3 Testing Infrastructure

**New File**: `tests/orchestration/test_langgraph_migration.py`

```python
import pytest
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.state import TravelPlanningState

class TestLangGraphMigration:
    """Comprehensive tests for LangGraph migration"""
    
    @pytest.fixture
    def orchestrator(self):
        return TripSageOrchestrator()
    
    @pytest.mark.asyncio
    async def test_basic_flight_search(self, orchestrator):
        """Test basic flight search workflow"""
        result = await orchestrator.process_message(
            user_id="test_user",
            message="I need a flight from NYC to LAX on March 15th"
        )
        
        assert result["response"] is not None
        assert "flight" in result["state"]["agent_history"]
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, orchestrator):
        """Test coordination between multiple agents"""
        # First request: Flight search
        result1 = await orchestrator.process_message(
            user_id="test_user",
            message="Find flights from NYC to LAX on March 15th",
            session_id="test_session"
        )
        
        # Second request: Hotel search
        result2 = await orchestrator.process_message(
            user_id="test_user", 
            message="Now find hotels near LAX for the same dates",
            session_id="test_session"
        )
        
        assert "flight" in result1["state"]["agent_history"]
        assert "accommodation" in result2["state"]["agent_history"]
        assert len(result2["state"]["flight_searches"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, orchestrator):
        """Test error recovery mechanisms"""
        # Simulate error condition
        result = await orchestrator.process_message(
            user_id="test_user",
            message="Find flights to invalid_destination_xyz"
        )
        
        # Should gracefully handle error
        assert result["response"] is not None
        assert "error" not in result["response"].lower() or "sorry" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_state_persistence(self, orchestrator):
        """Test state persistence across requests"""
        session_id = "persistence_test"
        
        # First interaction
        result1 = await orchestrator.process_message(
            user_id="test_user",
            message="I'm planning a trip to Paris",
            session_id=session_id
        )
        
        # Second interaction - should remember context
        result2 = await orchestrator.process_message(
            user_id="test_user",
            message="What's the weather like there?",
            session_id=session_id
        )
        
        # Should maintain context about Paris
        assert "paris" in result2["response"].lower() or "destination" in result2["state"]
```

## Phase 4: Production Deployment (Weeks 7-8)

### 4.1 Configuration Management

**New File**: `tripsage/orchestration/config.py`

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os

@dataclass
class LangGraphConfig:
    """Configuration for LangGraph orchestration"""
    
    # Core settings
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # State management
    checkpoint_storage: str = "memory"  # memory, postgres, redis
    checkpoint_connection_string: Optional[str] = None
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    escalation_threshold: int = 5
    
    # Monitoring
    enable_langsmith: bool = True
    langsmith_project: str = "tripsage-langgraph"
    
    # Performance
    parallel_execution: bool = True
    timeout_seconds: int = 30
    
    @classmethod
    def from_environment(cls) -> "LangGraphConfig":
        """Load configuration from environment variables"""
        return cls(
            default_model=os.getenv("LANGGRAPH_DEFAULT_MODEL", "gpt-4o"),
            temperature=float(os.getenv("LANGGRAPH_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LANGGRAPH_MAX_TOKENS", "4096")),
            checkpoint_storage=os.getenv("LANGGRAPH_CHECKPOINT_STORAGE", "memory"),
            checkpoint_connection_string=os.getenv("LANGGRAPH_CHECKPOINT_CONNECTION"),
            max_retries=int(os.getenv("LANGGRAPH_MAX_RETRIES", "3")),
            escalation_threshold=int(os.getenv("LANGGRAPH_ESCALATION_THRESHOLD", "5")),
            enable_langsmith=os.getenv("LANGGRAPH_ENABLE_LANGSMITH", "true").lower() == "true",
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "tripsage-langgraph"),
            parallel_execution=os.getenv("LANGGRAPH_PARALLEL_EXECUTION", "true").lower() == "true",
            timeout_seconds=int(os.getenv("LANGGRAPH_TIMEOUT_SECONDS", "30"))
        )
```

### 4.2 Monitoring and Observability

**New File**: `tripsage/orchestration/monitoring.py`

```python
from langsmith import trace, traceable
from typing import Dict, Any
import time
import json
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger("orchestration.monitoring")

class LangGraphMonitoring:
    """Monitoring and observability for LangGraph workflows"""
    
    def __init__(self, project_name: str = "tripsage-langgraph"):
        self.project_name = project_name
    
    @traceable(project_name="tripsage-langgraph")
    def trace_agent_execution(self, agent_name: str, input_state: Dict, output_state: Dict):
        """Trace individual agent execution"""
        return {
            "agent": agent_name,
            "input_state_size": len(str(input_state)),
            "output_state_size": len(str(output_state)),
            "messages_processed": len(input_state.get("messages", [])),
            "tools_called": len(output_state.get("completed_tool_calls", []))
        }
    
    @traceable(project_name="tripsage-langgraph")
    def trace_workflow_completion(self, session_id: str, total_time: float, final_state: Dict):
        """Trace complete workflow execution"""
        return {
            "session_id": session_id,
            "total_execution_time": total_time,
            "agents_used": final_state.get("agent_history", []),
            "tools_executed": len(final_state.get("completed_tool_calls", [])),
            "error_count": final_state.get("error_count", 0),
            "final_message_count": len(final_state.get("messages", []))
        }
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics"""
        logger.info(f"Performance metrics: {json.dumps(metrics)}")
    
    def log_error_details(self, error: Exception, state: Dict):
        """Log detailed error information"""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "current_agent": state.get("current_agent"),
            "error_count": state.get("error_count", 0),
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id")
        }
        logger.error(f"Orchestration error: {json.dumps(error_details)}")
```

## Migration Execution Checklist

### ✅ Phase 1: Foundation (Weeks 1-2)

- [ ] Install LangGraph dependencies (`uv add langgraph langchain-core langchain-openai`)
- [ ] Set up LangSmith monitoring account and API keys
- [ ] Create state schema (`TravelPlanningState`) in `tripsage/orchestration/state.py`
- [ ] Implement base node class (`BaseAgentNode`) in `tripsage/orchestration/nodes/base.py`
- [ ] Create core orchestrator graph in `tripsage/orchestration/graph.py`
- [ ] Set up checkpointing with MemorySaver (dev) and PostgresSaver (prod)
- [ ] Create basic routing node (`RouterNode`) with semantic classification
- [ ] Test basic graph compilation and execution

### ✅ Phase 2: Agent Migration (Weeks 3-4)

- [ ] Migrate FlightAgent to FlightAgentNode
- [ ] Migrate AccommodationAgent to AccommodationAgentNode  
- [ ] Migrate BudgetAgent to BudgetAgentNode
- [ ] Migrate ItineraryAgent to ItineraryAgentNode
- [ ] Migrate DestinationResearchAgent to DestinationAgentNode
- [ ] Migrate TravelAgent to TravelAgentNode
- [ ] Create MemoryUpdateNode for session persistence
- [ ] Create ErrorRecoveryNode for failure handling
- [ ] Create UserApprovalNode for human-in-the-loop workflows
- [ ] Implement MCP tool integration wrapper (`MCPToolWrapper`)
- [ ] Test individual agent nodes in isolation
- [ ] Test agent-to-agent handoffs and coordination

### ✅ Phase 3: Integration (Weeks 5-6)

- [ ] Integrate with existing MCP abstraction layer
- [ ] Update session memory utilities for LangGraph state
- [ ] Implement checkpointing with PostgreSQL for production
- [ ] Create comprehensive test suite for all workflows
- [ ] Test error recovery and retry mechanisms
- [ ] Test state persistence across sessions
- [ ] Performance testing and optimization
- [ ] Security review and validation

### ✅ Phase 4: Production (Weeks 7-8)

- [ ] Create production configuration management
- [ ] Set up LangSmith monitoring and alerting
- [ ] Implement logging and observability
- [ ] Create deployment scripts and configuration
- [ ] Gradual rollout with feature flags
- [ ] Monitor performance and error rates
- [ ] User acceptance testing
- [ ] Full production deployment

### ✅ Code Cleanup and Deprecation

- [ ] Mark old ChatAgent as deprecated
- [ ] Remove unused agent orchestration code
- [ ] Update API endpoints to use new orchestrator
- [ ] Update documentation and README
- [ ] Clean up obsolete imports and dependencies
- [ ] Archive old orchestration tests

### ✅ Post-Migration Validation

- [ ] Verify all user workflows function correctly
- [ ] Validate session persistence and memory
- [ ] Confirm MCP tool integration works
- [ ] Test error scenarios and recovery
- [ ] Validate performance improvements
- [ ] User feedback collection and analysis

## File Structure Changes

### New Directory Structure

```plaintext
tripsage/orchestration/
├── __init__.py
├── config.py              # LangGraph configuration
├── graph.py               # Main orchestrator graph
├── monitoring.py          # Observability and tracing
├── routing.py             # Semantic routing logic  
├── state.py               # State schema definitions
├── nodes/                 # Agent node implementations
│   ├── __init__.py
│   ├── base.py           # Base node class
│   ├── flight_agent.py   # Flight agent node
│   ├── accommodation_agent.py
│   ├── budget_agent.py
│   ├── itinerary_agent.py
│   ├── destination_agent.py
│   ├── travel_agent.py
│   ├── memory_update.py  # Memory persistence node
│   ├── error_recovery.py # Error handling node
│   └── user_approval.py  # Human-in-the-loop node
└── tools/                # LangGraph tool integrations
    ├── __init__.py
    └── mcp_integration.py # MCP tool wrappers
```

### Files to Deprecate/Remove

- `tripsage/agents/chat.py` (862 lines) → Replace with `TripSageOrchestrator`
- `tripsage/services/chat_orchestration.py` → Functionality moved to nodes
- Manual handoff logic in `BaseAgent` → Replaced by graph edges
- Intent detection in `ChatAgent` → Replaced by `RouterNode`

### Files to Update

- `tripsage/api/routers/chat.py` → Update to use new orchestrator
- API endpoints → Route through `TripSageOrchestrator.process_message()`
- Frontend chat interface → No changes needed (API compatible)
- Session management → Updated for LangGraph checkpointing

## Backward Compatibility Plan

### Gradual Migration Strategy

1. **Parallel Deployment**: Run both systems simultaneously with feature flag
2. **API Compatibility**: Maintain existing API contract during transition
3. **Session Migration**: Gradual migration of active sessions to new system
4. **Rollback Plan**: Ability to quickly revert to old system if issues arise

### Feature Flag Implementation

```python
# Feature flag for LangGraph migration
USE_LANGGRAPH_ORCHESTRATION = os.getenv("USE_LANGGRAPH_ORCHESTRATION", "false").lower() == "true"

async def process_chat_message(user_id: str, message: str, session_id: str = None):
    if USE_LANGGRAPH_ORCHESTRATION:
        orchestrator = TripSageOrchestrator()
        return await orchestrator.process_message(user_id, message, session_id)
    else:
        # Legacy ChatAgent processing
        chat_agent = ChatAgent()
        return await chat_agent.process_message(message, user_id, session_id)
```

## Success Metrics

### Performance Improvements

- **Response Time**: Target 40-60% reduction in average response time
- **Parallel Processing**: 2-5x improvement in multi-agent coordination speed
- **Memory Usage**: 30-50% reduction in memory overhead
- **Error Recovery**: 90% reduction in unrecoverable failures

### Code Quality Improvements  

- **Code Reduction**: 70% reduction in orchestration code complexity
- **Maintainability**: Modular nodes vs monolithic ChatAgent
- **Testability**: Independent testing of each workflow component
- **Debuggability**: Visual workflow debugging with LangSmith

### User Experience Improvements

- **Conversation Flow**: More natural multi-turn conversations
- **Context Retention**: Perfect context preservation across sessions
- **Error Handling**: Graceful degradation vs hard failures
- **Response Quality**: More contextually aware responses

This comprehensive migration plan provides a clear, actionable roadmap for
transforming TripSage's agent orchestration from a maintenance burden into a
competitive advantage using LangGraph's sophisticated workflow capabilities.
