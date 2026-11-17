def main() -> None:
    """`uv run backend`: arranca a API em :8000, a recarregar quando o código muda."""
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
