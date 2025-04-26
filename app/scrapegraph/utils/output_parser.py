from typing import Any, Callable, Dict, Type, Union
import json
import re
from pydantic import BaseModel, ValidationError
try:
    from pydantic.v1 import BaseModel as BaseModelV1
except ImportError:
    BaseModelV1 = None
from .logging import get_logger
logger = get_logger(__name__)
def get_structured_output_parser(
    schema: Union[Dict[str, Any], Type[BaseModel], Type],
) -> Callable:
    logger.debug("Using basic JSON parsing for structured output.")
    return json.loads
def get_pydantic_output_parser(
    schema: Type[BaseModel],
) -> Callable:
    if not issubclass(schema, BaseModel):
        raise ValueError("Schema must be a Pydantic BaseModel subclass.")
    def parse_and_validate(json_string: str) -> dict:
        try:
            cleaned_json_str = re.sub(r"^```json\\s*|\\s*```$", "", json_string, flags=re.MULTILINE | re.DOTALL).strip()
            data = json.loads(cleaned_json_str)
            validated_model = schema(**data)
            return validated_model.model_dump()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\\nRaw string: {json_string}")
            raise ValueError(f"Invalid JSON format received from LLM: {e}") from e
        except ValidationError as e:
            logger.error(f"Pydantic validation failed: {e}\\nParsed data: {data}")
            raise ValueError(f"LLM output failed schema validation: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during Pydantic parsing: {e}")
            raise ValueError(f"Failed to process LLM output with schema: {e}") from e
    return parse_and_validate
def _base_model_v1_output_parser(x: Any) -> dict:
    if BaseModelV1 and isinstance(x, BaseModelV1):
        logger.warning("Processing Pydantic V1 model - V2 is recommended.")
        return x.dict()
    return x
def _base_model_v2_output_parser(x: Any) -> dict:
    if isinstance(x, BaseModel):
        return x.model_dump()
    return x
def _dict_output_parser(x: dict) -> dict:
    return x
