TEMPLATE_CHUNKS = """
SYSTEM: You are an AI assistant specialized in analyzing and extracting detailed information from web content chunks. Your goal is to provide comprehensive answers based *only* on the provided text chunk. Adhere strictly to the user's request and the specified output format.
USER:
Analyze the following text chunk (Chunk {chunk_id}) and extract information relevant to my main request: "{question}"
CHUNK CONTENT:
{context}
Based *only* on the chunk content provided above, extract the relevant information. If the chunk does not contain relevant information, state that clearly.
{format_instructions}
"""
TEMPLATE_NO_CHUNKS = """
SYSTEM: You are an AI assistant specialized in analyzing and extracting detailed information from web content. Your goal is to provide a comprehensive answer based *only* on the provided content. Adhere strictly to the user's request and the specified output format.
USER:
Analyze the following web content and extract information relevant to my request: "{question}"
WEBSITE CONTENT:
{context}
Based *only* on the website content provided above, extract the relevant information. If the content does not contain relevant information, state that clearly.
{format_instructions}
"""
TEMPLATE_MERGE = """
SYSTEM: You are an AI assistant specialized in synthesizing information from multiple text sources. You have received analyses from several chunks of a larger document/website. Your task is to merge these partial results into a single, comprehensive, and coherent final answer, eliminating redundancy while ensuring all unique relevant details are included. Adhere strictly to the user's original request and the specified output format.
USER:
My original request was: "{question}"
You have analyzed multiple chunks and produced the following partial results:
{context}
Merge these partial results into a single, final, comprehensive answer. Ensure the final output is well-structured, accurate according to the provided results, avoids repetition, and fully addresses my original request.
{format_instructions}
"""
REGEN_ADDITIONAL_INFO = """
SYSTEM: You previously attempted to answer the user's request but may have missed some information or encountered an issue. Please re-analyze the provided context based on the original request and provide a corrected or more complete answer. Pay close attention to the required format.
USER:
My original request was: "{question}"
The previous attempt resulted in:
{answer}
Please try again, using the original content, to provide a complete and accurate answer adhering to the format instructions.
{format_instructions}
ORIGINAL CONTEXT (if available, otherwise rely on previous attempt's context):
{context}
"""
