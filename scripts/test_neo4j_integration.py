#!/usr/bin/env python3
"""
Test Neo4j knowledge graph integration.

This script provides a command-line interface for testing the Neo4j knowledge
graph integration, allowing basic operations and synchronization with the
relational database.
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from src.db.neo4j.client import neo4j_client
from src.db.neo4j.sync import sync_destinations_to_knowledge_graph, sync_trips_to_knowledge_graph
from src.mcp.memory.client import memory_client
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


async def test_connection():
    """Test connection to Neo4j database."""
    try:
        await neo4j_client.initialize()
        print("✅ Successfully connected to Neo4j database")
        stats = await neo4j_client.get_graph_statistics()
        print(f"📊 Knowledge Graph Statistics:")
        print(f"  - Nodes: {stats['node_count']}")
        print(f"  - Relationships: {stats['relationship_count']}")
        print(f"  - Node Labels: {', '.join(stats['node_labels'].keys())}")
        print(f"  - Relationship Types: {', '.join(stats['relationship_types'].keys())}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j database: {str(e)}")
        return False


async def list_destinations(limit: int = 10):
    """List destinations in the knowledge graph.
    
    Args:
        limit: Maximum number of destinations to list
    """
    try:
        await neo4j_client.initialize()
        destinations = await neo4j_client.get_all_destinations(limit=limit)
        
        print(f"📍 Found {len(destinations)} destinations:")
        for i, dest in enumerate(destinations, 1):
            print(f"{i}. {dest.name} ({dest.country}) - {dest.type}")
            if dest.description:
                print(f"   {dest.description[:100]}...")
            if dest.safety_rating:
                print(f"   Safety: {dest.safety_rating}/5")
            if dest.cost_level:
                print(f"   Cost: {dest.cost_level}/5")
            print()
        
        return True
    except Exception as e:
        print(f"❌ Failed to list destinations: {str(e)}")
        return False


async def search_knowledge_graph(query: str, limit: int = 10):
    """Search the knowledge graph.
    
    Args:
        query: Search query
        limit: Maximum number of results to return
    """
    try:
        await neo4j_client.initialize()
        results = await neo4j_client.run_knowledge_graph_search(query, limit=limit)
        
        print(f"🔍 Search results for '{query}':")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['name']} ({result.get('type', 'Unknown')}) - Score: {result.get('score', 0):.2f}")
            if result.get('description'):
                print(f"   {result['description'][:100]}...")
            print()
        
        return True
    except Exception as e:
        print(f"❌ Failed to search knowledge graph: {str(e)}")
        return False


async def find_travel_route(from_dest: str, to_dest: str, max_stops: int = 2):
    """Find travel routes between destinations.
    
    Args:
        from_dest: Origin destination name
        to_dest: Destination name
        max_stops: Maximum number of intermediate stops
    """
    try:
        await neo4j_client.initialize()
        routes = await neo4j_client.find_travel_routes(from_dest, to_dest, max_stops)
        
        if not routes:
            print(f"❌ No routes found from {from_dest} to {to_dest} with {max_stops} max stops")
            return False
        
        print(f"🚀 Found {len(routes)} routes from {from_dest} to {to_dest}:")
        for i, route in enumerate(routes, 1):
            places = route.get('places', [])
            stops = len(places) - 2  # Exclude origin and destination
            
            print(f"Route {i}: {' -> '.join(places)} ({stops} stops)")
            
            connections = route.get('route_connections', [])
            for j, conn in enumerate(connections, 1):
                props = conn.get('properties', {})
                transport = props.get('transport', ['unknown'])
                distance = props.get('distance_km', 'unknown')
                
                print(f"  Leg {j}: {conn.get('from')} -> {conn.get('to')} "
                     f"({distance} km, {'/'.join(transport)})")
            
            print()
        
        return True
    except Exception as e:
        print(f"❌ Failed to find travel routes: {str(e)}")
        return False


async def get_travel_recommendations(interests: List[str], countries: Optional[List[str]] = None,
                               budget: Optional[int] = None):
    """Get travel recommendations based on interests and constraints.
    
    Args:
        interests: List of traveler interests
        countries: Optional list of preferred countries
        budget: Optional budget level constraint (1-5)
    """
    try:
        await neo4j_client.initialize()
        recommendations = await neo4j_client.find_travel_recommendations(
            interests, countries, budget
        )
        
        print(f"💡 Travel recommendations for interests: {', '.join(interests)}")
        if countries:
            print(f"   Countries: {', '.join(countries)}")
        if budget:
            print(f"   Budget level: {budget}/5")
        
        print()
        
        for i, rec in enumerate(recommendations, 1):
            match_score = rec.get('match_score', 0) * 100
            print(f"{i}. {rec['name']} ({rec['country']}) - Match: {match_score:.0f}%")
            
            if rec.get('description'):
                print(f"   {rec['description'][:100]}...")
            
            if rec.get('popular_for'):
                matching = [int for int in rec['popular_for'] if int in interests]
                print(f"   Matching interests: {', '.join(matching)}")
            
            print(f"   Cost: {rec.get('cost_level', '?')}/5, "
                 f"Safety: {rec.get('safety_rating', '?')}/5")
            print()
        
        return True
    except Exception as e:
        print(f"❌ Failed to get travel recommendations: {str(e)}")
        return False


async def sync_from_relational():
    """Synchronize data from relational database to knowledge graph."""
    try:
        print("🔄 Synchronizing destinations from relational database...")
        dest_stats = await sync_destinations_to_knowledge_graph()
        
        print(f"✅ Destination sync complete: "
             f"{dest_stats['created']} created, "
             f"{dest_stats['updated']} updated, "
             f"{dest_stats['failed']} failed")
        
        print("🔄 Synchronizing trips from relational database...")
        trip_stats = await sync_trips_to_knowledge_graph()
        
        print(f"✅ Trip sync complete: "
             f"{trip_stats['trips_created']} trips created, "
             f"{trip_stats['trips_updated']} trips updated, "
             f"{trip_stats['relationships_created']} relationships created, "
             f"{trip_stats['failed']} failed")
        
        return True
    except Exception as e:
        print(f"❌ Failed to sync from relational database: {str(e)}")
        return False


async def test_memory_mcp():
    """Test Memory MCP integration."""
    try:
        print("🧠 Testing Memory MCP integration...")
        
        # Initialize memory client
        await memory_client.initialize()
        
        # Create a test entity
        test_entity = {
            "name": "TestDestination",
            "entityType": "Destination",
            "observations": [
                "This is a test destination created through the Memory MCP.",
                "It should be visible in the Neo4j knowledge graph."
            ]
        }
        
        created = await memory_client.create_entities([test_entity])
        print(f"✅ Created entity: {created[0]['name']}")
        
        # Search for the entity
        found = await memory_client.search_nodes("test destination")
        print(f"✅ Found {len(found)} nodes matching search")
        
        # Get entity details
        details = await memory_client.open_nodes(["TestDestination"])
        if details:
            print(f"✅ Retrieved entity details:")
            print(f"  - Name: {details[0]['name']}")
            print(f"  - Type: {details[0]['type']}")
            print(f"  - Observations: {len(details[0]['observations'])}")
        
        # Delete the test entity
        deleted = await memory_client.delete_entities(["TestDestination"])
        print(f"✅ Deleted entity: {deleted[0]}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test Memory MCP: {str(e)}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test Neo4j knowledge graph integration')
    
    # Main commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Test connection
    test_parser = subparsers.add_parser('test', help='Test connection to Neo4j')
    
    # List destinations
    list_parser = subparsers.add_parser('list', help='List destinations in knowledge graph')
    list_parser.add_argument('--limit', type=int, default=10, help='Maximum number of destinations to list')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search knowledge graph')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum number of results')
    
    # Find route
    route_parser = subparsers.add_parser('route', help='Find travel route')
    route_parser.add_argument('from_dest', help='Origin destination name')
    route_parser.add_argument('to_dest', help='Destination name')
    route_parser.add_argument('--max-stops', type=int, default=2, help='Maximum number of intermediate stops')
    
    # Get recommendations
    rec_parser = subparsers.add_parser('recommend', help='Get travel recommendations')
    rec_parser.add_argument('interests', nargs='+', help='Traveler interests')
    rec_parser.add_argument('--countries', nargs='+', help='Preferred countries')
    rec_parser.add_argument('--budget', type=int, choices=range(1, 6), help='Budget level (1-5)')
    
    # Sync from relational
    sync_parser = subparsers.add_parser('sync', help='Sync from relational database')
    
    # Test Memory MCP
    memory_parser = subparsers.add_parser('memory', help='Test Memory MCP integration')
    
    args = parser.parse_args()
    
    if args.command == 'test':
        await test_connection()
    elif args.command == 'list':
        await list_destinations(args.limit)
    elif args.command == 'search':
        await search_knowledge_graph(args.query, args.limit)
    elif args.command == 'route':
        await find_travel_route(args.from_dest, args.to_dest, args.max_stops)
    elif args.command == 'recommend':
        await get_travel_recommendations(args.interests, args.countries, args.budget)
    elif args.command == 'sync':
        await sync_from_relational()
    elif args.command == 'memory':
        await test_memory_mcp()
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation canceled by user")
        sys.exit(1)