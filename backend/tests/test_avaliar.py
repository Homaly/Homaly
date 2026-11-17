from datetime import datetime, time, timedelta

from backend.formatos import Contexto, Desvio, Periodo, Rotina, Silencio
from backend.ia import avaliar
from backend.ia.avaliar import registar_us, us_da_anomalia
from tests.conftest import AGORA, ModeloFixo

CONTEXTO_VAZIO = Contexto([], [], [], False)


def desvio(**campos) -> Desvio:
    base = dict(us="US08", classe="seguranca", resumo="A porta está aberta.", habitual=None)
    return Desvio(**{**base, **campos})


def com_silencio(silencio: Silencio) -> Contexto:
    return Contexto([], [], [silencio], False)


def test_modelo_decide_avisar():
    modelo = ModeloFixo({"avisar": True, "titulo": "Porta aberta", "explicacao": "x", "acao": None})
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=modelo)
    assert a is not None
    assert a.titulo == "Porta aberta"
    assert a.explicacao == "x"
    assert a.acao_proposta is None
    assert a.estado == "ativa"
    assert a.detetada_em == AGORA
    assert us_da_anomalia(a.id) == "US08"


def test_modelo_decide_nao_avisar():
    modelo = ModeloFixo({"avisar": False, "titulo": "T", "explicacao": "E", "acao": None})
    assert avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=modelo) is None


def test_imediato_avisa_mesmo_que_modelo_diga_que_nao():
    modelo = ModeloFixo({"avisar": False, "titulo": "T", "explicacao": "E"})
    a = avaliar(desvio(imediato=True), CONTEXTO_VAZIO, agora=AGORA, modelo=modelo)
    assert a is not None
    assert a.titulo == "T"


def test_sem_modelo_usa_resumo():
    d = desvio(classe="eficiencia", resumo="Luz acesa há 5 h.", habitual="Costuma estar acesa 1 h.")
    a = avaliar(d, CONTEXTO_VAZIO, agora=AGORA, modelo=ModeloFixo(None))
    assert a is not None
    assert a.titulo == "Energia a mais"
    assert a.explicacao == "Luz acesa há 5 h. Habitual: Costuma estar acesa 1 h."
    assert a.acao_proposta is None


def test_resposta_malformada_usa_resumo():
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=ModeloFixo({"avisar": "sim"}))
    assert a is not None
    assert a.titulo == "Alerta de segurança"
    assert a.explicacao == "A porta está aberta."


def test_resposta_que_nao_e_dicionario_usa_resumo():
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=ModeloFixo(["lixo"]))  # type: ignore[arg-type]
    assert a is not None
    assert a.titulo == "Alerta de segurança"


def test_titulo_so_com_espacos_e_invalido():
    resposta = {"avisar": False, "titulo": "   ", "explicacao": "E", "acao": None}
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=ModeloFixo(resposta))
    assert a is not None  # inválida: recurso, e avisa sempre
    assert a.titulo == "Alerta de segurança"


def test_acao_proposta():
    resposta = {"avisar": True, "titulo": "T", "explicacao": "E", "acao": "Apagar a lâmpada"}
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=ModeloFixo(resposta))
    assert a is not None
    assert a.acao_proposta is not None
    assert a.acao_proposta.descricao == "Apagar a lâmpada"


def test_acao_vazia_nao_propoe_nada():
    resposta = {"avisar": True, "titulo": "T", "explicacao": "E", "acao": ""}
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=ModeloFixo(resposta))
    assert a is not None
    assert a.acao_proposta is None


def test_silencio_ativo_cala_sem_chamar_modelo():
    modelo = ModeloFixo(None)
    contexto = com_silencio(Silencio("US08", AGORA + timedelta(hours=1), "m"))
    assert avaliar(desvio(), contexto, agora=AGORA, modelo=modelo) is None
    assert modelo.chamadas == []


def test_silencio_permanente_cala():
    contexto = com_silencio(Silencio("US08", None, "m"))
    assert avaliar(desvio(), contexto, agora=AGORA, modelo=ModeloFixo(None)) is None


def test_silencio_expirado_nao_cala():
    contexto = com_silencio(Silencio("US08", AGORA - timedelta(minutes=1), "m"))
    assert avaliar(desvio(), contexto, agora=AGORA, modelo=ModeloFixo(None)) is not None


def test_silencio_de_outra_us_nao_cala():
    contexto = com_silencio(Silencio("US10", None, "m"))
    assert avaliar(desvio(), contexto, agora=AGORA, modelo=ModeloFixo(None)) is not None


def test_mensagem_leva_desvio_contexto_e_agora():
    modelo = ModeloFixo(None)
    d = desvio(resumo="Resumo único.", habitual="Habitual único.")
    ferias = [Periodo(AGORA, AGORA + timedelta(days=7), "praia")]
    rotinas = [Rotina("a empregada vem", [1], time(9, 0))]
    avaliar(d, Contexto(ferias, rotinas, [], True, "ferro"), agora=AGORA, modelo=modelo)
    (_, mensagem), = modelo.chamadas
    assert "Resumo único." in mensagem
    assert "Habitual único." in mensagem
    assert "ferro" in mensagem
    assert "praia" in mensagem
    assert "a empregada vem" in mensagem
    assert AGORA.isoformat() in mensagem


def test_fornecedor_desconhecido_usa_resumo(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "xpto")
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA)
    assert a is not None
    assert a.titulo == "Alerta de segurança"


def test_silencio_com_fim_sem_fuso_cala():
    contexto = com_silencio(Silencio("US08", datetime(2030, 1, 1), "m"))
    assert avaliar(desvio(), contexto, agora=AGORA, modelo=ModeloFixo(None)) is None


def test_us_desconhecida():
    assert us_da_anomalia("nao-existe") is None


def test_agora_sem_fuso_nao_rebenta():
    contexto = com_silencio(Silencio("US08", AGORA + timedelta(days=1), "m"))
    naive = datetime(2026, 11, 17, 15, 0)
    assert avaliar(desvio(), contexto, agora=naive, modelo=ModeloFixo(None)) is None


def test_acao_so_espacos_e_sem_acao():
    modelo = ModeloFixo({"avisar": True, "titulo": "T", "explicacao": "E", "acao": "   "})
    a = avaliar(desvio(), CONTEXTO_VAZIO, agora=AGORA, modelo=modelo)
    assert a is not None
    assert a.acao_proposta is None


def test_registar_us():
    registar_us("x", "US09")
    assert us_da_anomalia("x") == "US09"
