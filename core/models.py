from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    params: dict = None  # Optional parameters for parameterized queries
    api_key: str = None  # Optional API key
    
# Payload model including API key
class SecureQueryRequest(BaseModel):
    api_key: str
    query: str  # your actual data field
    params: dict = None  # Optional parameters for parameterized queries
