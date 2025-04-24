import logging
from typing import Type, Dict, Any
from pydantic import BaseModel
from scrapegraphai.graphs import SearchGraph
from google.api_core import exceptions as google_exceptions

from app.core.config import settings

logger = logging.getLogger(__name__)

def run_search_graph(query: str, dynamic_schema_model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Initializes and runs the ScrapeGraphAI SearchGraph using Gemini configuration.
    ScrapeGraphAI internally handles the LLM interaction based on the config.
    """
    logger.info(f"Initializing SearchGraph for query: '{query}' with schema: {dynamic_schema_model.__name__}")

    llm_provider = "google_genai"
    graph_config = {
        "llm": {
            "model": f"{llm_provider}/{settings.SCRAPEGRAPH_EXTRACTION_MODEL}",
            "api_key": settings.GEMINI_API_KEY,
            "temperature": 0.1,
            "max_tokens": settings.SCRAPEGRAPH_MAX_TOKENS,
        },
        "scraper": {
            "scraper_instance": "PlaywrightScraper",
            "headless": settings.SCRAPER_HEADLESS,
        },
        "verbose": True,
        "max_results": settings.SCRAPER_MAX_RESULTS,
    }

    try:
        search_graph = SearchGraph(
            prompt=query,
            config=graph_config,
            schema=dynamic_schema_model
        )

        logger.info(f"Running SearchGraph with Gemini model: {settings.SCRAPEGRAPH_EXTRACTION_MODEL}...")
        result = search_graph.run()
        logger.info("SearchGraph execution finished.")

        if isinstance(result, dict):
            return result
        else:
             logger.error(f"SearchGraph returned an unexpected type: {type(result)}. Expected dict.")
             return {"error": "SearchGraph returned unexpected data type", "data": str(result)}

    except ValueError as ve:
        if "Provider" in str(ve) and "is not supported" in str(ve):
             logger.error(f"Configuration error: Invalid LLM provider '{llm_provider}' specified in ScrapeGraphAI config. {ve}")
             raise ValueError(f"Internal configuration error: Invalid LLM provider '{llm_provider}'.") from ve
        else:
             logger.error(f"ValueError during SearchGraph execution: {ve}")
             raise ve
    except google_exceptions.NotFound as nfe:
        logger.error(f"Configuration error: Gemini model '{settings.SCRAPEGRAPH_EXTRACTION_MODEL}' not found or not accessible. Check model name and API permissions. Error: {nfe}")
        raise ValueError(f"Configuration error: Specified Gemini model '{settings.SCRAPEGRAPH_EXTRACTION_MODEL}' not found.") from nfe
    except RecursionError as re:
        logger.error(f"RecursionError during SearchGraph execution. This might be due to excessively low 'max_tokens' ({settings.SCRAPEGRAPH_MAX_TOKENS}) for the task, or overly complex data/schema. Error: {re}")
        raise RuntimeError(f"Processing error: Task exceeded recursion limits, potentially due to token constraints or complexity.") from re
    except ImportError as ie:
         logger.exception(f"ImportError during SearchGraph init/run. Ensure 'scrapegraphai[google]' or necessary dependencies are installed. Error: {ie}")
         raise RuntimeError(f"ScrapeGraphAI failed due to potentially missing dependency: {ie}") from ie
    except KeyError as ke:
        logger.exception(f"KeyError during SearchGraph execution, possibly related to config or response parsing: {ke}")
        raise RuntimeError(f"Configuration or parsing error in ScrapeGraphAI: {ke}") from ke
    except Exception as e:
        logger.exception(f"An unexpected error occurred during SearchGraph execution: {e}")
        raise e
