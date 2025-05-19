# Node.js Compatibility Guide for MCP Servers

## Overview

TripSage's MCP servers are designed to work with any Node.js installation method. The system automatically detects and uses the Node.js installation available in your PATH.

## Supported Node.js Installation Methods

The following Node.js installation methods are fully supported:

1. **nvm (Node Version Manager)**
   - Popular version manager for Node.js
   - <https://github.com/nvm-sh/nvm>
   - Automatically sets up PATH for Node.js and npm/npx

2. **fnm (Fast Node Manager)**
   - Rust-based alternative to nvm
   - <https://github.com/Schniz/fnm>
   - Works seamlessly with our MCP servers

3. **volta**
   - JavaScript toolchain manager
   - <https://volta.sh/>
   - Provides automatic project-based Node.js versions

4. **asdf**
   - Multi-language version manager
   - <https://asdf-vm.com/>
   - Supports Node.js through plugins

5. **System Package Managers**
   - Ubuntu/Debian: `apt install nodejs`
   - macOS: `brew install node`
   - Windows: Chocolatey, Scoop

6. **Official Node.js Installer**
   - Direct download from <https://nodejs.org/>
   - Includes npm and npx by default

## How It Works

The MCP launcher uses `npx` command, which is included with npm (Node Package Manager). The `npx` command works identically across all Node.js installation methods because:

1. All Node version managers add their Node.js installation to the system PATH
2. `npx` is a standard tool included with npm since version 5.2
3. The launcher uses `npx -y <package>` to automatically download and run packages

## Server Types

### Node.js-based MCP Servers

These servers require Node.js to be installed:

- Supabase MCP
- Neo4j Memory MCP
- Duffel Flights MCP
- Airbnb MCP
- Google Maps MCP
- Time MCP
- Weather MCP
- Google Calendar MCP
- Firecrawl MCP

### Python-based MCP Servers

These servers don't require Node.js:

- Crawl4AI MCP
- Custom Python MCP servers

## Dependency Checking

The MCP launcher automatically checks for Node.js availability on startup. If Node.js is not found, it will:

1. Log a warning with installation instructions
2. Provide links to various installation methods
3. Continue running (Python-based servers will still work)

Example output when Node.js is missing:

```plaintext
Node.js not found in PATH. Node-based MCP servers will not work.
Please install Node.js using one of the following:
  - Official installer: https://nodejs.org/
  - Package manager: brew install node (macOS)
  - nvm: https://github.com/nvm-sh/nvm
  - fnm: https://github.com/Schniz/fnm
```

## Version Requirements

- **Minimum Node.js version**: 16.x
- **Recommended Node.js version**: 18.x or 20.x (LTS)
- **npm/npx version**: 5.2+ (included with Node.js)

## Troubleshooting

### Node.js not found

If you see "Node.js not found in PATH":

1. Verify Node.js is installed: `node --version`
2. Check if npm/npx is available: `npx --version`
3. Ensure your Node version manager has been properly initialized in your shell

### npx not found

If Node.js is installed but npx is missing:

1. Update npm: `npm install -g npm@latest`
2. Install npx separately: `npm install -g npx`

### Version Manager Issues

For nvm users:

```bash
# Add to ~/.bashrc, ~/.zshrc, etc.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

For fnm users:

```bash
# Add to shell configuration
eval "$(fnm env)"
```

## Best Practices

1. **Use an LTS Node.js version** for stability
2. **Keep npm updated** to ensure npx compatibility
3. **Set up your version manager** in your shell configuration
4. **Test the installation** by running: `npx -v`

## Example Usage

Once Node.js is properly installed (through any method), MCP servers can be launched:

```bash
# Using the unified launcher
python scripts/mcp/mcp_launcher.py start supabase

# Individual scripts also work
./scripts/startup/start_time_mcp.sh

# Direct npx usage (what the launcher does internally)
npx -y supabase-mcp
```

All these methods will work regardless of how you installed Node.js.
