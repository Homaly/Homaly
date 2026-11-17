from backend.dependencias import obter_modelo_dep


def test_modelo_desconhecido_nao_rebenta_e_fica_sem_modelo(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "xpto")
    assert obter_modelo_dep().completar_json("s", "m") is None
