import logging
from typing import Type, Dict, Any, Union, List
from pydantic import BaseModel
from app.scrapegraph.graphs import SearchGraph
from app.scrapegraph.utils import prettify_exec_info
from app.core.config import settings
logger = logging.getLogger(__name__)
def run_search_graph(
    query: str,
    dynamic_schema_model: Type[BaseModel],
    merge_results: bool = True
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    logger.info(f"Initializing internal SearchGraph for query: '{query}' with schema: {dynamic_schema_model.__name__}")
    graph_config = {
        "llm": {
            "provider": "google_genai",
            "model": settings.SCRAPEGRAPH_EXTRACTION_MODEL,
            "api_key": settings.GEMINI_API_KEY,
            "temperature": 0.1,
        },
        "scraper": {
            "headless": settings.SCRAPER_HEADLESS,
        },
        "verbose": True,
        "max_results": settings.SCRAPER_MAX_RESULTS,
        "merge_results": merge_results,
        "timeout": 480,
        "batchsize": settings.SCRAPEGRAPH_BATCHSIZE,
        "loader_kwargs": {}
    }
    try:
        search_graph = SearchGraph(
            prompt=query,
            config=graph_config,
            schema=dynamic_schema_model
        )
        logger.info(f"Running internal SearchGraph with Gemini model: {settings.SCRAPEGRAPH_EXTRACTION_MODEL}...")
        result = search_graph.run()
        logger.info("Internal SearchGraph execution finished.")
        logger.info("--- Internal Graph Execution Information ---")
        try:
            graph_exec_info = search_graph.get_execution_info()
            logger.info(prettify_exec_info(graph_exec_info))
        except Exception as e:
            logger.warning(f"Could not retrieve execution info: {e}")
        return result
    except ValueError as ve:
         logger.error(f"ValueError during internal SearchGraph execution: {ve}")
         raise ve
    except RuntimeError as rte:
         logger.error(f"RuntimeError during internal SearchGraph execution: {rte}")
         raise rte
    except ImportError as ie:
         logger.exception(f"ImportError during internal SearchGraph init/run. Ensure dependencies are installed. Error: {ie}")
         raise RuntimeError(f"Internal scraping failed due to potentially missing dependency: {ie}") from ie
    except Exception as e:
        logger.exception(f"An unexpected error occurred during internal SearchGraph execution: {e}")
        raise e
