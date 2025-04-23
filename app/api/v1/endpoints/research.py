import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Body
from starlette.concurrency import run_in_threadpool

from app.api.v1.schemas.request import ResearchRequest
from app.core.llm import generate_dynamic_schema
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
        logger.info("Generating dynamic schema via Gemini in threadpool...")
        schema_definition = await run_in_threadpool(generate_dynamic_schema, query=query)
        logger.info(f"Using schema definition: {schema_definition.get('model_name', 'N/A')}")

        logger.info("Creating dynamic Pydantic model...")
        DynamicModel = create_dynamic_model(schema_definition)

        logger.info("Executing SearchGraph with Gemini in threadpool...")
        result = await run_in_threadpool(run_search_graph, query=query, dynamic_schema_model=DynamicModel)
        logger.info("Research task completed successfully.")

        return result

    except ValueError as ve:
        logger.error(f"Configuration or schema processing error: {ve}")
        raise HTTPException(status_code=400, detail=f"Input or Schema processing error: {ve}")
    except ConnectionError as ce:
         logger.error(f"Gemini API connection/permission error: {ce}")
         raise HTTPException(status_code=503, detail=f"Could not connect to Gemini API: {ce}")
    except ConnectionAbortedError as cae:
         logger.error(f"Gemini API quota error: {cae}")
         raise HTTPException(status_code=429, detail=f"Gemini API quota exceeded: {cae}")
    except RuntimeError as rte:
         logger.error(f"Runtime error during scraping: {rte}")
         raise HTTPException(status_code=500, detail=f"Internal server error during scraping task: {rte}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during the research process: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: An unexpected error occurred.")
