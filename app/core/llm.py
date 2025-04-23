import json
import logging
from typing import Dict, Any

import google as genai
from google.api_core import exceptions as google_exceptions

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA_DEFINITION = {
    "model_name": "DefaultResearchReport",
    "description": "Default report structure for general research findings.",
    "fields": [
        {"name": "query", "type": "string", "description": "The original research query."},
        {"name": "summary", "type": "string", "description": "A concise summary of the key findings from the search results."},
        {"name": "key_points", "type": "array", "items": "string", "description": "Bulleted list of important facts, figures, or insights discovered."},
        {"name": "entities", "type": "array", "items": "string", "description": "List of significant people, companies, products, or concepts mentioned."},
        {"name": "source_urls", "type": "array", "items": "string", "description": "List of URLs from which the information was primarily derived."}
    ]
}

def generate_dynamic_schema(query: str) -> Dict[str, Any]:
    """
    Asks the Gemini model to generate a Pydantic-like schema definition based on the query.
    Falls back to a default schema if the query doesn't specify one or if the LLM fails.
    (This function runs synchronously).
    """
    default_schema_json = json.dumps(DEFAULT_SCHEMA_DEFINITION)

    prompt = f"""
        Analyze the following user query:
        <query>{query}</query>

        Determine if the query explicitly asks for a specific structure or specific fields for the output.

        If the query *does* specify a structure (e.g., "list names and prices", "summarize findings and list sources", "extract company name, CEO, and founding date"), generate a JSON object representing a schema definition based *only* on those explicit instructions. The JSON object must have keys: "model_name" (string, e.g., "ProductList"), "description" (string, summarizing the schema's purpose), and "fields" (an array of objects, each with "name": string, "type": string [choose from: "string", "number", "integer", "boolean", "array", "object"], "items": string [required and only for type 'array', e.g., "string"], and "description": string). Stick strictly to the fields requested in the query. Use standard JSON types.

        If the query *does not* explicitly specify a structure or fields (e.g., "tell me about AI", "latest news on climate change"), output the following default schema JSON exactly:
        {default_schema_json}

        Output *only* the JSON object (either the generated one or the default one) and nothing else. Do not include explanations, markdown formatting like ```json, or any text before or after the JSON object. Ensure the output is valid JSON.
        """

    try:
        logger.info(f"Requesting schema generation from Gemini model: {settings.SCHEMA_GENERATION_MODEL}")
        model = genai.GenerativeModel(settings.SCHEMA_GENERATION_MODEL)

        generation_config = genai.types.GenerationConfig(
             # response_mime_type="application/json", # Enable if supported and desired
             temperature=0.0
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        schema_json_string = response.text.strip()
        if schema_json_string.startswith("```json"):
            schema_json_string = schema_json_string[7:]
        if schema_json_string.endswith("```"):
            schema_json_string = schema_json_string[:-3]
        schema_json_string = schema_json_string.strip()

        try:
            parsed_schema = json.loads(schema_json_string)
            if isinstance(parsed_schema, dict) and 'fields' in parsed_schema and isinstance(parsed_schema['fields'], list):
                logger.info("Gemini generated a valid custom schema structure.")
                return parsed_schema
            else:
                logger.warning(f"Gemini response was JSON but not the expected schema structure. Falling back to default. Response: {schema_json_string[:200]}...")
                return DEFAULT_SCHEMA_DEFINITION
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse Gemini response as JSON. Raw response: '{schema_json_string}'. Falling back to default schema.")
            return DEFAULT_SCHEMA_DEFINITION

    except google_exceptions.PermissionDenied as e:
         logger.error(f"Gemini API permission denied. Check API key and permissions: {e}")
         raise ConnectionError(f"Gemini API permission denied: {e}") from e
    except google_exceptions.ResourceExhausted as e:
         logger.error(f"Gemini API quota exceeded: {e}")
         raise ConnectionAbortedError(f"Gemini API quota exceeded: {e}") from e
    except google_exceptions.InvalidArgument as e:
         logger.error(f"Invalid argument passed to Gemini API (check model name or parameters): {e}")
         raise ValueError(f"Invalid argument for Gemini API: {e}") from e
    except Exception as e:
        logger.exception(f"Unexpected error during Gemini schema generation: {e}")

    logger.info("Falling back to default schema due to error or invalid response.")
    return DEFAULT_SCHEMA_DEFINITION
