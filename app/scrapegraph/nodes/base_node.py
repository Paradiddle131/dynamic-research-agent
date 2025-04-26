import re
from abc import ABC, abstractmethod
from typing import List, Optional
from ..utils.logging import get_logger
from langchain_core.callbacks import BaseCallbackHandler

class BaseNode(ABC):
    def __init__(
        self,
        node_name: str,
        node_type: str,
        input: str,
        output: List[str],
        min_input_len: int = 1,
        node_config: Optional[dict] = None,
    ):
        self.node_name = node_name
        self.input = input
        self.output = output
        self.min_input_len = min_input_len
        self.node_config = node_config if node_config is not None else {}
        self.logger = get_logger(__name__)
        if node_type not in ["node", "conditional_node"]:
            raise ValueError(
                f"node_type must be 'node' or 'conditional_node', got '{node_type}'"
            )
        self.node_type = node_type
        for key, value in self.node_config.items():
             if hasattr(self, key):
                 setattr(self, key, value)
    @abstractmethod
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        pass
    def get_input_keys(self, state: dict) -> List[str]:
        try:
            input_keys = self._parse_input_keys(state, self.input)
            self._validate_input_keys(input_keys, state)
            return input_keys
        except ValueError as e:
            self.logger.error(f"Error parsing input keys for node {self.node_name}: {e}")
            raise ValueError(f"Input key parsing failed for {self.node_name}") from e
    def _validate_input_keys(self, input_keys, state):
        if len(input_keys) < self.min_input_len:
            raise ValueError(
                f"{self.node_name} requires at least {self.min_input_len} input keys from spec '{self.input}', "
                f"but only found {len(input_keys)} valid keys in state: {list(state.keys())}."
            )
    def _parse_input_keys(self, state: dict, expression: str) -> List[str]:
        if not expression:
            raise ValueError("Input expression cannot be empty.")
        available_keys = set(state.keys())
        expression = expression.strip()
        identifiers = set(re.findall(r'\\b([a-zA-Z_][a-zA-Z0-9_]*)\\b', expression))
        unknown_keys = identifiers - available_keys
        if unknown_keys:
            self.logger.warning(f"Expression '{expression}' contains keys not found in state: {unknown_keys}")
        or_groups = expression.split('|')
        valid_keys_found = []
        for or_group in or_groups:
            and_keys = [key.strip() for key in or_group.replace('(', '').replace(')', '').split('&')]
            if all(key in available_keys for key in and_keys):
                valid_keys_found.extend(key for key in and_keys if key in available_keys)
                break
        final_keys = []
        for key in valid_keys_found:
             if key not in final_keys:
                 final_keys.append(key)
        if not final_keys:
             single_key_match = re.fullmatch(r'\\b([a-zA-Z_][a-zA-Z0-9_]*)\\b', expression)
             if single_key_match and expression not in available_keys:
                  raise ValueError(f"Required key '{expression}' not found in state keys: {list(available_keys)}")
             raise ValueError(
                 f"No valid set of input keys found for expression '{expression}' "
                 f"with available state keys: {list(available_keys)}"
             )
        return final_keys
