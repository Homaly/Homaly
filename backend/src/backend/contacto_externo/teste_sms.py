"""Uma SMS de teste, para confirmar que o textbee está a funcionar.

A partir de backend/, com as variáveis do .env da raiz no ambiente:

    set -a; . ../.env; set +a; uv run python -m backend.contacto_externo.teste_sms 912345678
"""

import os
import sys

from pydantic import ValidationError

from backend.contrato import Contacto

from . import sms


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        sys.exit("uso: python -m backend.contacto_externo.teste_sms <telemóvel>")
    try:
        numero = Contacto(nome="teste", telemovel=argv[0]).telemovel
    except ValidationError as e:
        sys.exit(f"Erro: {e.errors()[0]['msg'].removeprefix('Value error, ')}")
    if not os.environ.get("TEXTBEE_API_KEY", "").strip():
        sys.exit("Sem TEXTBEE_API_KEY no ambiente: a SMS não sai.")
    try:
        sms.enviar(numero, "Homaly: SMS de teste. Se a recebeu, o textbee está a funcionar.")
    except sms.ErroSMS as e:
        sys.exit(f"Erro: {e}")
    print(f"O textbee aceitou a SMS para {numero}. Confirme no telemóvel.")


if __name__ == "__main__":
    main(sys.argv[1:])
