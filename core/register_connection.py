from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from api.api_key import verify_api_key
from core.models import QueryRequest
from core.logger import get_logger

logger = get_logger(__name__)

def register_mysql_endpoint(app: FastAPI, db_name: str, engine):
    """
    Dynamically register endpoints like /mysql/{db_name}
    """

    @app.post(f"{db_name}")
    async def run_query(request: QueryRequest):
        query = request.query.strip()
        params = request.params or {}

        # Case 1: With API Key (secure mode)
        if request.api_key:
            verify_dict = verify_api_key(request.api_key)
            user_id = verify_dict.get("user_id")
            expiry = verify_dict.get("expiry")

            logger.warning(
                f"[{db_name}] User ID: {user_id} (exp in {expiry}) accessed query: {query} with params: {params}"
            )

            try:
                async with engine.connect() as connection:
                    result = await connection.execute(text(query), params)
                    query_type = query.split()[0].upper()

                    if query_type in {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN"}:
                        rows = [dict(zip(result.keys(), row)) for row in result]
                        return {"rows": rows, "user_id": user_id, "expiry": expiry}

                    response = {
                        "message": f"{query_type} executed successfully.",
                        "user_id": user_id,
                        "expiry": expiry
                    }

                    if query_type == "INSERT":
                        last_id_result = await connection.execute(
                            text("SELECT LAST_INSERT_ID()")
                        )
                        last_insert_id = last_id_result.scalar()
                        if last_insert_id:
                            response["last_insert_id"] = last_insert_id

                    return response

            except SQLAlchemyError as e:
                raise HTTPException(status_code=400, detail=str(e.__cause__ or e))

        # Case 2: Without API Key (readonly mode)
        else:
            logger.info(f"[{db_name}] Public query: {query} with params: {params}")

            allowed_statements = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
            if not query.upper().startswith(allowed_statements):
                raise HTTPException(
                    status_code=403,
                    detail="Only read-only queries are allowed without API key."
                )

            try:
                async with engine.connect() as connection:
                    result = await connection.execute(text(query), params)
                    rows = [dict(zip(result.keys(), row)) for row in result]
                    return {"rows": rows}
            except SQLAlchemyError as e:
                raise HTTPException(status_code=400, detail=str(e.__cause__ or e))