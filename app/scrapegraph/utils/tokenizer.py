import tiktoken
from .logging import get_logger
logger = get_logger(__name__)
try:
    encoding = tiktoken.encoding_for_model("gpt-4o")
except Exception:
    logger.warning("gpt-4o encoding not found, falling back to cl100k_base.")
    encoding = tiktoken.get_encoding("cl100k_base")
def num_tokens_calculus(string: str) -> int:
    """
    Estimates the number of tokens in a text string using tiktoken.
    """
    if not isinstance(string, str):
         logger.debug(f"Input to num_tokens_calculus is not a string: {type(string)}. Returning 0 tokens.")
         return 0
    if not string:
        return 0
    try:
        num_tokens = len(encoding.encode(string))
        return num_tokens
    except Exception as e:
        logger.error(f"Error calculating tokens: {e}. Falling back to character count estimate.")
        return len(string) // 4
