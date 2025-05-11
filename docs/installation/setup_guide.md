# TripSage Installation and Usage Guide

This guide explains how to set up, install, and run the TripSage project and its components using the `uv` Python package manager.

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (installation instructions below)
- Git (for cloning the repository)

## Installing UV

If you don't have `uv` installed, you can install it using:

```bash
# On macOS or Linux
curl -sSf https://astral.sh/uv/install.sh | sh

# On Windows with PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

## Project Structure

TripSage uses a hybrid package management approach:

- Root level `pyproject.toml` for project-wide settings and shared dependencies
- Individual `requirements.txt` files in each subproject for component-specific dependencies

The main subprojects are:

- `src/api/` - Backend API server
- `src/agents/` - AI agents implementation
- `src/mcp/` - MCP server implementations (browser, time, weather, etc.)
- `src/db/` - Database access layer

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd tripsage-ai
```

### 2. Create and Activate Virtual Environment

UV's built-in virtual environment management:

```bash
# Create a virtual environment in the project directory
uv venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

#### Option 1: Complete Installation (Recommended)

The simplest approach is to use the root `requirements.txt`, which includes all dependencies:

```bash
# From the project root with virtual environment activated
uv pip install -r requirements.txt
```

This installs most common dependencies, but may not include all module-specific dependencies.

#### Option 2: Comprehensive Installation

For a complete installation of all dependencies including subprojects:

```bash
# Install main project dependencies
uv pip install -r requirements.txt

# Install subproject dependencies
uv pip install -r src/api/requirements.txt
uv pip install -r src/agents/requirements.txt
uv pip install -r src/mcp/browser/requirements.txt

# Install any other module-specific dependencies as needed
# For example:
# uv pip install -r path/to/other/requirements.txt
```

#### Option 3: Modular Installation

If you prefer a more granular approach:

1. Install project-wide shared dependencies:

   ```bash
   uv pip install -e .
   ```

2. Install component-specific dependencies based on which parts you're working with:

```bash
# For API component
uv pip install -r src/api/requirements.txt

# For Agents component
uv pip install -r src/agents/requirements.txt

# For Browser MCP
uv pip install -r src/mcp/browser/requirements.txt
```

#### Option 4: Development Setup

If you're focusing on development:

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Then add required component dependencies
uv pip install -r src/api/requirements.txt
uv pip install -r src/agents/requirements.txt
uv pip install -r src/mcp/browser/requirements.txt
```

## Running the Project

### Setting Up Environment Variables

Create a `.env` file in the project root:

```bash
touch .env
```

Add the necessary environment variables to the `.env` file:

```plaintext
# API Keys
OPENAI_API_KEY=your_openai_api_key

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# API Configuration
API_SECRET_KEY=your_api_secret_key
```

### Running the API Server

```bash
cd src/api
uvicorn main:app --reload
```

The API will be available at <http://localhost:8000>

### Running Agent Components

```bash
cd src/agents
python travel_agent.py
```

## Development Workflow

### Code Formatting and Linting

Format and lint your code using Ruff:

```bash
# Format code
ruff format .

# Lint code
ruff check .
```

### Adding New Dependencies

When adding new dependencies to a specific component:

```bash
# For API component
cd src/api
uv pip install new_package
uv pip freeze > requirements.txt  # Update requirements.txt

# For Agents component
cd src/agents
uv pip install new_package
uv pip freeze > requirements.txt  # Update requirements.txt
```

For project-wide dependencies, update the `pyproject.toml` file manually and then run:

```bash
uv pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file.py
```

## Troubleshooting

### Common Issues

#### Package Not Found

If you encounter "package not found" errors, ensure you've installed the dependencies for the specific component you're working with:

```bash
# Verify which component's dependencies you need
uv pip install -r src/component_name/requirements.txt
```

Different modules have their own requirements.txt files:

- Main project: `/requirements.txt`
- API: `/src/api/requirements.txt`
- Agents: `/src/agents/requirements.txt`
- Browser MCP: `/src/mcp/browser/requirements.txt`
- (Other MCP components may have their own requirements.txt files)

#### Environment Variable Issues

If you encounter errors related to missing environment variables, make sure your `.env` file is properly set up and you're running your code from the correct directory.

#### Virtual Environment Issues

If your virtual environment isn't working correctly, you can recreate it:

```bash
# Remove existing virtual environment
rm -rf .venv

# Create a new virtual environment
uv venv

# Activate and reinstall dependencies
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e .
```

## Project Verification

To verify your installation works correctly:

```bash
# Run the connection verification script
cd scripts
node verify_connection.js
```

## Best Practices

1. **Always activate the virtual environment** before working on the project
2. **Keep requirements.txt files updated** when adding new dependencies
3. **Run formatting and linting checks** before committing code
4. **Never commit** the `.env` file or API keys
5. **Follow the Python standards** defined in CLAUDE.md
