from typing import List, Optional
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.callbacks import BaseCallbackHandler
from ..prompts import TEMPLATE_SEARCH_INTERNET
from ..utils.research_web import search_on_web
from .base_node import BaseNode
class SearchInternetNode(BaseNode):
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "SearchInternet",
    ):
        super().__init__(node_name, "node", input, output, 1, node_config)
        self.llm_model = self.node_config.get("llm_model")
        self.verbose = self.node_config.get("verbose", False)
        self.search_engine = self.node_config.get("search_engine", "duckduckgo")
        self.max_results = self.node_config.get("max_results", 3)
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")
        input_keys = self.get_input_keys(state)
        user_prompt = state[input_keys[0]]
        search_prompt = PromptTemplate(
            template=TEMPLATE_SEARCH_INTERNET,
            input_variables=["user_prompt"],
        )
        messages = [HumanMessage(content=search_prompt.format(user_prompt=user_prompt))]
        try:
            llm_response = self.llm_model.invoke(messages)
            search_query = llm_response.content.strip().strip('"').strip("'")
            if not search_query:
                 self.logger.warning("LLM generated an empty search query. Using the original prompt.")
                 search_query = user_prompt
        except Exception as e:
            self.logger.error(f"Error generating search query with LLM: {e}")
            self.logger.warning("Using the original prompt as search query due to error.")
            search_query = user_prompt
        self.logger.info(f"Search Query: {search_query}")
        try:
            search_results = search_on_web(
                query=search_query,
                max_results=self.max_results,
                search_engine=self.search_engine,
            )
            if not search_results:
                self.logger.warning(f"No results found for query: {search_query}")
                state.update({self.output[0]: []})
            else:
                state.update({self.output[0]: search_results})
        except Exception as e:
            self.logger.error(f"Error during web search for query '{search_query}': {e}")
            state.update({self.output[0]: []})
        state.update({self.output[1]: user_prompt})
        return state
