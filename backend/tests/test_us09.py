"""Os casos de dados/us09.csv."""

from datetime import datetime

from backend import falsos
from backend.avisos import Avisos
from backend.ciclo import Ciclo, correr
from backend.contrato import Anomalia
from backend.formatos import Contexto, Periodo
from backend.regras import us09
from tests.regras_casa import DADOS, Registo

FERIAS = Periodo(datetime(2026, 11, 23), datetime(2026, 11, 29, 23, 59), "férias no Algarve")
CONTEXTO = Contexto(ferias=[FERIAS], rotinas=[], silencios=[], casa_vazia=False)


def test_casos_da_us09():
    r = Registo(us09, CONTEXTO).correr("us09.csv")

    assert [quando for quando, _ in r.avaliados] == [
        datetime(2026, 11, 20, 9, 0),  # sexta: não abriu até às 09:00
        datetime(2026, 11, 21, 11, 30),  # sábado: não abriu até às 11:30
        datetime(2026, 12, 1, 9, 0),  # terça, depois de um dia com arranque tardio
    ]
    assert all(d.classe == "bem_estar" and not d.imediato for _, d in r.avaliados)
    # Resolve-se sozinha quando a porta abre; a de sábado atravessa a meia-noite.
    assert r.publicadas == [
        (datetime(2026, 11, 20, 9, 0), "ativa", "bem_estar"),
        (datetime(2026, 11, 20, 9, 40), "resolvida", "bem_estar"),
        (datetime(2026, 11, 21, 11, 30), "ativa", "bem_estar"),
        (datetime(2026, 11, 22, 10, 30), "resolvida", "bem_estar"),
        (datetime(2026, 12, 1, 9, 0), "ativa", "bem_estar"),
        (datetime(2026, 12, 1, 9, 30), "resolvida", "bem_estar"),
    ]


def test_resumo_e_habitual():
    r = Registo(us09, CONTEXTO).correr("us09.csv")
    sexta, sabado = r.avaliados[0][1], r.avaliados[1][1]
    assert sexta.resumo == "A porta ainda não tinha aberto hoje às 09:00."
    assert sexta.habitual == "Nos dias úteis, a porta costuma abrir pela primeira vez até às 08:30."
    assert sabado.resumo == "A porta ainda não tinha aberto hoje às 11:30."
    assert sabado.habitual == "Ao fim de semana, a porta costuma abrir pela primeira vez até às 11:00."


def test_sem_ferias_avisa_e_fica_ativa_ate_a_porta_abrir():
    r = Registo(us09, Contexto([], [], [], False)).correr("us09.csv")
    assert [q for q, _ in r.avaliados][2:] == [datetime(2026, 11, 23, 9, 0)]
    # Dias sem a porta abrir não a resolvem; só a abertura de 1/12.
    assert r.publicadas[4:] == [
        (datetime(2026, 11, 23, 9, 0), "ativa", "bem_estar"),
        (datetime(2026, 12, 1, 9, 30), "resolvida", "bem_estar"),
    ]


def test_casa_vazia_nao_avisa():
    r = Registo(us09, Contexto([], [], [], casa_vazia=True)).correr("us09.csv")
    assert r.avaliados == []


class Contacto:
    def __init__(self):
        self.chamadas: list[str] = []

    def agendar(self, anomalia: Anomalia, imediato: bool = False) -> None:
        self.chamadas.append(f"agendar {anomalia.estado}")

    def cancelar(self, anomalia_id: str) -> None:
        self.chamadas.append("cancelar")

    def resolvida(self, anomalia: Anomalia) -> None:
        self.chamadas.append(f"resolvida {anomalia.estado}")


def test_o_contacto_externo_e_informado_quando_a_porta_abre():
    us09.reiniciar()
    contacto = Contacto()
    avisos = Avisos(gravar=lambda a: None, enviar_ws=lambda m: None, contacto=contacto)
    ciclo = Ciclo(
        regras=[us09.verificar],
        avaliar=falsos.avaliar,
        publicar=avisos.publicar,
        obter_contexto=lambda: CONTEXTO,
        registar_historico=lambda d, motivo, agora: None,
    )
    sexta = [(q, l) for q, l in falsos.ler_csv(str(DADOS / "us09.csv")) if q.date() == datetime(2026, 11, 20).date()]
    correr(ciclo, sexta)
    assert contacto.chamadas == ["agendar ativa", "resolvida resolvida"]


def test_resolve_dizendo_quando_a_porta_abriu():
    r = Registo(us09, CONTEXTO).correr("us09.csv")
    assert r.resolucoes == ["a porta abriu às 09:40", "a porta abriu às 10:30", "a porta abriu às 09:30"]


def test_ferias_a_meio_resolvem_com_o_motivo_e_nao_sozinha():
    """A anomalia ativa não se resolve "sozinha": a casa passou a estar vazia."""
    from backend.formatos import Desvio, Leitura, Resolucao

    us09.reiniciar()
    fechada = lambda t: [Leitura("porta", "sensorState", "normal", t)]  # noqa: E731
    sexta = lambda h, m=0: datetime(2026, 11, 20, h, m)  # noqa: E731
    sem_ferias = Contexto([], [], [], False)
    assert us09.verificar(fechada(sexta(8)), sem_ferias, sexta(8)) == []
    [desvio] = us09.verificar(fechada(sexta(9)), sem_ferias, sexta(9))
    assert isinstance(desvio, Desvio)
    ferias = Contexto([Periodo(sexta(9, 5), sexta(23), "férias no Algarve")], [], [], False)
    assert us09.verificar(fechada(sexta(9, 10)), ferias, sexta(9, 10)) == [
        Resolucao("US09", "a casa ficou vazia (férias no Algarve): já não se espera que a porta abra", sexta(9, 10))
    ]
    assert us09.verificar(fechada(sexta(9, 20)), ferias, sexta(9, 20)) == []
