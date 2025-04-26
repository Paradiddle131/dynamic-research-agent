from typing import List
from .tokenizer import num_tokens_calculus
def split_text_into_chunks(text: str, chunk_size: int, use_semchunk=False) -> List[str]:
    tokens = num_tokens_calculus(text)
    if tokens <= chunk_size:
        return [text]
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0
    words = text.split()
    if not words:
         return []
    for word in words:
        word_tokens = num_tokens_calculus(word) + 1
        if current_length + word_tokens > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_tokens -1
            if current_length > chunk_size:
                 print(f"Warning: Word '{word[:30]}...' exceeds chunk size {chunk_size}")
                 if len(current_chunk) > 1:
                     chunks.append(" ".join(current_chunk[:-1]))
                     current_chunk = [word]
                     current_length = word_tokens -1
        else:
            current_chunk.append(word)
            current_length += word_tokens
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks
