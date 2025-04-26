from abc import ABC, abstractmethod
from typing import Optional, Type
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from ..utils.logging import get_logger
from ..helpers.models_tokens import models_tokens
class AbstractGraph(ABC):
    def __init__(
        self,
        prompt: str,
        config: dict,
        source: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
    ):
        self.prompt = prompt
        self.source = source
        self.config = config
        self.schema = schema
        self.logger = get_logger(__name__)
        self.llm_model = self._create_llm(config["llm"])
        self.verbose = config.get("verbose", False)
        self.headless = config.get("headless", True)
        self.loader_kwargs = config.get("loader_kwargs", {})
        self.timeout = config.get("timeout", 480)
        self.graph = self._create_graph()
        self.final_state = None
        self.execution_info = None
        common_params = {
            "headless": self.headless,
            "verbose": self.verbose,
            "loader_kwargs": self.loader_kwargs,
            "llm_model": self.llm_model,
            "timeout": self.timeout,
        }
        self.set_common_params(common_params, overwrite=True)
    def set_common_params(self, params: dict, overwrite=False):
        for node in self.graph.nodes:
            for key, val in params.items():
                 if hasattr(node, key):
                     if getattr(node, key) is None or overwrite:
                         setattr(node, key, val)
            if hasattr(node, 'node_config') and node.node_config is not None:
                 for key, val in params.items():
                     if key not in node.node_config or overwrite:
                         node.node_config[key] = val
    def _create_llm(self, llm_config: dict) -> object:
        llm_provider = llm_config.get("provider", "google_genai")
        model_name = llm_config.get("model")
        api_key = llm_config.get("api_key")
        temperature = llm_config.get("temperature", 0.1)
        if llm_provider != "google_genai":
            raise ValueError("This internal Scrapegraph implementation only supports 'google_genai'.")
        if not model_name:
            raise ValueError("LLM model name ('model') is required in the config.")
        if not api_key:
            raise ValueError("LLM API key ('api_key') is required in the config.")
        try:
            provider_models = models_tokens.get(llm_provider, {})
            self.model_token = provider_models.get(model_name, 8192)
            self.logger.info(f"Using token limit for {model_name}: {self.model_token}")
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                convert_system_message_to_human=True
            )
            return llm
        except ImportError:
            raise ImportError(
                "langchain_google_genai is not installed. Please install it using 'pip install langchain-google-genai'."
            )
        except Exception as e:
            self.logger.error(f"Error initializing ChatGoogleGenerativeAI: {e}")
            raise RuntimeError(f"Failed to initialize the Gemini LLM: {e}") from e
    def get_state(self, key=None) -> dict:
        if self.final_state is None:
            return {}
        if key is not None:
            return self.final_state.get(key)
        return self.final_state
    def get_execution_info(self):
        return self.execution_info
    @abstractmethod
    def _create_graph(self):
        pass
    @abstractmethod
    def run(self) -> str:
        pass
