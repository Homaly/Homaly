"""Lê a casa real uma vez e mostra as leituras. Só lê; não muda nada na casa.

A partir de backend/, com as variáveis do .env da raiz no ambiente:

    set -a; . ../.env; set +a; uv run python -m backend.dispositivos
"""

import sys
from datetime import datetime

from backend import dispositivos, inventario
from backend.formatos import Leitura


def main() -> None:
    try:
        leituras = dispositivos.ler()
        estado_alarme = dispositivos.alarme()
    except dispositivos.ErroDispositivos as e:
        sys.exit(f"Erro: {e}")
    for l in sorted(leituras, key=lambda l: (l.dispositivo, l.tipo)):
        print(f"{l.dispositivo:12} {l.tipo:28} {l.valor!r}")
    print("\ninventário (de onde vem: csv, ia, mcp ou omissão):")
    for id, tipo in sorted(inventario.registados().items(), key=lambda par: (par[1], par[0])):
        d = inventario.de(Leitura(tipo, "", "", datetime.min, id))
        print(f"  {id[:8]:8} {tipo:12} {inventario.origem(id):8} {d.nome!r:34} {d.divisao!r:20} {d.papel}")
    print(f"\nalarme: {estado_alarme}")
    calados = dispositivos.em_silencio()
    if calados:
        print(f"\ncalados há mais de {dispositivos.silencio_minutos():g} min (leituras de fora):")
        for nome, quando in sorted(calados.items()):
            print(f"  {nome:12} desde {quando.astimezone():%d/%m %H:%M}")


if __name__ == "__main__":
    main()
