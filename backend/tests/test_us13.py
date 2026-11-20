"""US13: veículo desconhecido na entrada (a regra, com a câmara e a visão a fingir)."""

from concurrent.futures import Future
from datetime import datetime, timedelta

import pytest

from backend.ciclo import Ciclo
from backend.contrato import Anomalia
from backend.formatos import Contexto, Leitura, Periodo
from backend.ia.visao import Observacao
from backend.regras import us13
from tests.conftest import AGORA

SEM_NADA = Contexto([], [], [], False)
DESCONHECIDO = us13.Visto("/imagens/a.jpg", Observacao(
    veiculo=True, descricao="Um carro branco", tipo="carro", cor="branco", matricula="AA-00-BB"))
CONHECIDO = us13.Visto("", Observacao(veiculo=True, descricao="O Peugeot", conhecido_id="v1"))
NADA = us13.Visto("", Observacao(veiculo=False, descricao="A entrada vazia"))


def _ja(funcao) -> Future:
    """Corre já, como o executor faria noutra thread, e guarda o resultado ou a exceção."""
    f = Future()
    try:
        f.set_result(funcao())
    except Exception as erro:
        f.set_exception(erro)
    return f


class Camara:
    """O que a regra vê: o contador do detetor e o que cada observação devolve, por ordem."""

    def __init__(self, *vistos):
        self.vistos = list(vistos)
        self.movimentos = 0
        self.observacoes = 0

    def observar(self):
        self.observacoes += 1
        return self.vistos.pop(0) if self.vistos else NADA


@pytest.fixture
def camara(monkeypatch):
    c = Camara()
    us13.reiniciar()
    monkeypatch.setattr(us13, "observar", c.observar)
    monkeypatch.setattr(us13, "submeter", _ja)
    monkeypatch.setattr(us13, "contar_movimentos", lambda: c.movimentos)
    monkeypatch.delenv("VEICULO_MINUTOS", raising=False)
    monkeypatch.delenv("VEICULO_PAUSA_MINUTOS", raising=False)
    yield c
    us13.reiniciar()


def _volta(minutos: float, contexto=SEM_NADA, leituras=()):
    return us13.verificar(list(leituras), contexto, AGORA + timedelta(minutes=minutos))


def _movimento(camara):
    camara.movimentos += 1


def test_sem_movimento_nao_olha(camara):
    for m in range(5):
        assert _volta(m) == []
    assert camara.observacoes == 0


def test_desconhecido_que_fica_dois_minutos_avisa_com_a_imagem(camara):
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    _volta(0)  # o detetor arranca: ponto de partida
    _movimento(camara)
    assert _volta(0.1) == []  # pede a primeira observação
    assert _volta(0.2) == []  # desconhecido: espera dois minutos
    assert _volta(1.5) == []
    assert _volta(2.2) == []  # pede a segunda observação
    (desvio,) = _volta(2.3)
    assert desvio.us == "US13" and desvio.classe == "seguranca"
    assert desvio.imagem == "/imagens/a.jpg"
    assert "carro branco" in desvio.resumo and "AA-00-BB" in desvio.resumo
    assert f"{(AGORA + timedelta(minutes=0.1)):%H:%M}" in desvio.resumo
    assert not desvio.imediato
    assert camara.observacoes == 2


def test_conhecido_nao_avisa(camara):
    camara.vistos = [CONHECIDO]
    _volta(0)
    _movimento(camara)
    for m in (0.1, 0.2, 3, 4):
        assert _volta(m) == []
    assert camara.observacoes == 1


def test_saiu_antes_dos_dois_minutos_nao_avisa(camara):
    camara.vistos = [DESCONHECIDO, NADA]
    _volta(0)
    _movimento(camara)
    for m in (0.1, 0.2, 2.2, 2.3, 3):
        assert _volta(m) == []
    assert camara.observacoes == 2


def test_motion_detected_da_camara_exterior_tambem_dispara(camara, casa):
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    leitura = lambda v: [Leitura("camara", "motionDetected", v, AGORA, "cam-rua")]
    assert _volta(0, leituras=leitura("")) == []  # primeira leitura: ponto de partida
    assert camara.observacoes == 0
    _volta(0.1, leituras=leitura("1795128823805"))
    assert camara.observacoes == 1


def test_motion_detected_de_uma_camara_de_dentro_nao_conta(camara, casa):
    _volta(0, leituras=[Leitura("camara", "motionDetected", "", AGORA, "cam-sala")])
    _volta(1, leituras=[Leitura("camara", "motionDetected", "123", AGORA, "cam-sala")])
    assert camara.observacoes == 0


def test_motion_detected_igual_nao_dispara(camara):
    leitura = [Leitura("camara", "motionDetected", "", AGORA)]
    for m in range(4):
        _volta(m, leituras=leitura)
    assert camara.observacoes == 0


def test_pausa_depois_de_avisar(camara):
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    _volta(0)
    _movimento(camara)
    _volta(0.1), _volta(0.2), _volta(2.2)
    assert len(_volta(2.3)) == 1
    _movimento(camara)
    _volta(5)  # dentro da pausa de 30 minutos: não olha
    assert camara.observacoes == 2
    _movimento(camara)
    _volta(40)
    assert camara.observacoes == 3


def test_movimento_enquanto_espera_nao_pede_outra_observacao(camara):
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    _volta(0)
    _movimento(camara)
    _volta(0.1), _volta(0.2)
    _movimento(camara)
    _volta(1)
    assert camara.observacoes == 1


def test_casa_vazia_e_imediato(camara):
    ferias = Contexto([Periodo(AGORA - timedelta(days=1), AGORA + timedelta(days=5), "férias")], [], [], False)
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    _volta(0, ferias)
    _movimento(camara)
    _volta(0.1, ferias), _volta(0.2, ferias), _volta(2.2, ferias)
    (desvio,) = _volta(2.3, ferias)
    assert desvio.imediato


def test_observacao_que_falha_volta_ao_inicio(camara, monkeypatch):
    def rebenta():
        raise RuntimeError("ffmpeg morreu")

    monkeypatch.setattr(us13, "observar", rebenta)
    _volta(0)
    _movimento(camara)
    _volta(0.1)
    assert _volta(0.2) == []
    monkeypatch.setattr(us13, "observar", camara.observar)
    camara.vistos = [DESCONHECIDO]
    _movimento(camara)
    _volta(0.3)
    assert camara.observacoes == 1


def test_minutos_configuraveis(camara, monkeypatch):
    monkeypatch.setenv("VEICULO_MINUTOS", "0.5")
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    _volta(0)
    _movimento(camara)
    _volta(0.1), _volta(0.2), _volta(0.7)
    assert len(_volta(0.8)) == 1


def test_no_ciclo_a_anomalia_leva_a_imagem_e_so_se_resolve_com_resposta(camara):
    camara.vistos = [DESCONHECIDO, DESCONHECIDO]
    publicadas: list[Anomalia] = []

    def avaliar(desvio, contexto):
        return Anomalia(classe=desvio.classe, titulo="Veículo", explicacao=desvio.resumo, detetada_em=AGORA)

    ciclo = Ciclo(regras=[us13.verificar], avaliar=avaliar,
                  publicar=lambda a, imediato=False: publicadas.append(a),
                  obter_contexto=lambda: SEM_NADA, registar_historico=lambda d, m, a: None)
    ciclo.passo([], AGORA)
    _movimento(camara)
    for m in (0.1, 0.2, 2.2, 2.3, 3, 10):
        ciclo.passo([], AGORA + timedelta(minutes=m))
    (anomalia,) = publicadas
    assert anomalia.imagem_url == "/imagens/a.jpg"
    assert anomalia.estado == "ativa"
