"""Os casos de dados/us09.csv e os casos diretos da regra dos sinais de vida."""

from datetime import datetime

import pytest

from backend import db, falsos, habitual, sinais
from backend.avisos import Avisos
from backend.ciclo import Ciclo, correr
from backend.contrato import Anomalia
from backend.formatos import Contexto, Desvio, Leitura, Periodo, Resolucao
from backend.regras import us09
from tests.regras_casa import DADOS, Registo

FERIAS = Periodo(datetime(2026, 11, 23), datetime(2026, 11, 29, 23, 59), "férias no Algarve")
CONTEXTO = Contexto(ferias=[FERIAS], rotinas=[], silencios=[], casa_vazia=False)
SEM_FERIAS = Contexto([], [], [], False)


@pytest.fixture(autouse=True)
def lacuna_de_um_dia(monkeypatch):
    """O CSV tem voltas espaçadas de horas: sem isto, cada uma seria um buraco nas leituras."""
    monkeypatch.setenv("US09_LACUNA_MINUTOS", "1440")
    us09.reiniciar()


def sexta(h: int, m: int = 0) -> datetime:
    return datetime(2026, 11, 20, h, m)


def sabado(h: int, m: int = 0) -> datetime:
    return datetime(2026, 11, 21, h, m)


def porta_fechada(t: datetime) -> list[Leitura]:
    return [Leitura("porta", "sensorState", "normal", t)]


def camara(valor: str, t: datetime) -> list[Leitura]:
    return [Leitura("camara", "motionDetected", valor, t)] + porta_fechada(t)


def lampada(valor: str, t: datetime) -> list[Leitura]:
    return [Leitura("lampada", "power", valor, t)] + porta_fechada(t)


def voltas(*horas: datetime, contexto: Contexto = SEM_FERIAS) -> list[Desvio | Resolucao]:
    """Uma volta só com a porta fechada a cada hora; devolve a saída da última."""
    saida: list[Desvio | Resolucao] = []
    for t in horas:
        saida = us09.verificar(porta_fechada(t), contexto, t)
    return saida


# Os casos do CSV: quinta normal, sexta com os dois casos, sábado que sai pela porta, segunda das férias.


def test_casos_da_us09():
    r = Registo(us09, CONTEXTO).correr("us09.csv")
    assert [q for q, _ in r.avaliados] == [datetime(2026, 11, 20, 8, 45), datetime(2026, 11, 20, 22, 30)]
    assert all(d.classe == "bem_estar" and not d.imediato for _, d in r.avaliados)
    assert r.publicadas == [
        (datetime(2026, 11, 20, 8, 45), "ativa", "bem_estar"),
        (datetime(2026, 11, 20, 11, 5), "resolvida", "bem_estar"),
        (datetime(2026, 11, 20, 22, 30), "ativa", "bem_estar"),  # atravessa a meia-noite
        (datetime(2026, 11, 21, 7, 50), "resolvida", "bem_estar"),
    ]
    assert r.resolucoes == ["movimento na câmara às 11:05", "a luz ligada às 07:50"]


def test_resumo_e_habitual():
    r = Registo(us09, CONTEXTO).correr("us09.csv")
    manha, parou = r.avaliados[0][1], r.avaliados[1][1]
    assert manha.resumo == ("Ainda não houve nenhum sinal de vida hoje até às 08:45. "
                            "O último foi a luz desligada às 23:40 de ontem.")
    assert manha.habitual == "Nos dias úteis, o primeiro sinal de vida costuma chegar até às 07:15."
    assert parou.resumo == ("O último sinal de vida foi movimento na câmara às 19:30 e, desde então, "
                            "passaram 3 h sem nenhum, a horas em que costuma haver atividade.")
    assert parou.habitual == habitual.padrao().texto_atividade(datetime(2026, 11, 20, 22, 30))


def test_sem_ferias_avisa_e_diz_o_ultimo_sinal_de_outro_dia():
    r = Registo(us09, Contexto([], [], [], False)).correr("us09.csv")
    assert [q for q, _ in r.avaliados][2:] == [datetime(2026, 11, 23, 8, 45)]
    assert r.avaliados[2][1].resumo.endswith("O último foi a porta aberta às 10:00 de 21/11.")
    assert r.publicadas[4:] == [(datetime(2026, 11, 23, 8, 45), "ativa", "bem_estar")]


def test_casa_vazia_nao_avisa():
    assert Registo(us09, Contexto([], [], [], casa_vazia=True)).correr("us09.csv").avaliados == []


class Contacto:
    def __init__(self):
        self.chamadas: list[str] = []

    def agendar(self, anomalia: Anomalia, imediato: bool = False) -> None:
        self.chamadas.append(f"agendar {anomalia.estado}")

    def cancelar(self, anomalia_id: str) -> None:
        self.chamadas.append("cancelar")

    def resolvida(self, anomalia: Anomalia) -> None:
        self.chamadas.append(f"resolvida {anomalia.estado}")


def test_o_contacto_externo_e_informado_quando_ha_um_sinal():
    contacto = Contacto()
    avisos = Avisos(gravar=lambda a: None, enviar_ws=lambda m: None, contacto=contacto)
    ciclo = Ciclo(
        regras=[us09.verificar],
        avaliar=falsos.avaliar,
        publicar=avisos.publicar,
        obter_contexto=lambda: CONTEXTO,
        registar_historico=lambda d, motivo, agora: None,
    )
    # Até sexta às 11:05: o aviso da manhã e o movimento que o resolve. A quinta vai junto para a
    # câmara ter uma leitura anterior (sem ela, o movimento das 11:05 seria o ponto de partida).
    ate_as_11 = [(q, l) for q, l in falsos.ler_csv(str(DADOS / "us09.csv")) if q <= sexta(11, 5)]
    correr(ciclo, ate_as_11)
    assert contacto.chamadas == ["agendar ativa", "resolvida resolvida"]


# Casos diretos: numa sexta, 2026-11-20, sem férias.


def test_arranque_depois_da_hora_habitual_nao_avisa_de_manha():
    assert us09.verificar(porta_fechada(sexta(9)), SEM_FERIAS, sexta(9)) == []


def test_porta_e_camara_na_mesma_volta_o_ultimo_sinal_e_a_porta():
    # A ordem do MCP põe a câmara depois da porta: quem abriu a porta pode ter saído.
    sab = lambda h, m=0: datetime(2026, 11, 21, h, m)  # noqa: E731
    assert us09.verificar(camara("antes", sab(9, 50)), SEM_FERIAS, sab(9, 50)) == []
    volta = [
        Leitura("porta", "sensorState", "alarm", sab(10)),
        Leitura("camara", "motionDetected", "movimento", sab(10)),
    ]
    assert us09.verificar(volta, SEM_FERIAS, sab(10)) == []
    assert us09._carregar().ultimo.dispositivo == "porta"
    saidas = []
    for h in range(11, 15):
        saidas += us09.verificar(
            [Leitura("camara", "motionDetected", "movimento", sab(h))] + porta_fechada(sab(h)), SEM_FERIAS, sab(h)
        )
    assert saidas == []


def test_tem_pendente():
    assert us09.tem_pendente() is False
    [desvio] = voltas(sexta(6), sexta(8, 45))
    assert us09.tem_pendente() is True


def test_um_buraco_nas_leituras_de_manha_nao_avisa(monkeypatch):
    monkeypatch.setenv("US09_LACUNA_MINUTOS", "30")
    assert us09.verificar(porta_fechada(sexta(6)), SEM_FERIAS, sexta(6)) == []
    assert us09.verificar(porta_fechada(sexta(9)), SEM_FERIAS, sexta(9)) == []  # 3 h sem ler


def test_um_buraco_nao_conta_como_silencio(monkeypatch):
    monkeypatch.setenv("US09_LACUNA_MINUTOS", "30")
    assert us09.verificar(camara("", sexta(18, 50)), SEM_FERIAS, sexta(18, 50)) == []
    assert us09.verificar(camara("2026-11-20T19:00:00", sexta(19)), SEM_FERIAS, sexta(19)) == []
    assert voltas(sexta(19, 10)) == []
    # Buraco das 19:10 às 21:50: o que aconteceu nele não se sabe.
    assert voltas(sexta(22)) == []
    assert voltas(sexta(22, 10)) == []  # sem o buraco seriam 3 h 10 min de silêncio


def test_sem_nenhum_dispositivo_a_comunicar_nao_avisa():
    temperatura = lambda t: [Leitura("temperatura", "temperatureValue", 19.5, t)]  # noqa: E731
    assert voltas(sexta(6), sexta(8)) == []
    assert us09.verificar(temperatura(sexta(8, 45)), SEM_FERIAS, sexta(8, 45)) == []

    [desvio] = voltas(sexta(8, 50))
    assert isinstance(desvio, Desvio)
    # Com o desvio já ativo, uma volta sem sinais de vida possíveis não o resolve.
    assert us09.verificar(temperatura(sexta(9)), SEM_FERIAS, sexta(9)) == [desvio]


def test_com_a_camara_calada_continua_a_vigiar():
    [desvio] = voltas(sexta(6), sexta(7), sexta(8), sexta(8, 45))
    assert desvio == Desvio(
        us="US09",
        classe="bem_estar",
        resumo="Ainda não houve nenhum sinal de vida hoje até às 08:45.",
        habitual="Nos dias úteis, o primeiro sinal de vida costuma chegar até às 07:15.",
    )


def test_deitar_depois_da_meia_noite_nao_e_atividade_parada():
    saidas = us09.verificar(camara("", sexta(22, 50)) + lampada("on", sexta(22, 50)), SEM_FERIAS, sexta(22, 50))
    saidas += us09.verificar(camara("2026-11-20T23:00:00", sexta(23)), SEM_FERIAS, sexta(23))
    saidas += us09.verificar(lampada("off", sabado(0, 30)), SEM_FERIAS, sabado(0, 30))
    for h in range(1, 8):
        saidas += voltas(sabado(h))
    assert saidas == []


def test_a_casa_apagar_a_luz_nao_resolve(monkeypatch):
    monkeypatch.setattr(us09.dispositivos, "comandado_ha_pouco", lambda d, t: (d, t) == ("lampada", "power"))
    assert us09.verificar(lampada("on", sexta(6)), SEM_FERIAS, sexta(6)) == []  # volta de partida
    [desvio] = us09.verificar(lampada("on", sexta(8, 45)), SEM_FERIAS, sexta(8, 45))
    assert isinstance(desvio, Desvio)
    assert us09.verificar(lampada("off", sexta(9)), SEM_FERIAS, sexta(9)) == [desvio]


def test_ferias_a_meio_resolvem_com_o_motivo():
    [desvio] = voltas(sexta(6), sexta(8, 45))
    assert isinstance(desvio, Desvio)
    ferias = Contexto([Periodo(sexta(9, 5), sexta(23), "férias no Algarve")], [], [], False)
    assert voltas(sexta(9, 10), contexto=ferias) == [
        Resolucao("US09", "a casa ficou vazia (férias no Algarve): já não se espera atividade", sexta(9, 10))
    ]
    assert voltas(sexta(9, 20), contexto=ferias) == []


def test_casa_vazia_sem_motivo_resolve_sem_parenteses():
    voltas(sexta(6), sexta(8, 45))
    assert voltas(sexta(9), contexto=Contexto([], [], [], casa_vazia=True)) == [
        Resolucao("US09", "a casa ficou vazia: já não se espera atividade", sexta(9))
    ]


def test_o_estado_sobrevive_a_um_reinicio():
    assert us09.verificar(lampada("off", sexta(6)), SEM_FERIAS, sexta(6)) == []
    [desvio] = voltas(sexta(8, 45))
    assert isinstance(desvio, Desvio)

    us09._detetor = sinais.Detetor()  # um processo novo: só o que está em SQLite sobrevive
    assert us09.verificar(lampada("off", sexta(9)), SEM_FERIAS, sexta(9)) == [desvio]
    # A volta das 09:00 foi o ponto de partida: a luz a ligar já é um sinal.
    assert us09.verificar(lampada("on", sexta(9, 5)), SEM_FERIAS, sexta(9, 5)) == [
        Resolucao("US09", "a luz ligada às 09:05", sexta(9, 5))
    ]


def test_um_estado_do_futuro_e_esquecido():
    quarta = lambda h, m=0: datetime(2026, 11, 25, h, m)  # noqa: E731
    [desvio] = voltas(quarta(6), quarta(8, 45))
    assert isinstance(desvio, Desvio)

    assert voltas(sexta(6)) == []
    assert us09._carregar().pendente is None


def test_depois_de_um_reinicio_a_primeira_volta_e_um_buraco():
    # Às 07:00 a luz estava apagada; o backend reinicia (um deploy) e a luz acende entretanto.
    # Esse sinal perdeu-se: a casa não pode dizer que viu a manhã toda sem sinais.
    assert us09.verificar(lampada("off", sexta(6)), SEM_FERIAS, sexta(6)) == []
    assert us09.verificar(lampada("off", sexta(7)), SEM_FERIAS, sexta(7)) == []

    us09._detetor = sinais.Detetor()  # um processo novo
    saidas = []
    for t in (sexta(7, 20), sexta(7, 40), sexta(8), sexta(8, 20), sexta(8, 45)):
        saidas += us09.verificar(lampada("on", t), SEM_FERIAS, t)
    assert saidas == []


@pytest.mark.parametrize("dados", [
    "isto não é JSON",
    "{}",  # faltam as chaves
    "[]",
    '{"ultimo": null, "vigia_desde": 5, "lida_em": null, "pendente": null}',  # tipo errado
    '{"ultimo": {"dispositivo": "porta"}, "vigia_desde": null, "lida_em": null, "pendente": null}',
])
def test_um_estado_estragado_nao_para_o_ciclo(dados, caplog):
    with db.ligar() as con:
        con.execute("INSERT OR REPLACE INTO estado_us09 (id, dados) VALUES (1, ?)", (dados,))
    assert us09.verificar(porta_fechada(sexta(6)), SEM_FERIAS, sexta(6)) == []
    assert "estado_us09" in caplog.text
    assert us09._carregar().lida_em is not None  # a volta gravou um estado novo
