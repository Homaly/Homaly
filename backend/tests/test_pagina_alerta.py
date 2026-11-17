"""US05: a página do alerta que o contacto externo abre a partir da SMS (GET /a/{codigo})."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend import anomalias, contacto_externo, definicoes
from backend.contacto_externo import pagina, sms
from backend.contrato import Anomalia, Contacto, Definicoes, TextoEm
from backend.main import app

from .conftest import AGORA

api = TestClient(app)


@pytest.fixture(autouse=True)
def preparar(monkeypatch):
    monkeypatch.setenv("HOMALY_URL_PUBLICO", "http://casa.exemplo")
    enviadas: list[str] = []
    monkeypatch.setattr(sms, "enviar", lambda para, texto: enviadas.append(texto))
    definicoes.guardar(
        Definicoes(contacto=Contacto(nome="Ana", telemovel="912345678"), espera_minutos=0, nome_casa="Casa da D. Maria")
    )
    return enviadas


def com_alerta(enviadas, explicacao="A porta da rua está aberta há mais de 5 minutos, desde as 14:55.") -> tuple[Anomalia, str]:
    """Uma anomalia de segurança já enviada por SMS; devolve-a e o caminho do link."""
    a = Anomalia(classe="seguranca", titulo="Porta aberta", explicacao=explicacao, detetada_em=AGORA)
    anomalias.guardar(a)
    contacto_externo.ContactoExterno(agora=lambda: AGORA).agendar(a)
    contacto_externo.verificar(AGORA)
    link = enviadas[-1].splitlines()[-1].removeprefix("Ver: http://casa.exemplo")
    return a, link


def pedir(link: str, em):
    pagina.agora = lambda: em
    try:
        return api.get(link)
    finally:
        pagina.agora = pagina._agora_real


def test_mostra_o_alerta_ainda_por_resolver(preparar):
    _, link = com_alerta(preparar)

    r = pedir(link, AGORA + timedelta(minutes=2))

    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    for texto in ("Casa da D. Maria", "Porta aberta", "Segurança", "A porta da rua está aberta", "Ainda por resolver", "15:00"):
        assert texto in r.text
    assert 'http-equiv="refresh"' in r.text  # atualiza-se sozinha enquanto está ativo


def test_mostra_que_esta_resolvido_e_como(preparar):
    a, link = com_alerta(preparar)
    anomalias.guardar(
        a.model_copy(update={"estado": "resolvida", "resolucao": TextoEm(texto="a porta fechou às 15:12", em=AGORA + timedelta(minutes=12))})
    )

    r = pedir(link, AGORA + timedelta(hours=1))

    assert "Resolvido às 15:12" in r.text
    assert "a porta fechou às 15:12" in r.text
    assert "Ainda por resolver" not in r.text
    assert 'http-equiv="refresh"' not in r.text


def test_expira_24_horas_depois_da_sms(preparar):
    _, link = com_alerta(preparar)

    assert "Porta aberta" in pedir(link, AGORA + timedelta(hours=23, minutes=59)).text
    r = pedir(link, AGORA + timedelta(hours=24, minutes=1))
    assert r.status_code == 410
    assert "expirou" in r.text
    assert "Porta aberta" not in r.text


def test_a_sms_de_resolvido_renova_as_24_horas(preparar):
    a, link = com_alerta(preparar)
    resolvida = a.model_copy(update={"estado": "resolvida", "resolucao": TextoEm(texto="fechou", em=AGORA + timedelta(hours=20))})
    anomalias.guardar(resolvida)
    contacto_externo.ContactoExterno(agora=lambda: AGORA + timedelta(hours=20)).resolvida(resolvida)
    contacto_externo.verificar(AGORA + timedelta(hours=20))

    assert pedir(link, AGORA + timedelta(hours=30)).status_code == 200


def test_codigo_desconhecido(preparar):
    r = pedir("/a/nao-existe", AGORA)

    assert r.status_code == 404
    assert "não existe" in r.text


def test_o_codigo_e_longo_e_nao_e_o_id_da_anomalia(preparar):
    a, link = com_alerta(preparar)
    codigo = link.removeprefix("/a/")

    assert len(codigo) >= 20
    assert a.id not in link
    assert pedir(f"/a/{a.id}", AGORA).status_code == 404


def test_o_texto_e_escapado(preparar):
    _, link = com_alerta(preparar, explicacao="<script>alert(1)</script>")

    r = pedir(link, AGORA)

    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text


def test_nao_fica_em_cache_nem_em_motores_de_busca(preparar):
    _, link = com_alerta(preparar)

    r = pedir(link, AGORA)

    assert "no-store" in r.headers["cache-control"]
    assert "noindex" in r.headers["x-robots-tag"]
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["content-security-policy"] == "default-src 'none'; style-src 'unsafe-inline'"
    assert r.headers["x-content-type-options"] == "nosniff"
