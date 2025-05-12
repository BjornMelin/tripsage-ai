# TripSage: AI-Powered Travel Planning System

✈️ AI-powered travel planning system with budget optimization, multi-source search, and personalized recommendations built on Supabase, OpenAI Agents, and Streamlit.

## Overview

TripSage is an intelligent travel planning platform that seamlessly integrates flight, accommodation, and location data from multiple sources while storing search results in a dual-storage architecture (Supabase + knowledge graph memory). The system optimizes travel plans against budget constraints by comparing options across services, tracking price changes, and building a persistent knowledge base of travel relationships and patterns across sessions.

## Features

- **Smart Budget Optimization**: Allocate your travel budget efficiently across flights, accommodations, activities, and transportation
- **Multi-Source Search**: Find and compare travel options from multiple providers in one place
- **Personalized Recommendations**: Get customized suggestions based on your preferences and past trips
- **Price Tracking**: Monitor price changes for flights and accommodations
- **Comprehensive Itineraries**: Create detailed day-by-day trip plans with all bookings in one place
- **Knowledge Building**: Build a travel knowledge graph that improves recommendations over time

## Tech Stack

- **Backend**: Python, FastAPI
- **Database**: PostgreSQL (via Supabase)
- **AI/ML**: OpenAI Agents SDK, Knowledge Graph
- **Frontend**: Streamlit
- **Integrations**: Flight APIs, Hotel APIs, Activity APIs

## Architecture

TripSage uses a dual-storage architecture:

1. **Relational Database (Supabase)**: Stores structured trip data, options, and booking information
2. **Knowledge Graph**: Maintains relationships between travel entities and patterns

### Database Schema

The database consists of the following main tables:

- `trips`: Core trip information (dates, destination, budget)
- `flights`: Flight options and bookings
- `accommodations`: Hotel and lodging options
- `transportation`: Local transit options
- `itinerary_items`: Daily activities and plans
- Additional supporting tables for search parameters, price history, comparisons, and more

For detailed schema information, see the [Database Setup Documentation](./docs/database_setup.md).

## Getting Started

### Prerequisites

- Node.js (v16+)
- Python (v3.9+)
- Supabase account
- OpenAI API key

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/BjornMelin/tripsage-ai.git
   cd tripsage-ai
   ```

2. Set up environment variables:

   ```bash
   # API server environment
   cp src/api/.env.example src/api/.env
   # Agent environment
   cp src/agents/.env.example src/agents/.env
   # Edit each .env file with your API keys and configuration
   ```

3. Configure MCP Servers:

   TripSage uses several MCP (Model Context Protocol) servers to enhance its functionality. The following environment variables are required:

   ```bash
   # OpenAI API Key
   OPENAI_API_KEY=your_openai_api_key_here

   # Flights MCP Server (ravinahp/flights-mcp)
   DUFFEL_API_KEY=your_duffel_api_key_here  # Get from duffel.com
   DUFFEL_API_VERSION=2023-06-02            # Use this specific version

   # Google Maps MCP Server
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

   # Other MCP Servers
   # Add other MCP server environment variables as needed
   ```

   Note that the `ravinahp/flights-mcp` server is read-only and can only search for flights, not book them. For Duffel API key setup, you can start with a test key (`duffel_test`) to try the functionality with simulated data.

4. Install dependencies:

   ```bash
   # API server dependencies
   pip install -r src/api/requirements.txt

   # Agent dependencies
   pip install -r src/agents/requirements.txt
   ```

5. Set up the database:

   ```bash
   # See docs/database_setup.md for detailed instructions
   # Verify connection to your Supabase project
   node scripts/verify_connection.js
   ```

6. Start the API server:

   ```bash
   cd src/api
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. Try the agent demo:

   ```bash
   cd src/agents
   python demo.py
   ```

### Database Setup

TripSage requires a Supabase project for data storage. The database has already been set up with the following details:

- **Project Name:** tripsage_planner
- **Region:** us-east-2
- **Database:** PostgreSQL 15.8

To connect to the database:

1. Copy `.env.example` to `.env` and update with your Supabase keys
2. Verify the database connection using the verification script:

   ```bash
   node scripts/verify_connection.js
   ```

For detailed database setup instructions, see the [Database Setup Documentation](./docs/database_setup.md).

## Development Workflow

1. Create a feature branch from `dev`:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit using conventional commits:

   ```bash
   git commit -m "feat: add new feature"
   ```

3. Push your branch and create a pull request to the `dev` branch

4. After review and approval, merge to `dev` and eventually to `main`

## Roadmap

- [x] Initial database setup
- [x] Backend API implementation (FastAPI)
- [x] Initial OpenAI Agents integration
- [ ] Flight and hotel API integrations
- [ ] Streamlit frontend
- [ ] Knowledge graph integration
- [ ] User authentication and profiles
- [ ] Mobile-friendly interface

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- OpenAI for the Agents SDK
- Supabase for the database infrastructure
- All contributors and beta testers
