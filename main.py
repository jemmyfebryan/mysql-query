from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import re
import os
import time

from api.api_key import verify_api_key
from core.logger import get_logger

from dotenv import load_dotenv
load_dotenv(override=True)

logger = get_logger(__name__)

app = FastAPI()

DB_CONFIG = {
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASS"),
    "host": os.getenv("MYSQL_HOST"),
    "database": os.getenv("MYSQL_DB"),
}

# Use async driver (aiomysql) and create async engine
DATABASE_URL = f"mysql+aiomysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def serve_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class QueryRequest(BaseModel):
    query: str
    params: dict = None  # Optional parameters for parameterized queries

@app.post("/query")
async def run_query(request: QueryRequest):
    query = request.query.strip()
    params = request.params or {}
    
    logger.info(f"A user accessed the DB, query: {query} with params: {params}")

    allowed_statements = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
    if not query.upper().startswith(allowed_statements):
        raise HTTPException(status_code=403, detail="Only read-only queries are allowed.")

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(query), params)
            rows = [dict(zip(result.keys(), row)) for row in result]
            return {"rows": rows}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=str(e.__cause__ or e))


# API Key Test
# Payload model including API key
class SecureQueryRequest(BaseModel):
    api_key: str
    query: str  # your actual data field
    params: dict = None  # Optional parameters for parameterized queries

@app.post("/secure_query")
async def secure_data(request: SecureQueryRequest):
    verify_dict = verify_api_key(request.api_key)
    user_id = verify_dict.get("user_id")
    expiry = verify_dict.get("expiry")
    
    query = request.query.strip()
    params = request.params or {}
    
    logger.warning(f"User ID: {user_id} (exp in {expiry}) accessed the DB, query: {query} with params: {params}")

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(query), params)

            # Check the type of query (e.g., SELECT vs. INSERT/UPDATE/DELETE)
            query_type = query.split()[0].upper()

            if query_type in {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN"}:
                rows = [dict(zip(result.keys(), row)) for row in result]
                return {"rows": rows, "user_id": user_id, "expiry": expiry}
            
            response = {
                "message": f"{query_type} executed successfully.",
                "user_id": user_id,
                "expiry": expiry
            }

            # Capture last insert ID if applicable
            if query_type == "INSERT":
                last_id_result = await connection.execute(text("SELECT LAST_INSERT_ID()"))
                last_insert_id = last_id_result.scalar()
                if last_insert_id:
                    response["last_insert_id"] = last_insert_id

            return response
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=str(e.__cause__ or e))
    
# @app.post("/secure-data")
# def secure_data(payload: SecurePayload):
#     verify_dict = verify_api_key(payload.api_key)
#     user_id = verify_dict.get("user_id")
#     expiry_in = verify_dict.get("expiry")
#     if expiry_in == 0:
#         expiry_in = "UNLIMITED"
#     else:
#         expiry_in = expiry_in - int(time.time())
#     return {
#         "message": f"Hello {user_id}, api_key expiry in {expiry_in}, you sent: {payload.query}"
#     }