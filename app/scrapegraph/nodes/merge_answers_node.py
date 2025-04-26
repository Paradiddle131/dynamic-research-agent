import json
import re
from typing import List, Optional
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import ValidationError
from ..prompts import TEMPLATE_COMBINED
from .base_node import BaseNode
from ..utils.logging import get_logger
class MergeAnswersNode(BaseNode):
    def __init__(
        self,
        input: str,
        output: List[str],
        node_config: Optional[dict] = None,
        node_name: str = "MergeAnswers",
    ):
        super().__init__(node_name, "node", input, output, 2, node_config)
        self.llm_model = self.node_config.get("llm_model")
        self.schema = self.node_config.get("schema")
        self.verbose = self.node_config.get("verbose", False)
        self.logger = get_logger(__name__)
    def execute(self, state: dict, callback_manager: Optional[BaseCallbackHandler] = None) -> dict:
        self.logger.info(f"--- Executing {self.node_name} Node ---")
        input_keys = self.get_input_keys(state)
        if len(input_keys) < 2:
             raise ValueError(f"MergeAnswersNode requires at least two inputs (prompt, results), found: {input_keys}")
        user_prompt = state.get(input_keys[0])
        results = state.get(input_keys[1])
        if not user_prompt:
            raise ValueError("User prompt is missing from state.")
        if not results or not isinstance(results, list):
            self.logger.warning("No results found or results are not a list.")
            if self.schema:
                 try:
                      empty_data = {field: None for field in self.schema.model_fields.keys()}
                      state.update({self.output[0]: self.schema(**empty_data).model_dump()})
                 except Exception:
                      state.update({self.output[0]: {"error": "No results to merge"}})
            else:
                 state.update({self.output[0]: {"answer": "No results to merge"}})
            return state
        valid_results = [res for res in results if isinstance(res, dict) and "error" not in res]
        if not valid_results:
             self.logger.warning("All results contained errors, cannot merge.")
             state.update({self.output[0]: {"error": "All scraping results failed"}})
             return state
        results_str = ""
        for i, res in enumerate(valid_results):
             results_str += f"--- Source {i+1} Result ---\\n"
             results_str += json.dumps(res, indent=2)
             results_str += "\\n\\n"
        output_parser = None
        format_instructions = ""
        if self.schema:
            try:
                schema_description = json.dumps(self.schema.model_json_schema(), indent=2)
                format_instructions = f"Merge the provided results into a single JSON object adhering to the following schema. Ensure comprehensive coverage and eliminate redundancy:\\n```json\\n{schema_description}\\n```"
                output_parser = StrOutputParser()
            except Exception as e:
                self.logger.warning(f"Could not get Pydantic output parser/instructions for merging: {e}. Using default JSON parser.")
                output_parser = JsonOutputParser()
                format_instructions = "Merge the provided results into a single, comprehensive JSON object. Eliminate redundancy. Respond ONLY with the final JSON object."
        else:
            output_parser = JsonOutputParser()
            format_instructions = "Merge the provided results into a single, comprehensive JSON object. Eliminate redundancy. Respond ONLY with the final JSON object."
        prompt_template = PromptTemplate(
            template=TEMPLATE_COMBINED,
            input_variables=["user_prompt", "website_content"],
            partial_variables={"format_instructions": format_instructions},
        )
        merge_chain = prompt_template | self.llm_model | output_parser
        final_answer = None
        try:
            final_answer = merge_chain.invoke(
                {"user_prompt": user_prompt, "website_content": results_str},
                config={"callbacks": [callback_manager]} if callback_manager else {}
            )
        except Exception as e:
            self.logger.error(f"Failed to merge answers: {e}")
            state.update({self.output[0]: {"error": f"Answer merging failed: {str(e)}", "raw_response": None}})
            return state
        if self.schema and isinstance(final_answer, str):
            try:
                cleaned_json_str = re.sub(r"^```json\n|```$", "", final_answer, flags=re.DOTALL).strip()
                parsed_answer = json.loads(cleaned_json_str)
                validated_answer = self.schema(**parsed_answer).model_dump()
                state.update({self.output[0]: validated_answer})
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse merged LLM JSON response: {e}\\nRaw response: {final_answer}")
                state.update({self.output[0]: {"error": "Failed to parse merged LLM JSON response", "raw_response": final_answer}})
            except ValidationError as e:
                 self.logger.error(f"Merged LLM response failed Pydantic validation: {e}\\nParsed JSON: {parsed_answer}")
                 state.update({self.output[0]: {"error": "Merged response failed schema validation", "parsed_json": parsed_answer}})
            except Exception as e:
                 self.logger.error(f"Unexpected error during merged answer post-processing: {e}")
                 state.update({self.output[0]: {"error": "Merged answer post-processing failed", "raw_response": final_answer}})
        elif isinstance(final_answer, dict):
             state.update({self.output[0]: final_answer})
        else:
             state.update({self.output[0]: {"answer": str(final_answer)} if final_answer is not None else {"error": "No merged answer generated"}})
        source_urls = state.get("urls", [])
        if source_urls and isinstance(state.get(self.output[0]), dict):
            state[self.output[0]]["sources"] = source_urls
        return state
