"""Os cenários do ciclo decididos a 2026-11-17."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from backend.avisos import Avisos
from backend.ciclo import Ciclo
from backend.contrato import Anomalia, TextoEm
from backend.formatos import Contexto, Desvio, Resolucao, Silencio

T0 = datetime(2026, 11, 17, 3, 10)


def minuto(n: int) -> datetime:
    return T0 + timedelta(minutes=n)


class Casa:
    """Um ciclo com peças falsas que registam o que lhes pedem."""

    def __init__(self, ia_avisa: bool = True, silencios: list[Silencio] | None = None):
        self.desvios: list[Desvio] = []  # o que as regras veem neste passo
        self.ia_avisa = ia_avisa
        self.silencios = silencios or []
        self.chamadas_ia: list[str] = []
        self.publicadas: list[tuple[str, str, str]] = []  # (estado, classe, explicacao)
        self.historico: list[tuple[str, str]] = []
        self.ciclo = Ciclo(
            regras=[lambda leituras, contexto, agora: list(self.desvios)],
            avaliar=self._avaliar,
            publicar=self._publicar,
            obter_contexto=lambda: Contexto([], [], self.silencios, False),
            registar_historico=lambda d, motivo, agora: self.historico.append((d.us, motivo)),
        )
        self.ultima: Anomalia | None = None

    def _avaliar(self, desvio: Desvio, contexto: Contexto) -> Anomalia | None:
        self.chamadas_ia.append(desvio.us)
        if not self.ia_avisa:
            return None
        return Anomalia(id=f"a{len(self.chamadas_ia)}", classe=desvio.classe, titulo="t",
                        explicacao=desvio.resumo, detetada_em=datetime.now())

    def _publicar(self, anomalia: Anomalia, imediato: bool = False) -> None:
        self.ultima = anomalia
        self.publicadas.append((anomalia.estado, anomalia.classe, anomalia.explicacao))

    def passo(self, n: int, *desvios: Desvio) -> None:
        self.desvios = list(desvios)
        self.ciclo.passo([], minuto(n))


def desvio(us="US08", classe="seguranca", resumo="porta aberta há 5 minutos"):
    return Desvio(us=us, classe=classe, resumo=resumo, habitual=None)


def test_ia_avalia_uma_vez_por_ocorrencia_e_avisa_uma_vez():
    casa = Casa()
    for n in range(3):
        casa.passo(n, desvio())
    assert casa.chamadas_ia == ["US08"]
    assert casa.publicadas == [("ativa", "seguranca", "porta aberta há 5 minutos")]
    assert casa.ultima.detetada_em == minuto(0)


def test_ignorada_pela_ia_fica_no_historico_e_nao_volta_a_ia():
    casa = Casa(ia_avisa=False)
    for n in range(3):
        casa.passo(n, desvio("US07"))
    assert casa.chamadas_ia == ["US07"]
    assert casa.historico == [("US07", "a IA decidiu não avisar")]
    assert casa.publicadas == []


def test_exemplo_do_vila_us07_ignorada_e_us08_avisa_aos_5_minutos():
    casa = Casa()
    casa.ia_avisa = False
    casa.passo(0, desvio("US07"))
    casa.ia_avisa = True
    casa.passo(5, desvio("US07"), desvio("US08"))
    assert casa.chamadas_ia == ["US07", "US08"]
    assert len(casa.publicadas) == 1


def test_ocorrencia_ignorada_que_volta_e_nova():
    casa = Casa(ia_avisa=False)
    casa.passo(0, desvio("US07"))
    casa.passo(1)
    casa.passo(2, desvio("US07"))
    assert casa.chamadas_ia == ["US07", "US07"]


def test_silenciada_nao_vai_a_ia_mas_fica_no_historico():
    casa = Casa(silencios=[Silencio(us="US11", ate=minuto(60), motivo="visita")])
    casa.passo(0, desvio("US11", classe="eficiencia"))
    casa.passo(1, desvio("US11", classe="eficiencia"))
    assert casa.chamadas_ia == []
    assert casa.historico == [("US11", "silenciado pelo responsável")]


def test_silencio_expirado_nao_conta():
    casa = Casa(silencios=[Silencio(us="US11", ate=minuto(-1), motivo="visita")])
    casa.passo(0, desvio("US11", classe="eficiencia"))
    assert casa.chamadas_ia == ["US11"]


def test_ativa_que_muda_atualiza_com_o_resumo_sem_ir_a_ia():
    casa = Casa()
    casa.passo(0, desvio("US08", "eficiencia", "a sala desceu 2 °C"))
    casa.passo(2, desvio("US08", "seguranca", "porta aberta há 5 minutos e a sala desceu 2 °C"))
    assert casa.chamadas_ia == ["US08"]
    assert casa.publicadas[-1] == ("ativa", "seguranca", "porta aberta há 5 minutos e a sala desceu 2 °C")


def test_resolve_sozinha_quando_o_desvio_desaparece():
    casa = Casa()
    casa.passo(0, desvio())
    casa.passo(2)
    assert casa.publicadas[-1][0] == "resolvida"
    assert casa.ultima.resolucao == TextoEm(texto="Resolvida sozinha às 03:12.", em=minuto(2))


def test_resolve_com_o_texto_da_resolucao_da_regra():
    casa = Casa()
    casa.passo(0, desvio())
    casa.passo(2, Resolucao(us="US08", texto="a porta fechou às 03:12", em=minuto(2)))
    assert casa.publicadas[-1][0] == "resolvida"
    assert casa.ultima.resolucao.texto == "a porta fechou às 03:12"


def test_resolucao_resolve_tambem_as_que_esperam_resposta():
    casa = Casa()
    casa.passo(0, desvio("US07"))
    casa.passo(1, Resolucao(us="US07", texto="fechou", em=minuto(1)))
    assert [p[0] for p in casa.publicadas] == ["ativa", "resolvida"]


def test_us07_so_se_resolve_com_resposta():
    casa = Casa()
    casa.passo(0, desvio("US07"))
    casa.passo(2)
    assert [p[0] for p in casa.publicadas] == ["ativa"]


def test_respondida_com_o_desvio_ainda_presente_nao_volta_a_avisar():
    casa = Casa()
    casa.passo(0, desvio())
    # O responsável responde pela PWA: na base de dados a anomalia fica resolvida.
    resolvida = casa.ultima.model_copy(update={"estado": "resolvida"})
    casa.ciclo.obter_anomalia = {resolvida.id: resolvida}.get
    casa.passo(1, desvio(resumo="porta aberta há 6 minutos"))  # o ciclo lê-a e vê que já foi respondida
    casa.passo(2, desvio())
    casa.passo(3)
    assert casa.chamadas_ia == ["US08"]
    assert len(casa.publicadas) == 1


class Contacto:
    def __init__(self):
        self.chamadas: list[str] = []

    def agendar(self, a, imediato=False):
        self.chamadas.append("agendar")

    def cancelar(self, i):
        self.chamadas.append("cancelar")

    def resolvida(self, a):
        self.chamadas.append("resolvida")


@pytest.fixture
def avisos():
    contacto = Contacto()
    enviadas: list[dict] = []
    return Avisos(gravar=lambda a: None, enviar_ws=enviadas.append, contacto=contacto), contacto, enviadas


def anomalia(classe="seguranca"):
    return Anomalia(id="a1", classe=classe, titulo="t", explicacao="e", detetada_em=T0)


def test_publicar_nova_agenda_e_envia_pelo_ws(avisos):
    av, contacto, enviadas = avisos
    av.publicar(anomalia())
    assert contacto.chamadas == ["agendar"]
    assert enviadas == [anomalia()]


def test_publicar_resolvida_avisa_o_contacto(avisos):
    av, contacto, _ = avisos
    a = anomalia()
    av.publicar(a)
    a.estado = "resolvida"
    av.publicar(a)
    av.publicar(a)
    assert contacto.chamadas == ["agendar", "resolvida"]


def test_publicar_passou_a_seguranca_agenda_de_novo(avisos):
    av, contacto, _ = avisos
    a = anomalia("eficiencia")
    av.publicar(a)
    a.classe = "seguranca"
    av.publicar(a)
    a.explicacao = "outro texto"
    av.publicar(a)
    assert contacto.chamadas == ["agendar", "agendar"]


def test_ao_vivo_usa_a_hora_do_relogio():
    from backend.ciclo import ao_vivo
    from backend.relogio import Relogio

    vistos: list[datetime] = []
    ciclo = Ciclo(
        regras=[lambda leituras, contexto, agora: vistos.append(agora) or []],
        avaliar=lambda d, c: None,
        publicar=lambda a, **k: None,
        obter_contexto=lambda: Contexto([], [], [], False),
        registar_historico=lambda d, m, a: None,
    )
    real = [datetime(2026, 11, 18, 14, 0)]
    relogio = Relogio(datetime(2026, 11, 19, 8, 50), fator=60, real=lambda: real[0])

    def dormir(segundos: float) -> None:
        real[0] += timedelta(seconds=segundos)

    ao_vivo(ciclo, lambda: [], relogio, intervalo=5, passos=3, dormir=dormir)
    assert vistos == [datetime(2026, 11, 19, 8, 50), datetime(2026, 11, 19, 8, 55), datetime(2026, 11, 19, 9, 0)]


def test_publicar_resolvida_que_nunca_viu_nao_agenda(avisos):
    """Ex.: resposta via API depois de um reinício (o --reload do docker) ou anomalia de /dev."""
    av, contacto, _ = avisos
    a = anomalia()
    a.estado = "resolvida"
    av.publicar(a)
    assert contacto.chamadas == []


class ContactoComImediato(Contacto):
    def agendar(self, a, imediato=False):
        self.chamadas.append("agendar imediato" if imediato else "agendar")


def test_desvio_imediato_chega_ao_contacto_externo():
    """US07/US14 com a casa vazia: o contacto é avisado sem esperar o tempo de espera."""
    contacto = ContactoComImediato()
    av = Avisos(gravar=lambda a: None, enviar_ws=lambda a: None, contacto=contacto)
    casa = Casa()
    casa.ciclo.publicar = av.publicar
    casa.passo(0, Desvio(us="US07", classe="seguranca", resumo="porta abriu", habitual=None, imediato=True))
    casa.passo(1, desvio())
    assert contacto.chamadas == ["agendar imediato", "agendar"]


def test_a_linha_de_comandos_nao_escreve_no_homaly_db(tmp_path, monkeypatch):
    from backend import avisos, ciclo, db

    monkeypatch.setattr(avisos, "_padrao", None)  # o main() põe as peças falsas
    dev = tmp_path / "homaly.db"
    monkeypatch.setattr(db, "CAMINHO", str(dev))
    ciclo.main([str(Path(__file__).parent.parent / "dados" / "us11.csv")])
    assert db.CAMINHO != str(dev)
    assert not dev.exists()


def test_silencio_temporario_nao_cala_seguranca_no_ciclo():
    """Recusar desligar a tomada silencia a US14 até ao fim do dia; com a casa vazia é segurança e avisa."""
    casa = Casa(silencios=[Silencio("US14", minuto(60), "Recusou: desligar a tomada")])
    casa.passo(0, desvio(us="US14", classe="eficiencia", resumo="a gastar"))
    casa.passo(1)
    casa.passo(2, desvio(us="US14", classe="seguranca", resumo="a gastar com a casa vazia"))
    assert casa.chamadas_ia == ["US14"]
    assert casa.historico[0] == ("US14", "silenciado pelo responsável")


@pytest.mark.parametrize("ia_avisa, silencios", [
    (True, [Silencio("US14", minuto(60), "Recusou: desligar a tomada")]),  # silenciada
    (False, []),  # a IA decidiu não avisar
])
def test_a_meio_passa_a_seguranca_e_avisa(ia_avisa, silencios):
    """A tomada já gastava (eficiência, calada) e a casa fica vazia: agora é segurança e avisa."""
    casa = Casa(ia_avisa=ia_avisa, silencios=silencios)
    casa.passo(0, desvio(us="US14", classe="eficiencia", resumo="a gastar"))
    casa.ia_avisa = True
    casa.passo(1, desvio(us="US14", classe="seguranca", resumo="a gastar com a casa vazia"))
    assert casa.publicadas[-1][:2] == ("ativa", "seguranca")


def test_ativa_que_muda_guarda_o_habitual_na_explicacao():
    casa = Casa()
    casa.passo(0, desvio(us="US12", classe="saude_conforto", resumo="porta aberta, frio"))
    casa.passo(1, Desvio(us="US12", classe="seguranca", resumo="porta aberta há 5 min",
                         habitual="A porta costuma fechar em 1 min."))
    assert casa.publicadas[-1][2] == "porta aberta há 5 min Habitual: A porta costuma fechar em 1 min."
