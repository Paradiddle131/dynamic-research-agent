import logging
from typing import List, Dict, Any, Type, Optional

from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

def map_json_type_to_python(json_type: str, items_type: Optional[str] = None) -> Type:
    """Maps JSON schema types to Python types for Pydantic."""
    type_mapping = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "object": Dict[str, Any],
        "array": list
    }

    if json_type == "array":
        if items_type:
            item_py_type = map_json_type_to_python(items_type) 
            return List[item_py_type]
        else:
            logger.warning("Array type specified without 'items' type, defaulting to List[Any]")
            return List[Any]

    py_type = type_mapping.get(json_type)
    if py_type is None:
        logger.warning(f"Unknown JSON type '{json_type}', defaulting to Any")
        return Any
    return py_type

def create_dynamic_model(schema_definition: Dict[str, Any]) -> Type[BaseModel]:
    """
    Creates a Pydantic BaseModel class dynamically from a schema definition dictionary.
    """
    model_name = schema_definition.get("model_name", "DynamicResearchModel")
    model_description = schema_definition.get("description", f"Dynamically generated model for {model_name}")
    fields_config: Dict[str, Any] = {}

    if not isinstance(schema_definition.get("fields"), list):
         raise ValueError("Schema definition must contain a list of 'fields'.")

    for field_info in schema_definition["fields"]:
        if not isinstance(field_info, dict):
             logger.warning(f"Skipping invalid field definition (not a dict): {field_info}")
             continue

        field_name = field_info.get("name")
        field_type_str = field_info.get("type")
        field_items_type_str = field_info.get("items")
        field_description = field_info.get("description", "")

        if not field_name or not isinstance(field_name, str):
            logger.warning(f"Skipping field with invalid or missing name: {field_info}")
            continue
        if not field_type_str or not isinstance(field_type_str, str):
             logger.warning(f"Skipping field '{field_name}' with invalid or missing type: {field_info}")
             continue
        if field_type_str == "array" and (not field_items_type_str or not isinstance(field_items_type_str, str)):
             logger.warning(f"Skipping array field '{field_name}' with invalid or missing 'items' type: {field_info}")
             continue

        try:
            python_type = map_json_type_to_python(field_type_str, field_items_type_str)
            fields_config[field_name] = (python_type, Field(description=field_description))
        except Exception as e:
            logger.error(f"Error processing field '{field_name}': {e}. Skipping field.")
            continue

    if not fields_config:
         raise ValueError("No valid fields could be generated for the dynamic model from the provided schema definition.")

    DynamicModel = create_model(
        model_name,
        __doc__=model_description,
        **fields_config
    )
    logger.info(f"Successfully created dynamic Pydantic model: {model_name}")
    return DynamicModel
