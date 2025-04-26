import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin
from langchain_community.document_transformers import Html2TextTransformer
from langchain_core.callbacks import BaseCallbackHandler
from ..helpers import default_filters
from ..utils.split_text_into_chunks import split_text_into_chunks
from .base_node import BaseNode
class ParseNode(BaseNode):
    url_pattern = re.compile(
        r"[http[s]?:\/\/]?(www\.)?([-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)"
    )
    relative_url_pattern = re.compile(r"[\\(](/[^\\(\\)\\s]*)")
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "ParseNode",
    ):
        super().__init__(node_name, "node", input, output, 1, node_config)
        self.verbose = self.node_config.get("verbose", False)
        self.parse_urls = (
            False if node_config is None else node_config.get("parse_urls", False)
        )

        self.llm_model = node_config.get("llm_model")
        self.chunk_size = self.node_config.get("chunk_size", 1024)
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")
        input_keys = self.get_input_keys(state)
        doc_list = state.get(input_keys[0])
        if not doc_list or not isinstance(doc_list, list) or not doc_list[0].page_content:
            self.logger.warning("No document content found to parse.")
            state.update({self.output[0]: []})
            if len(self.output) > 1:
                 state.update({key: [] for key in self.output[1:]})
            return state
        document = doc_list[0]
        source_url = document.metadata.get("source", None)
        try:
            transformer = Html2TextTransformer(ignore_links=False)
            transformed_docs = transformer.transform_documents([document])
            if not transformed_docs or not transformed_docs[0].page_content:
                self.logger.warning(f"Html2TextTransformer returned empty content for source: {source_url}")
                parsed_text = ""
            else:
                parsed_text = transformed_docs[0].page_content
            chunks = split_text_into_chunks(
                text=parsed_text,
                chunk_size=self.chunk_size,
                use_semchunk=False
            )
            state.update({self.output[0]: chunks})
            if len(self.output) > 1:
                link_urls, img_urls = self._extract_urls(parsed_text, source_url)
                if self.output[1] == "link_urls":
                    state.update({self.output[1]: link_urls})
                if len(self.output) > 2 and self.output[2] == "img_urls":
                    state.update({self.output[2]: img_urls})
        except Exception as e:
            self.logger.error(f"Error parsing document from {source_url}: {e}")
            state.update({self.output[0]: []})
            if len(self.output) > 1:
                state.update({key: [] for key in self.output[1:]})
        return state
    def _extract_urls(self, text: str, source: str) -> Tuple[List[str], List[str]]:
        """
        Extracts URLs from the given text.

        Args:
            text (str): The text to extract URLs from.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing the extracted link URLs and image URLs.
        """
        if not self.parse_urls:
            return [], []

        image_extensions = default_filters.filter_dict["img_exts"]
        url = ""
        all_urls = set()

        for group in ParseNode.url_pattern.findall(text):
            for el in group:
                if el != "":
                    url += el
            all_urls.add(url)
            url = ""

        url = ""
        for group in ParseNode.relative_url_pattern.findall(text):
            for el in group:
                if el not in ["", "[", "]", "(", ")", "{", "}"]:
                    url += el
            all_urls.add(urljoin(source, url))
            url = ""

        all_urls = list(all_urls)
        all_urls = self._clean_urls(all_urls)
        if not source.startswith("http"):
            all_urls = [url for url in all_urls if url.startswith("http")]
        else:
            all_urls = [urljoin(source, url) for url in all_urls]

        images = [
            url
            for url in all_urls
            if any(url.endswith(ext) for ext in image_extensions)
        ]
        links = [url for url in all_urls if url not in images]

        return links, images
    def _clean_urls(self, urls: List[str]) -> List[str]:
        cleaned_urls = []
        for url in urls:
            url = re.sub(r'^[\\(\\[]+|[\\)\\]]+$', '', url)
            url = url.strip('.,')
            if len(url) > 0 and url.startswith('http'):
                cleaned_urls.append(url)
        return cleaned_urls
