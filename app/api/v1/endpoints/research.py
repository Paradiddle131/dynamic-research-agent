import logging
from typing import Any, List, Dict, Union
from fastapi import APIRouter, HTTPException, Body, Query
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from google.api_core import exceptions as google_exceptions
from app.api.v1.schemas.request import ResearchRequest
from app.core.llm import generate_dynamic_schema, SchemaGenerationError
from app.core.dynamic_models import create_dynamic_model
from app.core.scraper import run_search_graph
logger = logging.getLogger(__name__)
router = APIRouter()
ResearchResponse = Union[Dict[str, Any], List[Dict[str, Any]]]
@router.post("/", response_model=ResearchResponse)
async def perform_research(
    request: ResearchRequest = Body(...),
    merge_results: bool = Query(True, description="Merge results from different sources into a single response")
):
    query = request.query
    logger.info(f"Received research request for query: '{query}' (Merge Results: {merge_results})")
    try:
        logger.info("Generating dynamic schema.")
        schema_definition = generate_dynamic_schema(query=query)
        logger.info(f"Using schema definition: {schema_definition.get('model_name', 'N/A')}")
        logger.info("Creating dynamic Pydantic model.")
        DynamicModel = create_dynamic_model(schema_definition)
        logger.info("Executing internal SearchGraph with Gemini...")
        result = await run_in_threadpool(
             run_search_graph,
             query=query,
             dynamic_schema_model=DynamicModel,
             merge_results=merge_results
        )
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
        if "not found" in str(ve) and "Gemini model" in str(ve):
             raise HTTPException(status_code=400, detail=f"Configuration error: {ve}")
        else:
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
         if "Graph execution failed at node" in str(rte):
              raise HTTPException(status_code=500, detail=f"Internal scraping error: {rte}")
         else:
              raise HTTPException(status_code=500, detail=f"Internal server error during scraping task: {rte}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during the research process: {e}")
        raise HTTPException(status_code=500, detail="Internal server error: An unexpected error occurred.")
