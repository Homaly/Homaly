import pytest

from backend.ia.modelo import obter_modelo


def test_obter_modelo_por_omissao_e_falso(monkeypatch):
    monkeypatch.delenv("IA_FORNECEDOR", raising=False)
    assert obter_modelo().completar_json("s", "m") is None


def test_obter_modelo_desconhecido_falha(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "xpto")
    with pytest.raises(ValueError):
        obter_modelo()


def test_modelo_fixo_importa_de_conftest_e_regista_chamadas():
    from tests.conftest import AGORA, LX, ModeloFixo

    m = ModeloFixo({"a": 1})
    assert m.completar_json("s", "m") == {"a": 1}
    assert m.chamadas == [("s", "m")]
    assert AGORA.tzinfo is LX and AGORA.weekday() == 1
