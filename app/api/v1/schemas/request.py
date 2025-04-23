from pydantic import BaseModel, Field

class ResearchRequest(BaseModel):
    """
    Pydantic model defining the expected structure of the request body
    for the research endpoint.
    """
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The natural language query for the research task."
    )
