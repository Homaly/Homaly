from backend.contrato import Veiculo
from backend.ia import visao
from tests.conftest import ModeloFixo

AZUL = Veiculo(id="v1", descricao="Peugeot 206 azul", tipo="carro", cor="azul", matricula="35-19-TA")


def _resposta(**campos):
    base = {"veiculo": True, "tipo": "carro", "cor": "branco", "marca": None, "matricula": None,
            "descricao": "Um carro branco parado na entrada", "conhecido_id": None}
    return {**base, **campos}


def test_veiculo_desconhecido():
    m = ModeloFixo(_resposta(matricula="AA-00-BB"))
    obs = visao.observar(b"jpeg", [AZUL], m)
    assert obs.veiculo and obs.conhecido_id is None
    assert obs.matricula == "AA-00-BB" and obs.cor == "branco"
    assert m.imagens == [b"jpeg"]
    sistema, mensagem = m.chamadas[0]
    assert "v1" in mensagem and "35-19-TA" in mensagem  # a lista de conhecidos vai na mensagem


def test_sem_veiculo():
    obs = visao.observar(b"jpeg", [], ModeloFixo(_resposta(veiculo=False, tipo=None, cor=None)))
    assert obs is not None and not obs.veiculo


def test_matricula_igual_manda_mesmo_que_o_modelo_diga_outra_coisa():
    m = ModeloFixo(_resposta(matricula="35 19 ta", conhecido_id=None))
    assert visao.observar(b"jpeg", [AZUL], m).conhecido_id == "v1"


def test_conhecido_pelo_aspeto_quando_nao_ha_matricula():
    m = ModeloFixo(_resposta(cor="azul", conhecido_id="v1"))
    assert visao.observar(b"jpeg", [AZUL], m).conhecido_id == "v1"


def test_matricula_diferente_ganha_ao_aspeto():
    # O modelo acha que é o azul, mas leu outra matrícula: é outro carro.
    m = ModeloFixo(_resposta(cor="azul", matricula="99-ZZ-99", conhecido_id="v1"))
    assert visao.observar(b"jpeg", [AZUL], m).conhecido_id is None


def test_id_que_nao_existe_e_ignorado():
    assert visao.observar(b"jpeg", [AZUL], ModeloFixo(_resposta(conhecido_id="xpto"))).conhecido_id is None


def test_sem_resposta_do_modelo_da_none():
    assert visao.observar(b"jpeg", [AZUL], ModeloFixo(None)) is None


def test_resposta_mal_formada_da_none():
    assert visao.observar(b"jpeg", [], ModeloFixo({"veiculo": "talvez"})) is None
    assert visao.observar(b"jpeg", [], ModeloFixo({"veiculo": True})) is None  # sem descrição


def test_normalizar_matricula():
    assert visao.normalizar("35-19-ta") == visao.normalizar("35 19 TA") == "3519TA"
    assert visao.normalizar(None) == visao.normalizar("") == ""


def test_descrever_para_registar():
    v = visao.descrever(b"jpeg", ModeloFixo(_resposta(marca="Peugeot 206", cor="azul",
                                                       descricao="Peugeot 206 azul")))
    assert v.descricao == "Peugeot 206 azul" and v.marca == "Peugeot 206"


def test_descrever_sem_veiculo_da_none():
    assert visao.descrever(b"jpeg", ModeloFixo(_resposta(veiculo=False))) is None
