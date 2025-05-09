from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads import Run
from typing import Dict, List, Any, Optional, Callable
from tenacity import retry, stop_after_attempt, wait_exponential
import uuid
import json
import time
from config import config

class BaseAgent:
    """Base class for all TripSage agents"""
    
    def __init__(
        self,
        name: str,
        instructions: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.model = model or config.model_name
        self.metadata = metadata or {"agent_type": "tripsage"}
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=config.openai_api_key)
        
        # Create assistant
        self.assistant = self._create_assistant()
        
        # Store thread and run info
        self.thread = None
        self.run = None
        self.messages_history = []
    
    def _create_assistant(self) -> Assistant:
        """Create or retrieve an assistant"""
        return self.client.beta.assistants.create(
            name=self.name,
            instructions=self.instructions,
            tools=self.tools,
            model=self.model,
            metadata=self.metadata
        )
    
    def create_thread(self) -> Thread:
        """Create a new thread for this agent"""
        self.thread = self.client.beta.threads.create()
        self.messages_history = []
        return self.thread
    
    def add_message(self, content: str, metadata: Optional[Dict[str, str]] = None) -> None:
        """Add a message to the thread"""
        if not self.thread:
            self.create_thread()
        
        # Add message to thread
        message = self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=content,
            metadata=metadata or {}
        )
        
        # Store message in history
        self.messages_history.append({
            "role": "user",
            "content": content,
            "created_at": time.time()
        })
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def run_thread(
        self,
        additional_instructions: Optional[str] = None,
        tool_outputs: Optional[List[Dict[str, Any]]] = None
    ) -> Run:
        """Run the thread with the assistant"""
        if not self.thread:
            raise ValueError("Thread not created. Call create_thread() first")
        
        # Create run
        self.run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            instructions=additional_instructions,
            tool_outputs=tool_outputs
        )
        
        # Wait for completion
        return self._wait_for_completion()
    
    def _wait_for_completion(self) -> Run:
        """Wait for the run to complete"""
        while self.run.status in ["queued", "in_progress"]:
            time.sleep(1)
            self.run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=self.run.id
            )
            
            # Handle tool calls
            if self.run.status == "requires_action":
                self._handle_tool_calls()
        
        # Check for errors
        if self.run.status == "failed":
            error_message = f"Run failed: {self.run.last_error.code} - {self.run.last_error.message}"
            raise RuntimeError(error_message)
        
        # Add assistant messages to history
        self._update_message_history()
        
        return self.run
    
    def _handle_tool_calls(self) -> None:
        """
        Handle tool calls from the assistant.
        Override this method in subclasses to implement custom tool handling.
        """
        tool_outputs = []
        
        for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
            tool_output = {
                "tool_call_id": tool_call.id,
                "output": json.dumps({"error": "Tool not implemented"})
            }
            tool_outputs.append(tool_output)
        
        # Submit tool outputs
        self.run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=self.run.id,
            tool_outputs=tool_outputs
        )
    
    def _update_message_history(self) -> None:
        """Update message history with assistant responses"""
        # Get messages since last update
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id,
            order="asc"
        )
        
        # Filter new messages (assistant role)
        new_messages = [
            msg for msg in messages.data 
            if msg.role == "assistant" and not any(
                hist_msg.get("assistant_id") == msg.id 
                for hist_msg in self.messages_history
            )
        ]
        
        # Add to history
        for msg in new_messages:
            content_text = ""
            for content in msg.content:
                if content.type == "text":
                    content_text += content.text.value
            
            self.messages_history.append({
                "role": "assistant",
                "content": content_text,
                "assistant_id": msg.id,
                "created_at": time.time()
            })
    
    def get_last_response(self) -> Optional[str]:
        """Get the last assistant response from the thread"""
        assistant_messages = [msg for msg in self.messages_history if msg["role"] == "assistant"]
        if not assistant_messages:
            return None
        return assistant_messages[-1]["content"]
    
    def get_full_conversation(self) -> List[Dict[str, Any]]:
        """Get the full conversation history"""
        return self.messages_history
    
    def delete_resources(self) -> None:
        """Delete the assistant and thread to clean up resources"""
        if self.assistant:
            self.client.beta.assistants.delete(assistant_id=self.assistant.id)
            self.assistant = None
        
        if self.thread:
            self.client.beta.threads.delete(thread_id=self.thread.id)
            self.thread = None