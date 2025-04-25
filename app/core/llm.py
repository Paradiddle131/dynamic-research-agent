import logging
from typing import Dict, Any, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, field_validator
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.exceptions import OutputParserException
from google.api_core import exceptions as google_exceptions

from app.core.config import settings

logger = logging.getLogger(__name__)

class SchemaGenerationError(Exception):
    pass

class SchemaField(BaseModel):
    name: str = Field(..., description="The name of the field.")
    type: str = Field(..., description="The JSON type of the field (e.g., 'string', 'number', 'integer', 'boolean', 'array', 'object').")
    items: Optional[str] = Field(None, description="Specifies the type of items if the type is 'array' (e.g., 'string'). Required for type 'array'.")
    description: str = Field(..., description="A brief description of what the field represents.")

    @field_validator('items')
    def check_items_for_array(cls, v, values):
        if values.get('type') == 'array' and not v:
            raise ValueError("The 'items' field is required when type is 'array'.")
        if values.get('type') != 'array' and v:
            raise ValueError("The 'items' field should only be provided when type is 'array'.")
        return v

class GeneratedSchema(BaseModel):
    model_name: str = Field(..., description="A concise, CamelCase name for the data structure (e.g., 'CompanyInfo', 'ProductComparison').")
    description: str = Field(..., description="A brief description of the purpose of this data structure.")
    fields: List[SchemaField] = Field(..., description="A list of fields defining the structure.")


DEFAULT_SCHEMA_DEFINITION = {
    "model_name": "DefaultResearchReport",
    "description": "Default report structure for general research findings.",
    "fields": [
        {"name": "query", "type": "string", "description": "The original research query."},
        {"name": "summary", "type": "string", "description": "A concise summary of the key findings from the search results."},
        {"name": "key_points", "type": "array", "items": "string", "description": "Bulleted list of important facts, figures, or insights discovered."},
        {"name": "entities", "type": "array", "items": "string", "description": "List of significant people, companies, products, or concepts mentioned."},
        {"name": "sources", "type": "array", "items": "string", "description": "List of source URLs from which the information was primarily derived."}
    ]
}


def generate_dynamic_schema(query: str) -> Dict[str, Any]:
    """
    Uses Langchain's ChatGoogleGenerativeAI with structured output to generate a schema definition.
    Falls back to a default schema if the query doesn't imply a structure or if generation fails.
    (This function runs synchronously).
    """

    system_prompt = f"""
    Analyze the user query below. Your task is to determine if the query explicitly requests a specific output structure or specific named fields.

    If the query *clearly specifies* a desired structure or fields (e.g., "list company names and their CEOs", "extract the product name, price, and rating", "summarize the article and list the key people mentioned"), generate a schema definition based *only* on those explicit requirements.

    If the query is general and *does not* specify a structure or fields (e.g., "tell me about quantum computing", "latest news on Mars exploration", "what is photosynthesis?"), indicate that no specific structure was requested.

    Output the schema using the `GeneratedSchema` tool. If no specific structure is requested, populate the `GeneratedSchema` with a model_name like "GeneralQuery" and an empty fields list.
    """

    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.SCHEMA_GENERATION_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )

        structured_llm = llm.with_structured_output(GeneratedSchema)

        logger.info(f"Requesting schema generation.")

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"<query>{query}</query>")
        ]

        response_schema: GeneratedSchema = structured_llm.invoke(messages)

        sources_field_definition = {
            "name": "sources",
            "type": "array",
            "items": "string",
            "description": "List of source URLs from which the information was primarily derived."
        }

        if response_schema and response_schema.fields:
            logger.info(f"Langchain Gemini generated a custom schema: {response_schema.model_name}")
            generated_schema_dict = response_schema.model_dump()
            
            # Ensure 'sources' field is present in the definition, otherwise mergeAnswers node might fail
            field_names = [field['name'] for field in generated_schema_dict.get('fields', [])]
            if "sources" not in field_names:
                logger.info("Adding mandatory 'sources' field to the generated schema.")
                generated_schema_dict.setdefault('fields', []).append(sources_field_definition)
            return generated_schema_dict
        else:
            logger.info("Query did not specify a structure or LLM indicated no specific structure needed. Using the default schema.")
            return DEFAULT_SCHEMA_DEFINITION

    except OutputParserException as ope:
        logger.warning(f"Langchain failed to parse LLM output into schema. Error: {ope}. Falling back to default schema.")
        return DEFAULT_SCHEMA_DEFINITION
    except (google_exceptions.PermissionDenied, google_exceptions.ResourceExhausted, google_exceptions.InvalidArgument) as google_error:
         logger.error(f"Google API error during schema generation: {google_error}")
         raise google_error
    except Exception as e:
        logger.exception(f"Unexpected error during Langchain schema generation: {e}")
        raise SchemaGenerationError(f"An unexpected error occurred during schema generation: {e}") from e
