# echo.py
from fastmcp import FastMCP
from typing import List, Dict

mcp = FastMCP("Echo Server")

# --------- TOOL: echo ---------
@mcp.tool()
def echo_tool(text: str) -> str:
    """Retorna exatamente o texto recebido."""
    return text

# --------- RESOURCES ---------
@mcp.resource("echo://static")
def static_resource() -> str:
    return "Echo!"

@mcp.resource("echo://{text}")
def dynamic_resource(text: str) -> str:
    return f"Echo: {text}"

# --------- PROMPT ---------
@mcp.prompt("echo")
def echo_prompt(text: str) -> str:
    return text

# --------- NOVO: TOOL search ---------
# Retorna "documentos" com id, title, snippet (estrutura simples e estável)
@mcp.tool(name="search", description="Busca itens de exemplo dentro do servidor MCP.")
def search(query: str, limit: int = 10) -> List[Dict]:
    items = [
        {"id": "echo://static", "title": "Static Echo", "snippet": "Echo!"},
        {"id": f"echo://{query}", "title": f"Echo for '{query}'", "snippet": f"Echo: {query}"},
    ]
    return items[:limit]

# --------- NOVO: TOOL fetch ---------
# Recebe ids e devolve conteúdo textual
@mcp.tool(name="fetch", description="Busca o conteúdo bruto de itens por id.")
def fetch(ids: List[str]) -> List[Dict]:
    results = []
    for _id in ids:
        if _id == "echo://static":
            results.append({"id": _id, "mime_type": "text/plain", "content": "Echo!"})
        elif _id.startswith("echo://"):
            text = _id.replace("echo://", "", 1)
            results.append({"id": _id, "mime_type": "text/plain", "content": f"Echo: {text}"})
        else:
            results.append({"id": _id, "error": "not_found"})
    return results
