import json
import re
import time
from typing import List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnableParallel
from tqdm import tqdm
from pydantic import ValidationError
from ..prompts import (
    TEMPLATE_CHUNKS,
    TEMPLATE_MERGE,
    TEMPLATE_NO_CHUNKS,
)
from .base_node import BaseNode
from ..utils.logging import get_logger
class GenerateAnswerNode(BaseNode):
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "GenerateAnswer",
    ):
        super().__init__(node_name, "node", input, output, 2, node_config)
        self.llm_model = self.node_config.get("llm_model")
        self.schema = self.node_config.get("schema")
        self.verbose = self.node_config.get("verbose", False)
        self.additional_info = self.node_config.get("additional_info")
        self.timeout = self.node_config.get("timeout", 480)
        self.logger = get_logger(__name__)
    def _invoke_with_timeout(self, chain, inputs, timeout, callback_manager: Optional[BaseCallbackHandler] = None):
        try:
            start_time = time.time()
            config = {"callbacks": [callback_manager]} if callback_manager else {}
            response = chain.invoke(inputs, config=config)
            duration = time.time() - start_time
            if duration > timeout:
                 self.logger.warning(f"LLM call exceeded timeout ({duration:.2f}s > {timeout}s)")
            return response
        except Exception as e:
            self.logger.error(f"Error during LLM chain execution: {e}")
            raise
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")
        input_keys = self.get_input_keys(state)
        if len(input_keys) < 2:
             raise ValueError(f"GenerateAnswerNode requires at least two inputs (prompt, content), found: {input_keys}")
        user_prompt = state.get(input_keys[0])
        doc = state.get(input_keys[1])
        if not user_prompt:
            raise ValueError("User prompt is missing from state.")
        if not doc:
            self.logger.warning("No document content found in state for GenerateAnswerNode.")
            if self.schema:
                 try:
                      empty_data = {field: None for field in self.schema.model_fields.keys()}
                      state.update({self.output[0]: self.schema(**empty_data).model_dump()})
                 except Exception:
                      state.update({self.output[0]: {"error": "No content to process"}})
            else:
                 state.update({self.output[0]: {"answer": "No content to process"}})
            return state
        output_parser = None
        format_instructions = ""
        if self.schema:
            try:
                schema_description = json.dumps(self.schema.model_json_schema(), indent=2)
                format_instructions = f"Format your response as a JSON object adhering to the following schema:\\n```json\\n{schema_description}\\n```"
                output_parser = StrOutputParser()
            except Exception as e:
                self.logger.warning(f"Could not get Pydantic output parser or instructions: {e}. Using default JSON parser.")
                output_parser = JsonOutputParser()
                format_instructions = "You must respond ONLY with a valid JSON object."
        else:
            output_parser = JsonOutputParser()
            format_instructions = "You must respond ONLY with a valid JSON object."
        template_no_chunks_prompt = TEMPLATE_NO_CHUNKS
        template_chunks_prompt = TEMPLATE_CHUNKS
        template_merge_prompt = TEMPLATE_MERGE
        if self.additional_info:
            template_no_chunks_prompt = self.additional_info + "\\n" + template_no_chunks_prompt
            template_chunks_prompt = self.additional_info + "\\n" + template_chunks_prompt
            template_merge_prompt = self.additional_info + "\\n" + template_merge_prompt
        if isinstance(doc, list) and len(doc) == 1:
             doc_content = doc[0]
        elif isinstance(doc, str):
             doc_content = doc
        elif isinstance(doc, list) and len(doc) > 1:
             doc_content = doc
        else:
             self.logger.warning(f"Unexpected document format: {type(doc)}. Attempting to process.")
             doc_content = str(doc)
        final_answer = None
        try:
            if isinstance(doc_content, str) or (isinstance(doc_content, list) and len(doc_content) == 1):
                single_content = doc_content[0] if isinstance(doc_content, list) else doc_content
                prompt = PromptTemplate(
                    template=template_no_chunks_prompt,
                    input_variables=["question", "context"],
                    partial_variables={"format_instructions": format_instructions},
                )
                chain = prompt | self.llm_model | output_parser
                response_content = self._invoke_with_timeout(
                    chain, {"question": user_prompt, "context": single_content}, self.timeout
                )
                final_answer = response_content
            elif isinstance(doc_content, list) and len(doc_content) > 1:
                chains_dict = {}
                for i, chunk in enumerate(tqdm(doc_content, desc="Processing chunks", disable=not self.verbose)):
                    prompt = PromptTemplate(
                        template=template_chunks_prompt,
                        input_variables=["question", "context"],
                        partial_variables={
                            "chunk_id": i + 1,
                            "format_instructions": format_instructions,
                        },
                    )
                    chain_name = f"chunk_{i+1}"
                    chains_dict[chain_name] = prompt | self.llm_model | output_parser
                map_chain = RunnableParallel(**chains_dict)
                batch_results = self._invoke_with_timeout(
                    map_chain, {"question": user_prompt, "context": ""}, self.timeout
                )
                merge_prompt = PromptTemplate(
                    template=template_merge_prompt,
                    input_variables=["question", "context"],
                    partial_variables={"format_instructions": format_instructions},
                )
                merge_chain = merge_prompt | self.llm_model | output_parser
                merge_context = "\\n---\\n".join([str(res) for res in batch_results.values()])
                final_answer = self._invoke_with_timeout(
                    merge_chain, {"question": user_prompt, "context": merge_context}, self.timeout
                )
        except Exception as e:
            self.logger.error(f"Failed to generate answer: {e}")
            state.update({self.output[0]: {"error": f"Answer generation failed: {str(e)}", "raw_response": None}})
            return state
        if self.schema and isinstance(final_answer, str):
            try:
                cleaned_json_str = re.sub(r"^```json\n|```$", "", final_answer, flags=re.DOTALL).strip()
                parsed_answer = json.loads(cleaned_json_str)
                validated_answer = self.schema(**parsed_answer).model_dump()
                state.update({self.output[0]: validated_answer})
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM JSON response: {e}\\nRaw response: {final_answer}")
                state.update({self.output[0]: {"error": "Failed to parse LLM JSON response", "raw_response": final_answer}})
            except ValidationError as e:
                 self.logger.error(f"LLM response failed Pydantic validation: {e}\\nParsed JSON: {parsed_answer}")
                 state.update({self.output[0]: {"error": "LLM response failed schema validation", "parsed_json": parsed_answer}})
            except Exception as e:
                 self.logger.error(f"Unexpected error during answer post-processing: {e}")
                 state.update({self.output[0]: {"error": "Answer post-processing failed", "raw_response": final_answer}})
        elif isinstance(final_answer, dict):
             state.update({self.output[0]: final_answer})
        else:
             state.update({self.output[0]: {"answer": str(final_answer)} if final_answer is not None else {"error": "No answer generated"}})
        return state
