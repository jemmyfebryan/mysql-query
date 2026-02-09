import os
import json
import base64
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from api.api_key import verify_api_key
from core.models import SecureQueryRequest
from core.register_connection import register_mysql_endpoint
from core.logger import get_logger

from dotenv import load_dotenv
load_dotenv(override=True)

logger = get_logger(__name__)

app = FastAPI()

# HTTP Basic Auth Configuration
ACCESS_CREDENTIAL = os.getenv("ACCESS_CREDENTIAL")
AUTH_REALM = "MySQL Query Service"
STATIC_DIR = Path("static")

async def verify_basic_auth(request: Request) -> Optional[None]:
    """Verify HTTP Basic Authentication for all requests."""
    if not ACCESS_CREDENTIAL:
        # No password required if ACCESS_PASSWORD is not set
        return None
    
    access_username, access_password = ACCESS_CREDENTIAL.split(sep=":")

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": f'Basic realm="{AUTH_REALM}"'},
        )

    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication type",
            headers={"WWW-Authenticate": f'Basic realm="{AUTH_REALM}"'},
        )

    try:
        encoded_credentials = auth_header.split(" ")[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)

        # Verify password (username is ignored, only password matters)
        if username != access_username or password != access_password:
            logger.warning(f"Failed authentication attempt from user: {username}")
            raise HTTPException(
                status_code=401,
                detail="Invalid password",
                headers={"WWW-Authenticate": f'Basic realm="{AUTH_REALM}"'},
            )

    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials format",
            headers={"WWW-Authenticate": f'Basic realm="{AUTH_REALM}"'},
        )

@app.get("/static/{file_path:path}", dependencies=[Depends(verify_basic_auth)])
async def serve_static(file_path: str):
    """Serve static files with authentication."""
    file_path = STATIC_DIR / file_path
    if file_path.is_file():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# DB Registration Configuration
## Single DB Connection
DB_CONFIG = {
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASS"),
    "host": os.getenv("MYSQL_HOST"),
    "database": os.getenv("MYSQL_DB"),
}
## Multiple DB Connetions
### Load config.json and Build a dictionary of engines for each database
engines = {}
if os.path.exists("config.json"):
    with open("config.json") as f:
        config = json.load(f)

    for db_cfg in config.get("mysql", []):
        # conn_str = (
        #     f"mysql+aiomysql://{db_cfg['MYSQL_USER']}:{db_cfg['MYSQL_PASS']}"
        #     f"@{db_cfg['MYSQL_HOST']}/{db_cfg['MYSQL_DB']}"
        # )
        conn_url = URL.create(
            drivername="mysql+aiomysql",
            username=db_cfg["MYSQL_USER"],
            password=db_cfg["MYSQL_PASS"],            # raw password; URL handles escaping
            host=db_cfg["MYSQL_HOST"],
            port=int(db_cfg.get("MYSQL_PORT", 3306)) if db_cfg.get("MYSQL_PORT") else None,
            database=db_cfg["MYSQL_DB"],
        )
        
        cfg_name = db_cfg["NAME"]
        engines[f"/mysql/{cfg_name}"] = create_async_engine(
            conn_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )

# Use async driver (aiomysql) and create async engine
# DATABASE_URL = f"mysql+aiomysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
DATABASE_URL = URL.create(
    drivername="mysql+aiomysql",
    username=DB_CONFIG['user'],
    password=DB_CONFIG['password'],            # raw password; URL handles escaping
    host=DB_CONFIG['host'],
    port=int(DB_CONFIG.get("port", 3306)) if DB_CONFIG.get("port") else None,
    database=DB_CONFIG['database'],
)

single_db_engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

templates = Jinja2Templates(directory="templates")

@app.get("/", dependencies=[Depends(verify_basic_auth)])
async def serve_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Register Single DB Connection
# Only require auth if ACCESS_PASSWORD is set
auth_dep = verify_basic_auth if ACCESS_CREDENTIAL else None
register_mysql_endpoint(app, "/query", single_db_engine, auth_dependency=auth_dep)

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

# Multi DB Connections
## Register endpoints dynamically from config.json
for name, engine in engines.items():
    register_mysql_endpoint(app, name, engine, auth_dependency=auth_dep)