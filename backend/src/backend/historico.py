"""O histórico (US06): o que a casa viu, além das mudanças dos sensores.

As mudanças dos sensores (a porta abriu, a luz acendeu) chegam como eventos pelo `dispositivos`.
Aqui fica o resto, como eventos do mesmo `GET /eventos`, para o Histórico mostrar tudo por ordem:

- `anomalia_mudou(anterior, nova)`: a anomalia nova e a anomalia resolvida, com `anomaliaId`, para o
  Histórico abrir o detalhe. O `anomalias.guardar` chama-a sempre, por isso nenhum caminho fica de
  fora (ciclo, resposta, ação, /dev).
- `registar_desvio(desvio, motivo, agora)`: o desvio que a casa viu e não avisou (silenciado, ou a
  IA achou que não valia a pena). É o `registar_historico` que o ciclo recebe.
"""

from datetime import datetime

from backend import eventos
from backend.contrato import Anomalia, Evento
from backend.formatos import Desvio
from backend.ia.avaliar import us_da_anomalia

# O nome do dispositivo de cada user story, como nos eventos dos sensores.
DISPOSITIVO_POR_US = {
    "US07": "Porta da rua",
    "US08": "Porta da rua",
    "US10": "Sala",
    "US11": "Luz da sala",
    "US12": "Porta da rua",
    "US13": "Câmara da entrada",
    "US14": "Tomada",
}
SEM_DISPOSITIVO = "Casa"


def dispositivo(us: str | None) -> str:
    return DISPOSITIVO_POR_US.get(us or "", SEM_DISPOSITIVO)


def anomalia_mudou(anterior: Anomalia | None, nova: Anomalia) -> None:
    """Regista a anomalia nova e a passagem a resolvida. As outras mudanças não são eventos."""
    nome = dispositivo(us_da_anomalia(nova.id))
    if anterior is None:
        eventos.registar(
            Evento(
                id=f"{nova.id}-nova",  # id fixo: guardar duas vezes não repete o evento
                em=nova.detetada_em,
                dispositivo=nome,
                descricao=nova.titulo,
                anomalia_id=nova.id,
            )
        )
    if nova.estado == "resolvida" and (anterior is None or anterior.estado != "resolvida"):
        if nova.resolucao:
            descricao, em = _maiuscula(nova.resolucao.texto), nova.resolucao.em
        elif nova.resposta:
            descricao, em = f"Resolvida: {nova.resposta.texto}", nova.resposta.em
        else:
            descricao, em = "Resolvida", None
        campos = dict(id=f"{nova.id}-resolvida", dispositivo=nome, descricao=descricao, anomalia_id=nova.id)
        eventos.registar(Evento(**campos, **({"em": em} if em else {})))


def registar_desvio(desvio: Desvio, motivo: str, agora: datetime) -> None:
    """O desvio que a casa viu e não avisou, com o motivo (ex.: "silenciado pelo responsável")."""
    eventos.registar(
        Evento(
            em=agora,
            dispositivo=dispositivo(desvio.us),
            descricao=f"{desvio.resumo} Não avisou: {motivo}.",
        )
    )


def _maiuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]
