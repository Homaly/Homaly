"""Lê a casa real uma vez e mostra as leituras. Só lê; não muda nada na casa.

A partir de backend/, com as variáveis do .env da raiz no ambiente:

    set -a; . ../.env; set +a; uv run python -m backend.dispositivos
"""

import sys

from backend import dispositivos


def main() -> None:
    try:
        leituras = dispositivos.ler()
        estado_alarme = dispositivos.alarme()
    except dispositivos.ErroDispositivos as e:
        sys.exit(f"Erro: {e}")
    for l in sorted(leituras, key=lambda l: (l.dispositivo, l.tipo)):
        print(f"{l.dispositivo:12} {l.tipo:28} {l.valor!r}")
    print(f"\nalarme: {estado_alarme}")
    calados = dispositivos.em_silencio()
    if calados:
        print(f"\ncalados há mais de {dispositivos.silencio_minutos():g} min (leituras de fora):")
        for nome, quando in sorted(calados.items()):
            print(f"  {nome:12} desde {quando.astimezone():%d/%m %H:%M}")


if __name__ == "__main__":
    main()
