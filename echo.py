"""
Sample MCP Server for ChatGPT Integration — refatorado

- Ferramentas MCP: search(query), fetch(id)
- OpenAI SDK: usa OPENAI_API_KEY via env; VECTOR_STORE_ID via env
- Tratamento robusto de erros e logs estruturados
"""

import logging
import os
import time
from typing import Dict, List, Any, Optional

from fastmcp import FastMCP
from openai import OpenAI
from openai._exceptions import NotFoundError

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("mcp.sample")

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # O SDK lê automaticamente; validamos aqui
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")  # defina esta env var com o ID real

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY não definido. Exporte a variável de ambiente antes de iniciar."
    )

if not VECTOR_STORE_ID:
    raise RuntimeError(
        "VECTOR_STORE_ID não definido. Exporte a variável de ambiente com o ID do seu vector store."
    )

# Cliente OpenAI (usa OPENAI_API_KEY do ambiente)
client = OpenAI()

SERVER_INSTRUCTIONS = """
Este servidor MCP expõe ferramentas de busca e recuperação sobre um Vector Store
da OpenAI. Use 'search' para localizar documentos relevantes e 'fetch' para
recuperar o conteúdo completo de um documento pelo ID.
"""

# -----------------------------------------------------------------------------
# Utilitários
# -----------------------------------------------------------------------------
def _now_ms() -> int:
    return int(time.time() * 1000)


def _mk_url(file_id: str) -> str:
    # URL útil para auditoria/citação no dashboard
    return f"https://platform.openai.com/storage/files/{file_id}"


# -----------------------------------------------------------------------------
# MCP Server
# -----------------------------------------------------------------------------
def create_server() -> FastMCP:
    mcp = FastMCP(name="Sample MCP Server", instructions=SERVER_INSTRUCTIONS)

    @mcp.tool()
    async def search(query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Busca documentos no Vector Store associado.

        Args:
            query: consulta em linguagem natural

        Returns:
            {"results": [{"id", "title", "text", "url"}]}
        """
        started = _now_ms()
        results: List[Dict[str, Any]] = []

        if not query or not query.strip():
            logger.info("search :: query vazia -> 0 resultados")
            return {"results": results}

        logger.info(
            "search :: iniciando busca",
            extra={"vs_id": VECTOR_STORE_ID, "query": query},
        )
        try:
            # Tente a superfície atual do SDK
            resp = client.vector_stores.search(
                vector_store_id=VECTOR_STORE_ID,
                query=query,
                limit=10,  # ajuste conforme necessário
            )
        except AttributeError as e:
            logger.error(
                "search :: método vector_stores.search não encontrado; atualize o SDK",
                extra={"error": str(e)},
            )
            raise
        except Exception as e:
            logger.exception("search :: erro na consulta ao vector store")
            raise

        # Normalização dos resultados
        try:
            data = getattr(resp, "data", []) or []
            for i, item in enumerate(data):
                file_id = getattr(item, "file_id", f"vs_{i}")
                filename = getattr(item, "filename", f"Document {i+1}")

                # Alguns SDKs retornam chunks/trechos em 'content' ou 'text'
                snippet = ""
                content = getattr(item, "content", None)
                if isinstance(content, list) and content:
                    first = content[0]
                    if hasattr(first, "text"):
                        snippet = first.text or ""
                    elif isinstance(first, dict):
                        snippet = first.get("text", "") or ""
                if not snippet:
                    snippet = getattr(item, "text", "") or "No content available"

                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."

                results.append(
                    {
                        "id": file_id,
                        "title": filename,
                        "text": snippet,
                        "url": _mk_url(file_id),
                    }
                )
        except Exception as e:
            logger.exception("search :: falha ao processar resultados")
            raise

        elapsed = _now_ms() - started
        logger.info(
            "search :: sucesso",
            extra={"hits": len(results), "ms": elapsed, "vs_id": VECTOR_STORE_ID},
        )
        return {"results": results}

    @mcp.tool()
    async def fetch(id: str) -> Dict[str, Any]:
        """
        Recupera o conteúdo completo de um documento pelo file_id.

        Args:
            id: file_id do documento no Vector Store

        Returns:
            {"id","title","text","url","metadata"}
        """
        if not id or not id.strip():
            raise ValueError("fetch :: 'id' é obrigatório")

        started = _now_ms()
        logger.info("fetch :: iniciando", extra={"file_id": id})

        # Conteúdo
        try:
            content_resp = client.vector_stores.files.content(
                vector_store_id=VECTOR_STORE_ID,
                file_id=id,
            )
        except AttributeError as e:
            logger.error(
                "fetch :: método vector_stores.files.content não encontrado; atualize o SDK",
                extra={"error": str(e)},
            )
            raise
        except NotFoundError:
            logger.warning("fetch :: arquivo não encontrado", extra={"file_id": id})
            raise
        except Exception as e:
            logger.exception("fetch :: erro ao obter conteúdo")
            raise

        # Metadata
        try:
            file_info = client.vector_stores.files.retrieve(
                vector_store_id=VECTOR_STORE_ID,
                file_id=id,
            )
        except Exception:
            file_info = None
            logger.warning("fetch :: não foi possível recuperar metadados", extra={"file_id": id})

        # Montagem do texto
        full_text = ""
        try:
            parts: List[str] = []
            data = getattr(content_resp, "data", []) or []
            for c in data:
                if hasattr(c, "text"):
                    parts.append(c.text or "")
                elif isinstance(c, dict) and "text" in c:
                    parts.append(c["text"] or "")
            full_text = "\n".join(parts) if parts else "No content available"
        except Exception:
            logger.exception("fetch :: falha ao montar o texto")
            raise

        title = getattr(file_info, "filename", f"Document {id}") if file_info else f"Document {id}"
        metadata: Optional[Any] = getattr(file_info, "attributes", None) if file_info else None

        elapsed = _now_ms() - started
        logger.info("fetch :: sucesso", extra={"ms": elapsed, "bytes": len(full_text)})

        return {
            "id": id,
            "title": title,
            "text": full_text,
            "url": _mk_url(id),
            "metadata": metadata,
        }

    return mcp


def main() -> None:
    server = create_server()
    logger.info("Iniciando MCP server via SSE em 0.0.0.0:8000")
    try:
        server.run(transport="sse", host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logger.info("Servidor encerrado pelo usuário")
    except Exception:
        logger.exception("Erro fatal no servidor")
        raise


if __name__ == "__main__":
    main()