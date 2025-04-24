import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Body
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from google.api_core import exceptions as google_exceptions

from app.api.v1.schemas.request import ResearchRequest
from app.core.llm import generate_dynamic_schema, SchemaGenerationError
from app.core.dynamic_models import create_dynamic_model
from app.core.scraper import run_search_graph

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=Any)
async def perform_research(
    request: ResearchRequest = Body(...)
):
    """
    Performs research based on a user query.

    This endpoint takes a research request, dynamically generates a schema
    using an LLM, creates a Pydantic model from the schema, and then
    executes a web search and data extraction process using ScrapeGraphAI
    based on the generated schema.

    Args:
        request (ResearchRequest): The research request containing the query.

    Returns:
        Any: The result of the research, typically a dictionary
             structured according to the dynamically generated schema.

    Raises:
        HTTPException: If an error occurs during schema generation,
                       model creation, scraping, or due to API issues.
    """
    query = request.query
    logger.info(f"Received research request for query: '{query}'")

    try:
        logger.info("Generating dynamic schema via Langchain Gemini...")
        schema_definition = await run_in_threadpool(generate_dynamic_schema, query=query)
        logger.info(f"Using schema definition: {schema_definition.get('model_name', 'N/A')}")

        logger.info("Creating dynamic Pydantic model...")
        DynamicModel = create_dynamic_model(schema_definition)

        logger.info("Executing SearchGraph with Gemini...")
        result = await run_in_threadpool(run_search_graph, query=query, dynamic_schema_model=DynamicModel)
        logger.info("Research task completed successfully.")

        return result

    except SchemaGenerationError as sge:
         logger.error(f"Schema generation failed: {sge}")
         raise HTTPException(status_code=500, detail=f"Schema generation failed: {sge}")
    except ValidationError as ve:
        logger.error(f"Pydantic validation error during dynamic model creation or processing: {ve}")
        raise HTTPException(status_code=400, detail=f"Schema validation or processing error: {ve}")
    except ValueError as ve:
        logger.error(f"Configuration or schema processing error: {ve}")
        raise HTTPException(status_code=400, detail=f"Input or Schema processing error: {ve}")
    except google_exceptions.PermissionDenied as e:
         logger.error(f"Gemini API permission denied. Check API key and permissions: {e}")
         raise HTTPException(status_code=503, detail=f"Gemini API permission denied: {e}")
    except google_exceptions.ResourceExhausted as e:
         logger.error(f"Gemini API quota exceeded: {e}")
         raise HTTPException(status_code=429, detail=f"Gemini API quota exceeded: {e}")
    except google_exceptions.InvalidArgument as e:
         logger.error(f"Invalid argument passed to Gemini API (check model name or parameters): {e}")
         raise HTTPException(status_code=400, detail=f"Invalid argument for Gemini API: {e}")
    except ConnectionError as ce:
         logger.error(f"API connection/permission error: {ce}")
         raise HTTPException(status_code=503, detail=f"Could not connect to external API: {ce}")
    except RuntimeError as rte:
         logger.error(f"Runtime error during scraping: {rte}")
         raise HTTPException(status_code=500, detail=f"Internal server error during scraping task: {rte}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during the research process: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: An unexpected error occurred.")
