from typing import Optional, Type
from pydantic import BaseModel
from .abstract_graph import AbstractGraph
from .base_graph import BaseGraph
from ..nodes import FetchNode, ParseNode, GenerateAnswerNode, ConditionalNode
from ..prompts import REGEN_ADDITIONAL_INFO
class SmartScraperGraph(AbstractGraph):
    def __init__(
        self,
        prompt: str,
        source: str,
        config: dict,
        schema: Optional[Type[BaseModel]] = None,
    ):
        if source:
             self.input_key = "url" if source.startswith("http") else "local_dir"
        else:
             self.input_key = "url"
        super().__init__(prompt, config, source, schema)
        self.verbose = config.get("verbose", False)
    def _create_graph(self) -> BaseGraph:
        fetch_node = FetchNode(
            input="url | local_dir",
            output=["doc", "original_html"],
            node_config={
                "llm_model": self.llm_model,
                "force": self.config.get("force", False),
                "loader_kwargs": self.config.get("loader_kwargs", {}),
            },
            node_name="Fetch"
        )
        parse_node = ParseNode(
            input="doc",
            output=["parsed_doc"],
            node_config={
                "llm_model": self.llm_model,
                "chunk_size": self.model_token,
                "parse_html": True
            },
             node_name="Parse"
        )
        generate_answer_node = GenerateAnswerNode(
            input="user_prompt & (parsed_doc | doc)",
            output=["answer"],
            node_config={
                "llm_model": self.llm_model,
                "schema": self.schema,
                "additional_info": self.config.get("additional_info"),
                 "timeout": self.config.get("timeout", 480)
            },
            node_name="GenerateAnswer"
        )
        cond_node = None
        regen_node = None
        if self.config.get("reattempt", False):
            cond_node = ConditionalNode(
                input="answer",
                output=["next_action"],
                node_config={
                    "key_name": "answer",
                    "condition": 'not answer or (isinstance(answer, str) and answer == "NA") or (isinstance(answer, dict) and not answer)',
                },
                 node_name="ConditionalNode"
            )
            regen_node = GenerateAnswerNode(
                input="user_prompt & answer",
                output=["answer"],
                node_config={
                    "llm_model": self.llm_model,
                    "schema": self.schema,
                    "additional_info": REGEN_ADDITIONAL_INFO,
                    "timeout": self.config.get("timeout", 480)
                },
                 node_name="RegenerateAnswer"
            )
            nodes = [fetch_node, parse_node, generate_answer_node, cond_node, regen_node]
            edges = [
                (fetch_node, parse_node),
                (parse_node, generate_answer_node),
                (generate_answer_node, cond_node),
                (cond_node, regen_node),
                (cond_node, None),
                (regen_node, None)
            ]
        else:
            nodes = [fetch_node, parse_node, generate_answer_node]
            edges = [
                (fetch_node, parse_node),
                (parse_node, generate_answer_node),
                (generate_answer_node, None)
            ]
        return BaseGraph(
            nodes=nodes,
            edges=edges,
            entry_point=fetch_node,
            graph_name=self.__class__.__name__,
        )
    def run(self) -> str:
        self.input_key = "url" if self.source and self.source.startswith("http") else "local_dir"
        if not self.source:
             self.logger.error("SmartScraperGraph run called without a valid source.")
             return {"error": "Missing source URL/path"}
        inputs = {"user_prompt": self.prompt, self.input_key: self.source}
        try:
            self.final_state, self.execution_info = self.graph.execute(inputs)
            return self.final_state.get("answer", {"error": "No answer generated"})
        except Exception as e:
             self.logger.exception(f"Error running SmartScraperGraph for source {self.source}: {e}")
             return {"error": f"Graph execution failed: {str(e)}"}
