from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from sqlalchemy import create_engine, text
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

DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def serve_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def run_query(request: QueryRequest):
    query = request.query.strip()
    
    logger.info(f"A user the DB, query: {query}")

    allowed_statements = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
    if not query.upper().startswith(allowed_statements):
        raise HTTPException(status_code=403, detail="Only read-only queries are allowed.")

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = [dict(zip(result.keys(), row)) for row in result]
            return {"rows": rows}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=str(e.__cause__ or e))

@app.get("/")
def root():
    return {"message": "Use /query endpoint with POST (SELECT)"}

# API Key Test
# Payload model including API key
class SecureQueryRequest(BaseModel):
    api_key: str
    query: str  # your actual data field

@app.post("/secure_query")
def secure_data(request: SecureQueryRequest):
    verify_dict = verify_api_key(request.api_key)
    user_id = verify_dict.get("user_id")
    expiry = verify_dict.get("expiry")
    
    query = request.query.strip()
    
    logger.warning(f"User ID: {user_id} (exp in {expiry}) access the DB, query: {query}")

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = [dict(zip(result.keys(), row)) for row in result]
            return {"rows": rows, "user_id": user_id, "expiry": expiry}
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