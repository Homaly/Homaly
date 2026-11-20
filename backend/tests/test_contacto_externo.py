"""US05: o contacto externo recebe a SMS quando o responsável não responde a tempo."""

from datetime import timedelta

import pytest

from backend import anomalias, avisos, contacto_externo, definicoes
from backend.avisos import Avisos
from backend.contacto_externo import envios, sms
from backend.contrato import Anomalia, Contacto, Definicoes, TextoEm

from .conftest import AGORA

CONTACTO = Contacto(nome="Vizinha Ana", telemovel="912345678")


@pytest.fixture(autouse=True)
def preparar(monkeypatch):
    enviadas: list[tuple[str, str]] = []
    monkeypatch.setattr(sms, "enviar", lambda para, texto: enviadas.append((para, texto)))
    definicoes.guardar(Definicoes(contacto=CONTACTO, espera_minutos=5, nome_casa="Casa da D. Maria"))
    return enviadas


@pytest.fixture
def enviadas(preparar):
    return preparar


def minuto(m: float):
    return AGORA + timedelta(minutes=m)


def anomalia(classe="seguranca", **campos) -> Anomalia:
    a = Anomalia(
        classe=classe,
        titulo="Alerta de segurança",
        explicacao="A porta da rua está aberta há mais de 5 minutos, desde as 14:55.",
        detetada_em=AGORA,
        **campos,
    )
    anomalias.guardar(a)
    return a


def agendar(a: Anomalia, imediato: bool = False, em=AGORA) -> None:
    contacto_externo.ContactoExterno(agora=lambda: em).agendar(a, imediato=imediato)


def resolver(a: Anomalia, texto: str | None, em) -> Anomalia:
    resolvida = a.model_copy(
        update={"estado": "resolvida", "resolucao": TextoEm(texto=texto, em=em) if texto else None}
    )
    anomalias.guardar(resolvida)
    contacto_externo.ContactoExterno(agora=lambda: em).resolvida(resolvida)
    return resolvida


# Quando sai a SMS


def test_seguranca_sem_resposta_avisa_no_fim_do_tempo_de_espera(enviadas):
    a = anomalia()
    agendar(a)

    contacto_externo.verificar(minuto(4.9))
    assert enviadas == []

    contacto_externo.verificar(minuto(5))
    [(para, texto)] = enviadas
    assert para == "+351912345678"
    linhas = texto.splitlines()
    assert linhas[0] == "Homaly - Casa da D. Maria"
    assert linhas[1] == "Alerta de segurança às 15:00:"
    assert linhas[2] == "A porta da rua está aberta há mais de 5 minutos, desde as 14:55."
    assert len(linhas) == 3  # sem link: a mensagem basta (decisão de 2026-11-20)
    assert "http" not in texto


def test_bem_estar_tambem_chega_ao_contacto(enviadas):
    agendar(anomalia("bem_estar"))
    contacto_externo.verificar(minuto(5))

    assert enviadas[0][1].splitlines()[1] == "Alerta de bem-estar às 15:00:"


@pytest.mark.parametrize("classe", ["eficiencia", "saude_conforto"])
def test_eficiencia_e_saude_nunca_chegam_ao_contacto(enviadas, classe):
    agendar(anomalia(classe))
    contacto_externo.verificar(minuto(60))

    assert enviadas == []


def test_tempo_de_espera_zero_avisa_logo(enviadas):
    definicoes.guardar(Definicoes(contacto=CONTACTO, espera_minutos=0))
    agendar(anomalia())

    contacto_externo.verificar(AGORA)
    assert len(enviadas) == 1


def test_tempo_de_espera_de_trinta_segundos(enviadas):
    definicoes.guardar(Definicoes(contacto=CONTACTO, espera_minutos=0.5))
    agendar(anomalia())

    contacto_externo.verificar(AGORA + timedelta(seconds=29))
    assert enviadas == []

    contacto_externo.verificar(AGORA + timedelta(seconds=30))
    assert len(enviadas) == 1


def test_casa_vazia_avisa_logo_sem_esperar(enviadas):
    agendar(anomalia(), imediato=True)

    contacto_externo.verificar(AGORA)
    assert len(enviadas) == 1


def test_sem_nome_da_casa_a_sms_diz_so_homaly(enviadas):
    definicoes.guardar(Definicoes(contacto=CONTACTO, espera_minutos=0))
    agendar(anomalia())
    contacto_externo.verificar(AGORA)

    assert enviadas[0][1].splitlines()[0] == "Homaly"


def test_so_uma_sms_por_anomalia(enviadas):
    # Ex.: a US12 que passa a segurança volta a chamar agendar.
    a = anomalia()
    agendar(a)
    agendar(a, em=minuto(2))
    contacto_externo.verificar(minuto(5))
    contacto_externo.verificar(minuto(10))

    assert len(enviadas) == 1


def test_passou_a_seguranca_depois_conta_o_tempo_a_partir_dai(enviadas):
    a = anomalia("eficiencia")
    agendar(a)  # eficiência: não agenda
    a = a.model_copy(update={"classe": "seguranca"})
    anomalias.guardar(a)
    agendar(a, em=minuto(3))

    contacto_externo.verificar(minuto(7))
    assert enviadas == []
    contacto_externo.verificar(minuto(8))
    assert len(enviadas) == 1


# Quando não sai


def test_respondeu_a_tempo_nao_avisa(enviadas):
    a = anomalia()
    agendar(a)
    anomalias.guardar(a.model_copy(update={"resposta": TextoEm(texto="fui eu", em=minuto(2))}))

    contacto_externo.verificar(minuto(5))
    assert enviadas == []


def test_resolvida_antes_do_tempo_nao_avisa_nem_manda_resolvido(enviadas):
    a = anomalia()
    agendar(a)
    resolver(a, "a porta fechou às 15:02", minuto(2))

    contacto_externo.verificar(minuto(5))
    assert enviadas == []


def test_cancelar(enviadas):
    a = anomalia()
    agendar(a)
    contacto_externo.ContactoExterno().cancelar(a.id)

    contacto_externo.verificar(minuto(5))
    assert enviadas == []


def test_sem_contacto_nao_avisa(enviadas):
    definicoes.guardar(Definicoes(contacto=None, espera_minutos=5))
    agendar(anomalia())

    contacto_externo.verificar(minuto(5))
    assert enviadas == []


def test_contacto_removido_durante_a_espera_nao_recebe(enviadas):
    agendar(anomalia())
    definicoes.guardar(Definicoes(contacto=None, espera_minutos=5))

    contacto_externo.verificar(minuto(5))
    assert enviadas == []


# A SMS de resolvido


def test_ja_avisado_recebe_a_sms_de_resolvido(enviadas):
    a = anomalia()
    agendar(a)
    contacto_externo.verificar(minuto(5))

    resolver(a, "a porta fechou às 15:12", minuto(12))
    contacto_externo.verificar(minuto(12))

    para, texto = enviadas[1]
    assert para == "+351912345678"
    assert texto.splitlines() == ["Homaly - Casa da D. Maria", "Resolvido às 15:12: a porta fechou às 15:12."]


def test_resolvida_pelo_responsavel_sem_texto(enviadas):
    a = anomalia()
    agendar(a)
    contacto_externo.verificar(minuto(5))

    resolver(a, None, minuto(20))
    contacto_externo.verificar(minuto(20))

    assert enviadas[1][1].splitlines()[1] == "Resolvido às 15:20: o responsável tratou do assunto."


def test_a_sms_de_resolvido_vai_para_quem_recebeu_o_alerta(enviadas):
    a = anomalia()
    agendar(a)
    contacto_externo.verificar(minuto(5))
    definicoes.guardar(Definicoes(contacto=Contacto(nome="Outro", telemovel="961234567"), espera_minutos=5))

    resolver(a, "a porta fechou às 15:12", minuto(12))
    contacto_externo.verificar(minuto(12))

    assert enviadas[1][0] == "+351912345678"


def test_a_sms_de_resolvido_so_sai_uma_vez(enviadas):
    a = anomalia()
    agendar(a)
    contacto_externo.verificar(minuto(5))
    resolver(a, "a porta fechou às 15:12", minuto(12))
    contacto_externo.verificar(minuto(12))
    contacto_externo.verificar(minuto(13))

    assert len(enviadas) == 2


# O textbee falha


def test_textbee_falha_tenta_outra_vez_e_desiste_a_terceira(monkeypatch, enviadas):
    tentativas = []

    def falhar(para, texto):
        tentativas.append(para)
        raise sms.ErroSMS("o textbee respondeu 500")

    monkeypatch.setattr(sms, "enviar", falhar)
    agendar(anomalia())
    # A primeira no fim da espera; depois de 30 s e de mais 60 s.
    for m, esperadas in ((5, 1), (5.4, 1), (5.5, 2), (6.4, 2), (6.5, 3), (30, 3)):
        contacto_externo.verificar(minuto(m))
        assert len(tentativas) == esperadas, m


def test_textbee_volta_a_tempo(monkeypatch, enviadas):
    respostas = iter([sms.ErroSMS("500"), None])

    def enviar(para, texto):
        erro = next(respostas)
        if erro:
            raise erro
        enviadas.append((para, texto))

    monkeypatch.setattr(sms, "enviar", enviar)
    agendar(anomalia())
    contacto_externo.verificar(minuto(5))
    contacto_externo.verificar(minuto(5.5))

    assert len(enviadas) == 1


# Ligação ao resto


def test_os_avisos_reais_usam_o_contacto_externo_real():
    assert isinstance(avisos.reais()._contacto, contacto_externo.ContactoExterno)


def test_a_thread_envia_e_para(enviadas):
    definicoes.guardar(Definicoes(contacto=CONTACTO, espera_minutos=0))
    agendar(anomalia())
    parar = contacto_externo.arrancar(intervalo=0.01, agora=lambda: AGORA)
    try:
        for _ in range(200):
            if enviadas:
                break
            import time

            time.sleep(0.01)
    finally:
        parar()

    assert len(enviadas) == 1


# Revisão: reinício, corridas e falhas


def test_resolvida_depois_de_um_reinicio_manda_a_sms_de_resolvido(enviadas):
    contacto = contacto_externo.ContactoExterno(agora=lambda: AGORA)
    antes = Avisos(gravar=anomalias.guardar, enviar_ws=lambda a: None, contacto=contacto)
    a = anomalia()
    antes.publicar(a)
    contacto_externo.verificar(minuto(5))

    depois = Avisos(gravar=anomalias.guardar, enviar_ws=lambda a: None, contacto=contacto)  # o backend reiniciou
    depois.publicar(a.model_copy(update={"estado": "resolvida", "resolucao": TextoEm(texto="fechou", em=minuto(9))}))
    contacto_externo.verificar(minuto(9))

    assert [t.splitlines()[1] for _, t in enviadas] == ["Alerta de segurança às 15:00:", "Resolvido às 15:09: fechou."]


def test_resolvida_enquanto_a_sms_esta_a_sair_manda_depois_a_de_resolvido(monkeypatch, enviadas):
    a = anomalia()

    def enviar_devagar(para, texto):
        # Enquanto o textbee responde, a porta fecha e o ciclo publica a resolução.
        if not enviadas:
            resolver(a, "a porta fechou às 15:05", minuto(5))
        enviadas.append((para, texto))

    monkeypatch.setattr(sms, "enviar", enviar_devagar)
    agendar(a)
    contacto_externo.verificar(minuto(5))
    contacto_externo.verificar(minuto(5.1))

    assert [t.splitlines()[1] for _, t in enviadas] == [
        "Alerta de segurança às 15:00:",
        "Resolvido às 15:05: a porta fechou às 15:05.",
    ]


def test_no_limite_de_sms_o_alerta_espera_sem_gastar_tentativas(monkeypatch, enviadas):
    a = anomalia()
    agendar(a)
    bloqueado = [True]

    def enviar(para, texto):
        if bloqueado[0]:
            raise sms.LimiteSMS("Chegou-se ao limite de 10 SMS por hora (SMS_MAXIMO_HORA)")
        enviadas.append((para, texto))

    monkeypatch.setattr(sms, "enviar", enviar)
    for m in range(5, 30, 2):  # muito mais vezes do que as 3 tentativas
        contacto_externo.verificar(minuto(m))
    envio = envios.obter(a.id)
    assert (envio.estado, envio.tentativas) == ("pendente", 0)

    bloqueado[0] = False
    contacto_externo.verificar(minuto(31))
    assert len(enviadas) == 1
    assert envios.obter(a.id).estado == "enviada"


def test_no_limite_de_sms_o_resolvido_tambem_espera(monkeypatch, enviadas):
    a = anomalia()
    agendar(a)
    contacto_externo.verificar(minuto(5))  # o alerta saiu
    resolver(a, "a porta fechou às 15:10", minuto(10))
    bloqueado = [True]
    original = sms.enviar

    def enviar(para, texto):
        if bloqueado[0]:
            raise sms.LimiteSMS("limite")
        original(para, texto)

    monkeypatch.setattr(sms, "enviar", enviar)
    for m in range(10, 30, 2):
        contacto_externo.verificar(minuto(m))
    envio = envios.obter(a.id)
    assert (envio.resolvido, envio.tentativas_resolvido) == ("pendente", 0)

    bloqueado[0] = False
    contacto_externo.verificar(minuto(31))
    assert envios.obter(a.id).resolvido == "enviada"
    assert len(enviadas) == 2


def test_resolvida_no_instante_em_que_a_thread_reserva_o_envio_manda_a_de_resolvido(monkeypatch, enviadas):
    # resolvida() lê o envio ainda `pendente`; antes de o cancelar, a thread reserva-o (`a_enviar`)
    # e o alerta sai. Sem cuidado, o cancelamento falhava em silêncio e o resolvido nunca saía.
    a = anomalia()
    agendar(a)
    ainda_pendente = envios.obter(a.id)
    original = envios.obter
    lidos = iter([ainda_pendente])
    monkeypatch.setattr(envios, "obter", lambda i: next(lidos, None) or original(i))
    envios.mudar(a.id, so_se_estado="pendente", estado="a_enviar", codigo="c" * 22)  # a thread reservou

    resolver(a, "a porta fechou às 15:05", minuto(5))
    # A thread acaba de enviar o alerta.
    envios.mudar(a.id, so_se_estado="a_enviar", estado="enviada", telemovel=CONTACTO.telemovel, ultima_sms_em=minuto(5))
    contacto_externo.verificar(minuto(5.1))

    [(_, texto)] = enviadas
    assert texto.splitlines()[1] == "Resolvido às 15:05: a porta fechou às 15:05."


def test_falha_durante_o_envio_com_a_anomalia_resolvida_nao_manda_nada_depois(monkeypatch, enviadas):
    a = anomalia()

    def falhar(para, texto):
        resolver(a, "fechou", minuto(5))
        raise sms.ErroSMS("500")

    monkeypatch.setattr(sms, "enviar", falhar)
    agendar(a)
    contacto_externo.verificar(minuto(5))
    monkeypatch.setattr(sms, "enviar", lambda para, texto: enviadas.append((para, texto)))
    contacto_externo.verificar(minuto(10))

    assert enviadas == []


def test_um_envio_que_rebenta_nao_trava_os_outros(monkeypatch, enviadas):
    estragada = anomalia()
    boa = anomalia()
    agendar(estragada)
    agendar(boa)
    original = contacto_externo.mensagens.alerta

    def alerta(a, nome_casa):
        if a.id == estragada.id:
            raise RuntimeError("um erro inesperado")
        return original(a, nome_casa)

    monkeypatch.setattr(contacto_externo.mensagens, "alerta", alerta)
    contacto_externo.verificar(minuto(5))

    assert len(enviadas) == 1
    assert envios.obter(estragada.id).estado == "falhou"


def test_um_envio_interrompido_volta_a_pendente_ao_arrancar(enviadas):
    a = anomalia()
    agendar(a)
    envios.mudar(a.id, estado="a_enviar")  # o backend caiu a meio do envio

    contacto_externo.recuperar()

    assert envios.obter(a.id).estado == "pendente"
