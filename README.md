# Dynamic Research Agent

A FastAPI-powered research assistant that dynamically generates and populates structured data models based on natural language queries.

## Description

The Dynamic Research Agent is a sophisticated web service that leverages Google's Gemini AI models to:

1. Analyze natural language research queries
2. Dynamically generate appropriate data schemas for the research topic
3. Search the web for relevant information
4. Extract and structure the data according to the generated schema
5. Return comprehensive, well-organized research results

This project combines FastAPI for the web service layer with ScrapeGraphAI for web search and data extraction, and Google's Gemini models for intelligent schema generation and content extraction.

## Features

- **Natural Language Query Processing**: Submit research queries in plain English
- **Dynamic Schema Generation**: Automatically creates appropriate data models based on query content
- **Intelligent Web Scraping**: Uses ScrapeGraphAI to find and process relevant web content
- **Structured Response Data**: Returns research results in consistent, well-organized formats
- **Fallback Mechanisms**: Ensures reliability with sensible defaults when needed

## Installation

### Prerequisites

- Python 3.8+
- Google Gemini API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dynamic-research-agent.git
   cd dynamic-research-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file and add your Gemini API key:
   ```
   GEMINI_API_KEY="your-gemini-api-key"
   ```

## Configuration

The application can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| PROJECT_NAME | Name of the project | "Dynamic Research Agent" |
| API_V1_STR | API version prefix | "/api/v1" |
| SERVER_HOST | Host to bind the server | "0.0.0.0" |
| SERVER_PORT | Port to bind the server | 8765 |
| GEMINI_API_KEY | Google Gemini API key | Required |
| SCHEMA_GENERATION_MODEL | Gemini model for schema generation | "gemini-2.5-flash" |
| SCRAPEGRAPH_EXTRACTION_MODEL | Gemini model for data extraction | "gemini-2.5-flash" |
| SCRAPER_MAX_RESULTS | Maximum number of search results to process | 5 |
| SCRAPER_HEADLESS | Run browser in headless mode | True |

## Usage

### Starting the Server

Run the application with:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8765`.

### API Endpoints

#### Root Endpoint

- **GET** `/`: Welcome message and basic service info

#### Research Endpoint

- **POST** `/api/v1/research/`: Submit a research query

Example request:

```bash
curl -X POST "http://localhost:8765/api/v1/research/" \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the latest advancements in quantum computing?"}'
```

Example response:

```json
{
  "query": "What are the latest advancements in quantum computing?",
  "summary": "Recent advancements in quantum computing include significant progress in error correction, the development of more stable qubits, and breakthroughs in quantum algorithms...",
  "key_points": [
    "IBM unveiled a 1,121-qubit processor named 'Condor'",
    "Google achieved quantum error correction milestone",
    "PsiQuantum is developing photonic quantum computers",
    "Quantum advantage demonstrated in specific computational tasks"
  ],
  "entities": [
    "IBM", 
    "Google", 
    "PsiQuantum", 
    "Quantum Error Correction", 
    "Superconducting qubits"
  ],
  "source_urls": [
    "https://www.example.com/quantum-computing-news",
    "https://research.institution.edu/quantum-papers"
  ]
}
```

### Interactive API Documentation

FastAPI provides interactive documentation:

- Swagger UI: `http://localhost:8765/docs`
- ReDoc: `http://localhost:8765/redoc`

## Architecture

The project is structured as follows:

```
dynamic-research-agent/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── research.py  # API endpoints
│   │       └── schemas/
│   │           └── request.py   # API request schemas
│   ├── core/
│   │   ├── config.py            # Configuration settings
│   │   ├── dynamic_models.py    # Dynamic Pydantic model generation
│   │   ├── llm.py               # Gemini LLM integration
│   │   └── scraper.py           # ScrapeGraphAI integration
│   ├── utils/
│   │   └── logging_config.py    # Logging configuration
│   └── main.py                  # Application entry point
├── .env.example                 # Example environment variables
├── pyproject.toml               # Project metadata
└── requirements.txt             # Dependencies
```

## Error Handling

The API implements comprehensive error handling:

- 400: Bad Request (Invalid input or schema processing issues)
- 429: Too Many Requests (API quota exceeded)
- 500: Internal Server Error (Unexpected errors)
- 503: Service Unavailable (API connection issues)

## Dependencies

- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and settings management
- **HTTPX**: HTTP client
- **ScrapeGraphAI**: Web scraping and data extraction
- **Google Gemini**: LLM for schema generation and content extraction