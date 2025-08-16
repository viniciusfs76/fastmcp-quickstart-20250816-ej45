# runner_http.py
import os
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Importa seu servidor FastMCP existente
from echo import mcp  # type: ignore

app = FastAPI(title="FastMCP Echo Runner", version="0.1.0")

# ---------- Healthcheck ----------
@app.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok"}

# ---------- Modelos ----------
class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class FetchRequest(BaseModel):
    ids: List[str]

# ---------- Endpoints ----------
@app.post("/search")
def http_search(req: SearchRequest) -> List[Dict[str, Any]]:
    try:
        result = None
        if hasattr(mcp, "search"):
            result = mcp.search(req.query, req.limit)  # type: ignore[attr-defined]
        else:
            from echo import search as search_tool  # type: ignore
            result = search_tool(req.query, req.limit)
        if not isinstance(result, list):
            raise ValueError("search must return a list")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"search error: {e}")

@app.post("/fetch")
def http_fetch(req: FetchRequest) -> List[Dict[str, Any]]:
    try:
        result = None
        if hasattr(mcp, "fetch"):
            result = mcp.fetch(req.ids)  # type: ignore[attr-defined]
        else:
            from echo import fetch as fetch_tool  # type: ignore
            result = fetch_tool(req.ids)
        if not isinstance(result, list):
            raise ValueError("fetch must return a list")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch error: {e}")

# ---------- ExecuÃ§Ã£o local ----------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("runner_http:app", host="0.0.0.0", port=port, reload=False)