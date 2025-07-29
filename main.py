from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import re
import os

from dotenv import load_dotenv

load_dotenv(override=True)

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
