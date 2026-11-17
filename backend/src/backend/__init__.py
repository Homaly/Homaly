def main() -> None:
    """`uv run backend`: arranca a API em :8000, a recarregar quando o código muda.

    Com RECARREGAR=0 não recarrega: na demo, gravar um ficheiro não reinicia o backend.
    """
    import os

    import uvicorn

    recarregar = os.environ.get("RECARREGAR", "1") == "1"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=recarregar)
