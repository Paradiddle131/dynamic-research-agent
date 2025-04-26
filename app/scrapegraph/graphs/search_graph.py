from typing import List, Optional, Type
from pydantic import BaseModel
from copy import deepcopy
from .abstract_graph import AbstractGraph
from .base_graph import BaseGraph
from .smart_scraper_graph import SmartScraperGraph
from ..nodes import SearchInternetNode, GraphIteratorNode, MergeAnswersNode
from ..utils.copy import safe_deepcopy
class SearchGraph(AbstractGraph):
    def __init__(
        self,
        prompt: str,
        config: dict,
        schema: Optional[Type[BaseModel]] = None,
    ):
        self.max_results = config.get("max_results", 3)
        self.merge_results = config.get("merge_results", True)
        self.copy_config = safe_deepcopy(config)
        try:
            self.copy_schema = deepcopy(schema)
        except TypeError:
            self.copy_schema = schema
        self.considered_urls = []
        super().__init__(prompt, config, schema=schema)
    def _create_graph(self) -> BaseGraph:
        search_internet_node = SearchInternetNode(
            input="user_prompt",
            output=["urls", "user_prompt"],
            node_config={
                "llm_model": self.llm_model,
                "max_results": self.max_results,
                "search_engine": self.copy_config.get("search_engine", "duckduckgo"),
            },
            node_name="SearchInternet"
        )
        graph_iterator_node = GraphIteratorNode(
            input="user_prompt & urls",
            output=["results"],
            node_config={
                "graph_instance": SmartScraperGraph,
                "scraper_config": self.copy_config,
                 "batchsize": self.copy_config.get("batchsize", 16)
            },
            schema=self.copy_schema,
            node_name="GraphIterator"
        )
        if self.merge_results:
            merge_answers_node = MergeAnswersNode(
                input="user_prompt & results",
                output=["answer"],
                node_config={"llm_model": self.llm_model, "schema": self.copy_schema},
                node_name="MergeAnswers"
            )
            nodes = [search_internet_node, graph_iterator_node, merge_answers_node]
            edges = [
                (search_internet_node, graph_iterator_node),
                (graph_iterator_node, merge_answers_node),
            ]
        else:
            nodes = [search_internet_node, graph_iterator_node]
            edges = [
                (search_internet_node, graph_iterator_node),
                (graph_iterator_node, None)
            ]
        return BaseGraph(
            nodes=nodes,
            edges=edges,
            entry_point=search_internet_node,
            graph_name=self.__class__.__name__,
        )
    def run(self) -> str:
        inputs = {"user_prompt": self.prompt}
        self.final_state, self.execution_info = self.graph.execute(inputs)
        if "urls" in self.final_state:
            self.considered_urls = self.final_state["urls"]
        if self.merge_results:
            return self.final_state.get("answer", "No answer found.")
        else:
            return self.final_state.get("results", [])
    def get_considered_urls(self) -> List[str]:
        return self.considered_urls
