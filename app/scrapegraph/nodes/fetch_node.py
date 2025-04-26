from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.callbacks import BaseCallbackHandler
from .base_node import BaseNode
from ..docloaders import ChromiumLoader
class FetchNode(BaseNode):
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "Fetch",
    ):
        super().__init__(node_name, "node", input, output, 1, node_config)
        self.headless = self.node_config.get("headless", True)
        self.verbose = self.node_config.get("verbose", False)
        self.loader_kwargs = self.node_config.get("loader_kwargs", {})
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")
        input_keys = self.get_input_keys(state)
        source = state[input_keys[0]]
        if not source or not isinstance(source, str):
             raise ValueError("Input source is not a valid string URL or path.")
        if not source.startswith("http"):
            raise ValueError("FetchNode currently only supports HTTP/HTTPS URLs.")
        self.logger.info(f"--- (Fetching HTML from: {source}) ---")
        try:
            loader = ChromiumLoader(
                [source],
                headless=self.headless,
                **self.loader_kwargs,
            )
            document = loader.load()
            if not document or not document[0].page_content.strip():
                 self.logger.warning(f"No content fetched from {source}.")
                 fetched_content = ""
                 doc_list = [Document(page_content="", metadata={"source": source, "error": "No content found"})]
            else:
                 fetched_content = document[0].page_content
                 parsed_content = fetched_content
                 doc_list = [Document(page_content=parsed_content, metadata={"source": source})]
            state.update({
                self.output[0]: doc_list,
            })
            if len(self.output) > 1 and self.output[1] == "original_html":
                 state.update({self.output[1]: fetched_content})
        except Exception as e:
            self.logger.error(f"Failed to fetch content from {source}: {e}")
            state.update({
                 self.output[0]: [Document(page_content="", metadata={"source": source, "error": str(e)})],
            })
            if len(self.output) > 1 and self.output[1] == "original_html":
                 state.update({self.output[1]: ""})
        return state
