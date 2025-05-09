#!/usr/bin/env python3
"""
Demo script to test the TripSage Travel Agent.
"""
import os
import sys
from dotenv import load_dotenv
from travel_agent import TravelAgent

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in your .env file or environment.")
        sys.exit(1)
    
    # Check for Supabase credentials
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        print("Warning: Supabase credentials are not set.")
        print("Database operations will not work without SUPABASE_URL and SUPABASE_ANON_KEY.")
    
    print("Initializing TripSage Travel Agent...")
    agent = TravelAgent()
    
    print("Creating a new conversation thread...")
    agent.create_thread()
    
    # Display demo options
    print("\nTripSage Agent Demo")
    print("-------------------")
    print("This demo allows you to interact with the TripSage Travel Agent.")
    print("You can ask about trip planning, search for flights/accommodations, etc.\n")
    
    while True:
        # Get user input
        user_message = input("You: ")
        
        # Check for exit command
        if user_message.lower() in ["exit", "quit", "bye"]:
            print("Ending conversation. Goodbye!")
            break
        
        # Add message to thread
        print("Sending message to agent...")
        agent.add_message(user_message)
        
        # Run the agent
        print("Waiting for response...")
        agent.run_thread()
        
        # Get and display response
        response = agent.get_last_response()
        print("\nAgent:", response)
        print()
    
    # Clean up resources
    print("Cleaning up resources...")
    agent.delete_resources()
    print("Demo completed successfully!")

if __name__ == "__main__":
    main()