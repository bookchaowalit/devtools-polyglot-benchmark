import json
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

with open(os.environ["RECORDS_PATH"], encoding="utf-8") as fh:
    ITEMS = {r["id"]: r for r in json.load(fh)}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/items/{item_id}")
async def item(item_id: str):
    record = ITEMS.get(int(item_id)) if item_id.isdigit() else None
    if record is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return record


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["PORT"]), log_level="warning", access_log=False)
