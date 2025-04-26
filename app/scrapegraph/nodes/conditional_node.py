from typing import List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from .base_node import BaseNode
from ..utils.logging import get_logger
class ConditionalNode(BaseNode):
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "Conditional",
    ):
        super().__init__(node_name, "conditional_node", input, output, 1, node_config)
        self.logger = get_logger(__name__)
        self.key_name = input.strip()
        self.condition = self.node_config.get("condition", None)
        if not self.condition:
             self.condition = f"'{self.key_name}' in state and state['{self.key_name}']"
             self.logger.debug(f"No condition provided for {node_name}, using default: '{self.condition}'")
        self.true_node_name = None
        self.false_node_name = None
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> Optional[str]:
        """
        Evaluates the condition against the state and returns the name of the next node.
        Args:
            state (dict): The current state of the graph.
            callback_manager (Optional[BaseCallbackHandler]): Callback manager for handling callbacks.
        Returns:
            Optional[str]: The name of the next node (True or False path), or None if the path ends.
        """
        self.logger.debug(f"--- Executing {self.node_name} ---")
        self.logger.debug(f"Condition: {self.condition}")
        self.logger.debug(f"True Node: {self.true_node_name}, False Node: {self.false_node_name}")
        try:
            eval_context = {'state': state}
            condition_result = bool(eval(self.condition, {"__builtins__": {}}, eval_context))
            self.logger.debug(f"Condition evaluated to: {condition_result}")
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{self.condition}' in node {self.node_name}: {e}")
            condition_result = False
            self.logger.warning(f"Condition evaluation failed, defaulting to False path ({self.false_node_name}).")
        if condition_result:
            self.logger.info(f"Condition TRUE, proceeding to node: {self.true_node_name}")
            return self.true_node_name
        else:
            self.logger.info(f"Condition FALSE, proceeding to node: {self.false_node_name}")
            return self.false_node_name
