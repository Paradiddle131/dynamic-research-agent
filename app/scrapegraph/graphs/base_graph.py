import time
import warnings
from typing import Tuple
from ..utils.logging import get_logger
from ..utils.llm_callback_manager import CustomLLMCallbackManager
class BaseGraph:
    def __init__(
        self,
        nodes: list,
        edges: list,
        entry_point: str,
        graph_name: str = "CustomGraph",
    ):
        self.nodes = nodes
        self.raw_edges = edges
        self.edges = self._create_edges(set(edges))
        self.entry_point = entry_point.node_name
        self.graph_name = graph_name
        self.initial_state = {}
        self.logger = get_logger(__name__)
        self.callback_manager = CustomLLMCallbackManager()
        if nodes and nodes[0].node_name != entry_point.node_name:
            warnings.warn(
                f"Entry point node '{entry_point.node_name}' is not the first node in the graph list."
            )
        self._set_conditional_node_edges()
    def _create_edges(self, edges: list) -> dict:
        edge_dict = {}
        for edge_tuple in edges:
            if len(edge_tuple) != 2:
                continue
            from_node, to_node = edge_tuple
            if from_node is None:
                continue
            if hasattr(from_node, 'node_type') and from_node.node_type != "conditional_node":
                if to_node is not None:
                    edge_dict[from_node.node_name] = to_node.node_name
        return edge_dict
    def _set_conditional_node_edges(self):
        for node in self.nodes:
            if hasattr(node, 'node_type') and node.node_type == "conditional_node":
                outgoing_edges = [
                    (from_node, to_node)
                    for from_node, to_node in self.raw_edges
                    if from_node is not None and from_node.node_name == node.node_name
                ]
                if len(outgoing_edges) != 2:
                    if len(outgoing_edges) == 1:
                        node.true_node_name = outgoing_edges[0][1].node_name if outgoing_edges[0][1] else None
                        node.false_node_name = None
                        self.logger.debug(f"ConditionalNode '{node.node_name}' has only one outgoing edge. False condition will end graph.")
                    else:
                        raise ValueError(
                            f"ConditionalNode '{node.node_name}' must have one or two outgoing edges."
                        )
                else:
                    node.true_node_name = outgoing_edges[0][1].node_name if outgoing_edges[0][1] else None
                    node.false_node_name = outgoing_edges[1][1].node_name if outgoing_edges[1][1] else None
    def _get_node_by_name(self, node_name: str):
        for node in self.nodes:
            if node.node_name == node_name:
                return node
        raise ValueError(f"Node with name '{node_name}' not found in the graph.")
    def _execute_node(self, current_node, state, llm_model, llm_model_name):
        curr_time = time.time()
        result = None
        cb_data = None
        # Reset callback manager counts before executing a node that might use LLM
        if hasattr(current_node, "llm_model"):
             self.callback_manager.reset_counts()
        try:
            result = current_node.execute(state, self.callback_manager)
            node_exec_time = time.time() - curr_time

            # Retrieve token counts from the callback manager after execution
            total_tokens = self.callback_manager.total_tokens
            prompt_tokens = self.callback_manager.prompt_tokens
            completion_tokens = self.callback_manager.completion_tokens
            total_cost_usd = self.callback_manager.total_cost_USD # Assuming cost is handled by callback

            cb_data = {
                "node_name": current_node.node_name,
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "successful_requests": 1, # Assuming a successful execution means at least one request
                "total_cost_USD": total_cost_usd,
                "exec_time": node_exec_time,
            }
        except Exception as e:
             node_exec_time = time.time() - curr_time
             self.logger.error(f"Error executing node {current_node.node_name}: {e}")
             # If an error occurs, capture the current state of the callback manager's counts
             total_tokens = self.callback_manager.total_tokens
             prompt_tokens = self.callback_manager.prompt_tokens
             completion_tokens = self.callback_manager.completion_tokens
             total_cost_usd = self.callback_manager.total_cost_USD

             cb_data = {
                 "node_name": current_node.node_name,
                 "total_tokens": total_tokens,
                 "prompt_tokens": prompt_tokens,
                 "completion_tokens": completion_tokens,
                 "successful_requests": 0,
                 "total_cost_USD": total_cost_usd,
                 "exec_time": node_exec_time,
                 "error": str(e)
             }
             raise
        return result, node_exec_time, cb_data
    def _get_next_node_name(self, current_node, result):
        if hasattr(current_node, 'node_type') and current_node.node_type == "conditional_node":
            return result
        else:
            return self.edges.get(current_node.node_name)
    def execute(self, initial_state: dict) -> Tuple[dict, list]:
        self.initial_state = initial_state
        current_node_name = self.entry_point
        state = initial_state.copy()
        total_exec_time = 0.0
        exec_info = []
        cb_total = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "successful_requests": 0,
            "total_cost_USD": 0.0,
        }
        start_time = time.time()
        error_node = None
        llm_model = None
        llm_model_name = None
        while current_node_name:
            try:
                current_node = self._get_node_by_name(current_node_name)
                if llm_model is None and hasattr(current_node, "llm_model"):
                    llm_model = current_node.llm_model
                    if hasattr(llm_model, "model_name"):
                        llm_model_name = llm_model.model_name
                    elif hasattr(llm_model, "model"):
                        llm_model_name = llm_model.model
                result, node_exec_time, cb_data = self._execute_node(
                    current_node, state, llm_model, llm_model_name
                )
                total_exec_time += node_exec_time
                if cb_data:
                    exec_info.append(cb_data)
                    for key in cb_total:
                        cb_total[key] += cb_data.get(key, 0)
                current_node_name = self._get_next_node_name(current_node, result)
            except Exception as e:
                error_node = current_node_name
                self.logger.exception(f"Graph execution failed at node '{error_node}': {e}")
                if 'cb_data' in locals() and cb_data:
                     cb_data['error'] = str(e)
                else:
                    exec_info.append({
                        "node_name": error_node,
                        "exec_time": time.time() - start_time,
                        "error": str(e)
                    })
                raise RuntimeError(f"Graph execution failed at node '{error_node}'.") from e
        exec_info.append(
            {
                "node_name": "TOTAL RESULT",
                "total_tokens": cb_total["total_tokens"],
                "prompt_tokens": cb_total["prompt_tokens"],
                "completion_tokens": cb_total["completion_tokens"],
                "successful_requests": cb_total["successful_requests"],
                "total_cost_USD": cb_total["total_cost_USD"],
                "exec_time": total_exec_time,
            }
        )
        return state, exec_info
    def append_node(self, node):
        if node.node_name in {n.node_name for n in self.nodes}:
            raise ValueError(
                f"Node with name '{node.node_name}' already exists in the graph."
            )
        last_node = self.nodes[-1] if self.nodes else None
        if last_node:
            self.raw_edges.append((last_node, node))
        else:
            self.logger.warning(f"Appending node '{node.node_name}' to an empty graph.")
            if not self.entry_point:
                 self.entry_point = node.node_name
        self.nodes.append(node)
        self.edges = self._create_edges(set(self.raw_edges))
