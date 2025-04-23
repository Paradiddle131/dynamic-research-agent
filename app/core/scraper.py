import logging
from typing import Type, Dict, Any
from pydantic import BaseModel
from scrapegraphai.graphs import SearchGraph

from app.core.config import settings

logger = logging.getLogger(__name__)

def run_search_graph(query: str, dynamic_schema_model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Initializes and runs the ScrapeGraphAI SearchGraph using Gemini for extraction.
    """
    logger.info(f"Initializing SearchGraph for query: '{query}' with model: {dynamic_schema_model.__name__}")

    graph_config = {
        "llm": {
            "api_key": settings.GEMINI_API_KEY,
            "model": settings.SCRAPEGRAPH_EXTRACTION_MODEL,
            "temperature": 0.1,
            "max_tokens": 8192,
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
             logger.error(f"SearchGraph returned an unexpected type: {type(result)}. Expected dict. Data: {str(result)[:500]}...")
             return {"error": "SearchGraph returned unexpected data type", "data": str(result)}

    except ImportError as e:
         logger.exception(f"ImportError during SearchGraph init/run, likely missing 'google-genai'. Please install it. Error: {e}")
         raise RuntimeError(f"ScrapeGraphAI failed due to missing dependency 'google-genai': {e}") from e
    except Exception as e:
        logger.exception(f"An error occurred during SearchGraph execution: {e}")
        raise e
