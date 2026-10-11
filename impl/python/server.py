import json
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

with open(os.environ["RECORDS_PATH"], encoding="utf-8") as fh:
    ITEMS = {r["id"]: r for r in json.load(fh)}

POOL_SIZE = 10
DB_QUERY = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > %s ORDER BY id LIMIT %s"
pool: AsyncConnectionPool | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    if os.environ.get("DATABASE_URL"):
        pool = AsyncConnectionPool(
            os.environ["DATABASE_URL"], min_size=POOL_SIZE, max_size=POOL_SIZE,
            kwargs={"row_factory": dict_row}, open=False,
        )
        await pool.open(wait=True)
    yield
    if pool is not None:
        await pool.close()


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/items/{item_id}")
async def item(item_id: str):
    record = ITEMS.get(int(item_id)) if item_id.isdigit() else None
    if record is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return record


def _int_param(request: Request, name: str, default: int) -> int | None:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    return int(raw) if raw.isdigit() else None


@app.get("/db/items")
async def db_items(request: Request):
    if pool is None:
        return JSONResponse({"error": "no_database"}, status_code=503)
    after = _int_param(request, "after", 0)
    limit = _int_param(request, "limit", 50)
    if after is None or limit is None or not 1 <= limit <= 100:
        return JSONResponse({"error": "bad_request"}, status_code=400)
    async with pool.connection() as conn:
        rows = await (await conn.execute(DB_QUERY, (after, limit))).fetchall()
    return {"items": rows}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["PORT"]), log_level="warning", access_log=False)
