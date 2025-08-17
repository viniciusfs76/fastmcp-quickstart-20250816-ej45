# runner_http.py
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Importa seu servidor FastMCP existente
from echo import create_server  # type: ignore

# Instancia o servidor FastMCP para reutilizar os tools já definidos em echo.py
mcp = create_server()

app = FastAPI(title="FastMCP Echo Runner", version="0.1.0")

# ---------- Healthcheck ----------
@app.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok"}

# ---------- Modelos ----------
class SearchRequest(BaseModel):
    query: str


class FetchRequest(BaseModel):
    id: str


# ---------- Endpoints ----------
@app.post("/search")
async def http_search(req: SearchRequest) -> Dict[str, Any]:
    try:
        return await mcp.search(req.query)  # type: ignore[attr-defined]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"search error: {e}")


@app.post("/fetch")
async def http_fetch(req: FetchRequest) -> Dict[str, Any]:
    try:
        return await mcp.fetch(req.id)  # type: ignore[attr-defined]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch error: {e}")


# ---------- Execução local ----------
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("runner_http:app", host="0.0.0.0", port=port, reload=False)

