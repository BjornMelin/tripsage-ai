#!/usr/bin/env python3
"""
Unified MCP Server Launcher

This script provides a centralized way to launch and manage MCP servers
for TripSage. It automatically detects server runtime (Python/Node) and
spawns servers appropriately using STDIO transport.

Node.js Compatibility:
- Works with any Node.js installation (nvm, fnm, volta, system install)
- Uses standard npx command that comes with npm
- Automatically detects Node.js availability and version
"""

import asyncio
import json
import logging
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        try:
            self.settings = settings or MCPSettings()
        except Exception as e:
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"Failed to load MCP settings: {e}")
            self.settings = None
        self.servers: Dict[str, subprocess.Popen] = {}
        self.configs = self._load_server_configs()
        self.logger = logging.getLogger(__name__)
        self._check_dependencies()

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
                    "SUPABASE_URL": str(self.settings.supabase.url),
                    "SUPABASE_KEY": self.settings.supabase.service_key.get_secret_value(),
                },
            },
            "neo4j_memory": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "@neo4j-contrib/mcp-neo4j"],
                "env": {
                    "NEO4J_URI": f"{self.settings.neo4j_memory.scheme}://{self.settings.neo4j_memory.host}:{self.settings.neo4j_memory.port}",
                    "NEO4J_USERNAME": self.settings.neo4j_memory.username,
                    "NEO4J_PASSWORD": self.settings.neo4j_memory.password.get_secret_value(),
                },
            },
            "duffel_flights": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "duffel-mcp"],
                "env": {"DUFFEL_API_KEY": self.settings.duffel_flights.api_key.get_secret_value()},
            },
            "airbnb": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "airbnb-mcp"],
                "env": {"AIRBNB_API_KEY": self.settings.airbnb.api_key.get_secret_value()},
            },
            "playwright": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "playwright-mcp"],
                "env": {"BROWSER_TYPE": "chromium"},
            },
            "crawl4ai": {
                "runtime": ServerRuntime.PYTHON,
                "command": "python",
                "args": ["-m", "crawl4ai.mcp_server"],
                "env": {
                    "CRAWL4AI_API_KEY": (
                        self.settings.crawl4ai.api_key.get_secret_value()
                        if hasattr(self.settings, "crawl4ai") and hasattr(self.settings.crawl4ai, "api_key")
                        else ""
                    )
                },
            },
            "firecrawl": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "@mendableai/firecrawl-mcp-server"],
                "env": {"FIRECRAWL_API_KEY": self.settings.firecrawl.api_key.get_secret_value()},
            },
            "google_maps": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "google-maps-mcp"],
                "env": {"GOOGLE_MAPS_API_KEY": self.settings.google_maps.api_key.get_secret_value()},
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
                "env": {"OPENWEATHERMAP_API_KEY": self.settings.weather.api_key.get_secret_value()},
            },
            "google_calendar": {
                "runtime": ServerRuntime.NODE,
                "command": "npx",
                "args": ["-y", "google-calendar-mcp"],
                "env": {
                    "GOOGLE_CLIENT_ID": str(self.settings.google_calendar.auth_mode),
                    "GOOGLE_CLIENT_SECRET": self.settings.google_calendar.api_key.get_secret_value(),
                },
            },
        }

        for name, config_data in script_mappings.items():
            configs[name] = MCPServerConfig(name=name, **config_data)

        return configs

    def _check_dependencies(self):
        """Check if required dependencies are available"""
        # Check for Node.js and npm/npx
        node_cmd = shutil.which("node")
        npx_cmd = shutil.which("npx")
        
        if not node_cmd:
            self.logger.warning(
                "Node.js not found in PATH. Node-based MCP servers will not work."
                "\nPlease install Node.js using one of the following:"
                "\n  - Official installer: https://nodejs.org/"
                "\n  - Package manager: brew install node (macOS)"
                "\n  - nvm: https://github.com/nvm-sh/nvm"
                "\n  - fnm: https://github.com/Schniz/fnm"
            )
        elif not npx_cmd:
            self.logger.warning(
                "npx not found in PATH. This usually comes with npm."
                "\nTry running: npm install -g npm"
            )
        else:
            # Get Node.js version for info
            try:
                result = subprocess.run(
                    ["node", "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info(f"Node.js {result.stdout.strip()} detected")
            except subprocess.SubprocessError:
                pass
        
        # Check for Python (for Python-based servers)
        python_cmd = shutil.which("python") or shutil.which("python3")
        if not python_cmd:
            self.logger.warning(
                "Python not found in PATH. Python-based MCP servers will not work."
            )
        else:
            try:
                result = subprocess.run(
                    [python_cmd, "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info(f"{result.stdout.strip()} detected")
            except subprocess.SubprocessError:
                pass

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
