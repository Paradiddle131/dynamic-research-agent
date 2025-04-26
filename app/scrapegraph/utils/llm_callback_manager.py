from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from typing import Any, Optional
from uuid import UUID

class CustomLLMCallbackManager(BaseCallbackHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost_USD = 0.0

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        if response.llm_output and "token_usage" in response.llm_output:
            token_usage = response.llm_output["token_usage"]
            self.total_tokens += token_usage.get("total_tokens", 0)
            self.prompt_tokens += token_usage.get("prompt_tokens", 0)
            self.completion_tokens += token_usage.get("completion_tokens", 0)
            # Note: Cost is not always available in token_usage, might need a separate mechanism or calculate based on model and tokens
            # For now, we'll assume it might be present or handled elsewhere.
            # self.total_cost_USD += token_usage.get("total_cost_USD", 0.0)

    def reset_counts(self):
        """Reset token counts and cost."""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost_USD = 0.0
