import asyncio
from typing import List, Optional, Type
from pydantic import BaseModel
from tqdm.asyncio import tqdm
import traceback
from langchain_core.callbacks import BaseCallbackHandler
from .base_node import BaseNode
from ..utils.logging import get_logger
DEFAULT_BATCHSIZE = 16
class GraphIteratorNode(BaseNode):
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "GraphIterator",
        schema: Optional[Type[BaseModel]] = None,
    ):
        super().__init__(node_name, "node", input, output, 2, node_config)
        self.schema = schema
        self.verbose = self.node_config.get("verbose", False)
        self.logger = get_logger(__name__)
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")
        batchsize = self.node_config.get("batchsize", DEFAULT_BATCHSIZE)
        try:
            loop = asyncio.get_event_loop()
            self.logger.debug("Running GraphIteratorNode within existing asyncio loop.")
            future = asyncio.ensure_future(self._async_execute(state, batchsize))
            state = loop.run_until_complete(future)
        except RuntimeError:
            self.logger.debug("No running asyncio loop found. Starting new one for GraphIteratorNode.")
            state = asyncio.run(self._async_execute(state, batchsize))
        except Exception as e:
             self.logger.error(f"Error during GraphIterator execution: {e}")
             state[self.output[0]] = [{"error": f"Graph iteration failed: {str(e)}"}]
        return state
    async def _async_execute(self, state: dict, batchsize: int) -> dict:
        self.logger.info(f"--- Starting parallel graph execution with batchsize {batchsize} ---")
        input_keys = self.get_input_keys(state)
        if len(input_keys) < 2:
             raise ValueError(f"GraphIteratorNode requires at least two inputs (prompt, list), found: {input_keys}")
        user_prompt = state.get(input_keys[0])
        input_list = state.get(input_keys[1])
        if not user_prompt:
            raise ValueError("User prompt is missing from state.")
        if not input_list or not isinstance(input_list, list):
            self.logger.warning(f"Input list '{input_keys[1]}' is missing or not a list.")
            state[self.output[0]] = []
            return state
        graph_instance_class = self.node_config.get("graph_instance")
        scraper_config = self.node_config.get("scraper_config")
        if not graph_instance_class:
            raise ValueError("graph_instance class is required in node_config.")
        if not scraper_config:
            raise ValueError("scraper_config is required in node_config.")
        semaphore = asyncio.Semaphore(batchsize)
        tasks = []
        for i, item in enumerate(input_list):
            instance_config = scraper_config.copy()
            instance_config["instance_id"] = i
            instance_config["graph_depth"] = instance_config.get("graph_depth", 0) + 1
            graph = graph_instance_class(
                prompt=user_prompt,
                source=item,
                config=instance_config,
                schema=self.schema
            )
            tasks.append(self._run_graph_instance(graph, item, semaphore))
        results = await tqdm.gather(
            *tasks, desc="Processing graph instances", disable=not self.verbose
        )
        valid_results = [res for res in results if res is not None]
        state.update({self.output[0]: valid_results})
        self.logger.info(f"--- Finished parallel graph execution. Got {len(valid_results)} results. ---")
        return state
    async def _run_graph_instance(self, graph_instance, item_source, semaphore):
        async with semaphore:
            self.logger.debug(f"Running graph instance for: {item_source}")
            try:
                result = await asyncio.to_thread(graph_instance.run)
                self.logger.debug(f"Graph instance for {item_source} completed.")
                return result
            except Exception as e:
                self.logger.error(f"Error running graph instance for {item_source}: {e}")
                self.logger.debug(traceback.format_exc())
                return {"error": f"Failed to process source {item_source}: {str(e)}"}
