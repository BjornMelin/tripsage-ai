#!/usr/bin/env python3
"""
Unified MCP Server Launcher

This script provides a centralized way to launch and manage MCP servers
for TripSage. It automatically detects server runtime (Python/Node) and
spawns servers appropriately using STDIO transport.
"""

import asyncio
import json
import logging
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage.config.mcp_settings import MCPSettings


class ServerRuntime(str, Enum):
    PYTHON = "python"
    NODE = "node"
    BINARY = "binary"


class MCPServerConfig(BaseModel):
    """Configuration for an individual MCP server"""

    name: str
    runtime: ServerRuntime
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    working_dir: Optional[Path] = None
    auto_start: bool = False
    health_check_endpoint: Optional[str] = None


class MCPLauncher:
    """Manages launching and lifecycle of MCP servers"""

    def __init__(self, settings: Optional[MCPSettings] = None):
        self.settings = settings or MCPSettings()
        self.servers: Dict[str, subprocess.Popen] = {}
        self.configs = self._load_server_configs()
        self.logger = logging.getLogger(__name__)

    def _load_server_configs(self) -> Dict[str, MCPServerConfig]:
        """Load server configurations from settings"""
        configs = {}

        # Map existing shell scripts to unified launcher configs
        script_mappings = {
            "supabase": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "supabase-mcp"],
                "env": {
                    "SUPABASE_URL": self.settings.supabase.server_url,
                    "SUPABASE_KEY": self.settings.supabase.supabase_key,
                },
            },
            "neo4j_memory": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "@neo4j-contrib/mcp-neo4j"],
                "env": {
                    "NEO4J_URI": self.settings.neo4j_memory.server_url,
                    "NEO4J_USERNAME": self.settings.neo4j_memory.neo4j_username,
                    "NEO4J_PASSWORD": self.settings.neo4j_memory.neo4j_password,
                },
            },
            "duffel_flights": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "duffel-mcp"],
                "env": {"DUFFEL_API_KEY": self.settings.duffel_flights.api_key},
            },
            "airbnb": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "airbnb-mcp"],
                "env": {"AIRBNB_API_KEY": self.settings.airbnb.api_key},
            },
            "playwright": {
                "runtime": ServerRuntime.NODE,
                "command": "node",
                "args": [
                    str(
                        Path.home()
                        / ".nvm"
                        / "versions"
                        / "node"
                        / "v20.9.0"
                        / "bin"
                        / "playwright-mcp"
                    )
                ],
                "env": {"BROWSER_TYPE": "chromium"},
            },
            "crawl4ai": {
                "runtime": ServerRuntime.PYTHON,
                "command": "python",
                "args": ["-m", "crawl4ai.mcp_server"],
                "env": {
                    "CRAWL4AI_API_KEY": (
                        self.settings.crawl4ai.api_key
                        if hasattr(self.settings, "crawl4ai")
                        else ""
                    )
                },
            },
            "firecrawl": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "@mendableai/firecrawl-mcp-server"],
                "env": {"FIRECRAWL_API_KEY": self.settings.firecrawl.api_key},
            },
            "google_maps": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "google-maps-mcp"],
                "env": {"GOOGLE_MAPS_API_KEY": self.settings.google_maps.api_key},
            },
            "time": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "@anthropics/mcp-time"],
                "env": {},
            },
            "weather": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "weather-mcp-server"],
                "env": {"OPENWEATHERMAP_API_KEY": self.settings.weather.api_key},
            },
            "google_calendar": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "google-calendar-mcp"],
                "env": {
                    "GOOGLE_CLIENT_ID": self.settings.google_calendar.client_id,
                    "GOOGLE_CLIENT_SECRET": self.settings.google_calendar.client_secret,
                },
            },
        }

        for name, config_data in script_mappings.items():
            configs[name] = MCPServerConfig(name=name, **config_data)

        return configs

    async def start_server(self, server_name: str) -> bool:
        """Start a specific MCP server"""
        if server_name in self.servers:
            self.logger.warning(f"Server {server_name} is already running")
            return True

        if server_name not in self.configs:
            self.logger.error(f"Unknown server: {server_name}")
            return False

        config = self.configs[server_name]
        self.logger.info(f"Starting {server_name} server...")

        try:
            # Prepare environment
            env = {**config.env}

            # Launch server process
            process = subprocess.Popen(
                [config.command] + config.args,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=config.working_dir,
            )

            self.servers[server_name] = process
            self.logger.info(f"Started {server_name} server (PID: {process.pid})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start {server_name}: {e}")
            return False

    async def stop_server(self, server_name: str) -> bool:
        """Stop a specific MCP server"""
        if server_name not in self.servers:
            self.logger.warning(f"Server {server_name} is not running")
            return True

        process = self.servers[server_name]
        self.logger.info(f"Stopping {server_name} server...")

        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Force killing {server_name} server")
            process.kill()

        del self.servers[server_name]
        self.logger.info(f"Stopped {server_name} server")
        return True

    async def start_all(self, auto_only: bool = True) -> Dict[str, bool]:
        """Start all configured servers"""
        results = {}

        for name, config in self.configs.items():
            if auto_only and not config.auto_start:
                continue

            results[name] = await self.start_server(name)

        return results

    async def stop_all(self) -> Dict[str, bool]:
        """Stop all running servers"""
        results = {}

        for name in list(self.servers.keys()):
            results[name] = await self.stop_server(name)

        return results

    def list_servers(self) -> Dict[str, str]:
        """List all available servers and their status"""
        status = {}

        for name in self.configs:
            status[name] = "running" if name in self.servers else "stopped"

        return status

    async def health_check(self, server_name: str) -> bool:
        """Check if a server is responsive"""
        if server_name not in self.servers:
            return False

        process = self.servers[server_name]
        return process.poll() is None  # None means still running


async def main():
    """CLI interface for MCP launcher"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server Launcher")
    parser.add_argument(
        "command",
        choices=["start", "stop", "list", "start-all", "stop-all"],
        help="Command to execute",
    )
    parser.add_argument(
        "server", nargs="?", help="Server name (for start/stop commands)"
    )
    parser.add_argument(
        "--auto-only", action="store_true", help="Only start auto-start servers"
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    launcher = MCPLauncher()

    if args.command == "start":
        if not args.server:
            print("Server name required for start command")
            sys.exit(1)
        success = await launcher.start_server(args.server)
        sys.exit(0 if success else 1)

    elif args.command == "stop":
        if not args.server:
            print("Server name required for stop command")
            sys.exit(1)
        success = await launcher.stop_server(args.server)
        sys.exit(0 if success else 1)

    elif args.command == "list":
        servers = launcher.list_servers()
        print(json.dumps(servers, indent=2))

    elif args.command == "start-all":
        results = await launcher.start_all(auto_only=args.auto_only)
        print(json.dumps(results, indent=2))
        sys.exit(0 if all(results.values()) else 1)

    elif args.command == "stop-all":
        results = await launcher.stop_all()
        print(json.dumps(results, indent=2))
        sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    asyncio.run(main())
