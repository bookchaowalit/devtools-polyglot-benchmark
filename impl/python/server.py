"""python-fastapi lane and its variants.

The baseline uses no BENCH_* flags. Handlers return plain dicts, so FastAPI serializes them through its normal
path (jsonable_encoder + the default response class), exactly as the cells do.
Each variant lane sets exactly one flag
(see runner/lanes.py), so a result difference has one cause:

    BENCH_LOOP=uvloop    uvloop event loop + httptools parser (uvicorn[standard])
    BENCH_JSON=orjson    ORJSONResponse instead of the stdlib-json JSONResponse
    BENCH_DB=asyncpg     asyncpg pool instead of psycopg_pool
    BENCH_WORKERS=2      two uvicorn worker processes; the 10 connections are split between them
"""

import json
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

LOOP = os.environ.get("BENCH_LOOP", "asyncio")
JSON_LIB = os.environ.get("BENCH_JSON", "json")
DB_DRIVER = os.environ.get("BENCH_DB", "psycopg")
WORKERS = int(os.environ.get("BENCH_WORKERS", "1"))

if JSON_LIB == "orjson":
    from fastapi.responses import ORJSONResponse as Response
else:
    Response = JSONResponse

with open(os.environ["RECORDS_PATH"], encoding="utf-8") as fh:
    ITEMS = {r["id"]: r for r in json.load(fh)}

TOTAL_CONNECTIONS = 10
POOL_SIZE = TOTAL_CONNECTIONS // WORKERS
PSYCOPG_QUERY = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > %s ORDER BY id LIMIT %s"
ASYNCPG_QUERY = "SELECT id, name, price_cents, qty, tags FROM bench_items WHERE id > $1 ORDER BY id LIMIT $2"
pool = None


async def _open_pool(url: str):
    if DB_DRIVER == "asyncpg":
        import asyncpg

        return await asyncpg.create_pool(url, min_size=POOL_SIZE, max_size=POOL_SIZE)
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    p = AsyncConnectionPool(
        url,
        min_size=POOL_SIZE,
        max_size=POOL_SIZE,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await p.open(wait=True)
    return p


async def _fetch(after: int, limit: int) -> list:
    if DB_DRIVER == "asyncpg":
        async with pool.acquire() as conn:
            return [dict(r) for r in await conn.fetch(ASYNCPG_QUERY, after, limit)]
    async with pool.connection() as conn:
        return await (await conn.execute(PSYCOPG_QUERY, (after, limit))).fetchall()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    if os.environ.get("DATABASE_URL"):
        pool = await _open_pool(os.environ["DATABASE_URL"])
    yield
    if pool is not None:
        await pool.close()


app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
    default_response_class=Response,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/items/{item_id}")
async def item(item_id: str):
    record = ITEMS.get(int(item_id)) if item_id.isdigit() else None
    if record is None:
        return Response({"error": "not_found"}, status_code=404)
    return record


def _int_param(request: Request, name: str, default: int) -> int | None:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    return int(raw) if raw.isdigit() else None


@app.get("/db/items")
async def db_items(request: Request):
    if pool is None:
        return Response({"error": "no_database"}, status_code=503)
    after = _int_param(request, "after", 0)
    limit = _int_param(request, "limit", 50)
    if after is None or limit is None or not 1 <= limit <= 100 or after > 2**31 - 1:
        return Response({"error": "bad_request"}, status_code=400)
    return {"items": await _fetch(after, limit)}


if __name__ == "__main__":
    options = {
        "host": "127.0.0.1",
        "port": int(os.environ["PORT"]),
        "log_level": "warning",
        "access_log": False,
    }
    if LOOP == "uvloop":
        options.update(loop="uvloop", http="httptools")
    else:
        options.update(loop="asyncio", http="h11")
    if WORKERS > 1:
        uvicorn.run(
            "server:app",
            workers=WORKERS,
            app_dir=os.path.dirname(os.path.abspath(__file__)),
            **options,
        )
    else:
        uvicorn.run(app, **options)
