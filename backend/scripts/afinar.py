"""Passa o histórico pelas regras e mostra os falsos alarmes e as folgas (ver backend.afinacao).

Uso (em backend/): uv run python scripts/afinar.py
"""

from backend.afinacao import main

if __name__ == "__main__":
    main()
