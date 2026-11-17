"""Um reinício do backend não duplica anomalias nem SMS.

As regras da porta, da luz e da temperatura guardam o estado em SQLite e continuam a ver o desvio
depois de um reinício. O ciclo reconstrói as suas ocorrências a partir das anomalias ativas, para
não criar uma anomalia nova (e uma SMS nova) por cima da antiga.
"""

from datetime import datetime, timedelta

from backend import anomalias, ciclo
from backend.ciclo import Ciclo
from backend.contrato import Anomalia, TextoEm
from backend.formatos import Contexto, Desvio, Resolucao
from backend.ia.avaliar import registar_us

from .conftest import LX

AGORA = datetime(2026, 11, 17, 15, 0, tzinfo=LX)


class Montagem:
    """Um ciclo com uma só regra controlada pelo teste e uma "base de dados" em memória."""

    def __init__(self) -> None:
        self.saidas: list[Desvio | Resolucao] = []
        self.publicadas: list[Anomalia] = []
        self.avaliadas: list[Desvio] = []
        self.guardadas: dict[str, Anomalia] = {}
        self.ciclo = Ciclo(
            regras=[lambda l, ctx, agora: list(self.saidas)],
            avaliar=self._avaliar,
            publicar=self._publicar,
            obter_contexto=lambda: Contexto([], [], [], False),
            registar_historico=lambda d, m, a: None,
            obter_anomalia=self.guardadas.get,
        )

    def _avaliar(self, d: Desvio, ctx: Contexto) -> Anomalia:
        self.avaliadas.append(d)
        return Anomalia(classe=d.classe, titulo="t", explicacao=d.resumo)

    def _publicar(self, a: Anomalia, imediato: bool = False) -> None:
        self.publicadas.append(a.model_copy(deep=True))
        self.guardadas[a.id] = a.model_copy(deep=True)

    def ativa(self, us: str, classe: str = "seguranca") -> Anomalia:
        """Uma anomalia ativa, deixada na base de dados antes do reinício."""
        a = Anomalia(classe=classe, titulo="antes do reinício", explicacao="x", detetada_em=AGORA)
        self.guardadas[a.id] = a
        return a


def porta_aberta(classe: str = "seguranca") -> Desvio:
    return Desvio(us="US08", classe=classe, resumo="A porta está aberta há 6 min.", habitual=None)


def test_depois_do_reinicio_o_mesmo_desvio_nao_cria_outra_anomalia():
    m = Montagem()
    antiga = m.ativa("US08")
    m.ciclo.restaurar([("US08", antiga)])

    m.saidas[:] = [porta_aberta()]
    m.ciclo.passo([], AGORA)

    assert m.avaliadas == []  # não voltou à IA
    assert m.publicadas == []  # nem publicou (nem SMS) outra vez


def test_a_reconstruida_resolve_se_com_a_resolucao_da_regra():
    m = Montagem()
    antiga = m.ativa("US08")
    m.ciclo.restaurar([("US08", antiga)])

    fechou = AGORA + timedelta(minutes=2)
    m.saidas[:] = [Resolucao(us="US08", texto="A porta fechou às 15:02.", em=fechou)]
    m.ciclo.passo([], fechou)

    [a] = m.publicadas
    assert (a.id, a.estado, a.resolucao.texto) == (antiga.id, "resolvida", "A porta fechou às 15:02.")


def test_a_reconstruida_nao_se_da_como_resolvida_so_porque_a_regra_esta_calada():
    # A US14 guarda o estado em memória: depois de um reinício fica calada até voltar a contar.
    m = Montagem()
    antiga = m.ativa("US14", classe="eficiencia")
    m.ciclo.restaurar([("US14", antiga)])

    m.ciclo.passo([], AGORA)

    assert m.publicadas == []
    assert m.guardadas[antiga.id].estado == "ativa"


def test_a_reconstruida_que_a_regra_volta_a_ver_continua_a_mesma():
    m = Montagem()
    antiga = m.ativa("US14", classe="eficiencia")
    m.ciclo.restaurar([("US14", antiga)])
    m.ciclo.passo([], AGORA)  # calada

    m.saidas[:] = [Desvio(us="US14", classe="eficiencia", resumo="A gastar desde as 15:00.", habitual=None)]
    m.ciclo.passo([], AGORA + timedelta(hours=3))

    assert m.avaliadas == []
    assert m.publicadas == []


def test_a_reconstruida_que_muda_de_classe_e_publicada():
    # US12 (eficiência) antes do reinício; depois passa a segurança (US08): o mesmo aviso.
    m = Montagem()
    antiga = m.ativa("US08", classe="eficiencia")
    m.ciclo.restaurar([("US08", antiga)])

    m.saidas[:] = [porta_aberta("seguranca")]
    m.ciclo.passo([], AGORA)

    [a] = m.publicadas
    assert (a.id, a.classe) == (antiga.id, "seguranca")
    assert m.avaliadas == []


def test_resolvida_pelo_responsavel_o_desvio_seguinte_e_uma_anomalia_nova():
    m = Montagem()
    antiga = m.ativa("US08")
    m.ciclo.restaurar([("US08", antiga)])
    m.ciclo.passo([], AGORA)  # a regra calada

    # O responsável respondeu pela PWA.
    m.guardadas[antiga.id] = antiga.model_copy(
        update={"estado": "resolvida", "resposta": TextoEm(texto="já fechei")}
    )
    m.ciclo.passo([], AGORA + timedelta(minutes=1))

    m.saidas[:] = [porta_aberta()]
    m.ciclo.passo([], AGORA + timedelta(hours=1))

    assert len(m.avaliadas) == 1
    [nova] = m.publicadas
    assert nova.id != antiga.id


def test_us07_e_us09_nao_se_reconstroem():
    # Só disparam num momento (a abertura; a hora limite do dia): depois de um reinício não voltam
    # a ver o mesmo desvio, por isso não duplicam. Reconstruí-las engolia o desvio seguinte.
    m = Montagem()
    m.ciclo.restaurar([("US07", m.ativa("US07")), ("US09", m.ativa("US09", classe="bem_estar"))])

    m.saidas[:] = [
        Desvio(us="US07", classe="seguranca", resumo="A porta abriu às 03:10.", habitual=None),
        Desvio(us="US09", classe="bem_estar", resumo="A porta não abriu até às 10:30.", habitual=None),
    ]
    m.ciclo.passo([], AGORA)

    assert {d.us for d in m.avaliadas} == {"US07", "US09"}


def test_com_duas_ativas_da_mesma_us_fica_a_mais_recente():
    m = Montagem()
    recente, antiga = m.ativa("US08"), m.ativa("US08")
    m.ciclo.restaurar([("US08", recente), ("US08", antiga)])  # como anomalias.listar: recente primeiro

    m.saidas[:] = [Resolucao(us="US08", texto="A porta fechou.", em=AGORA)]
    m.ciclo.passo([], AGORA)

    [a] = m.publicadas
    assert a.id == recente.id


def test_o_ciclo_real_reconstroi_as_ativas_da_base_de_dados():
    ativa = Anomalia(classe="seguranca", titulo="Porta aberta", explicacao="x", detetada_em=AGORA)
    resolvida = Anomalia(classe="eficiencia", titulo="Luz", explicacao="x", detetada_em=AGORA, estado="resolvida")
    sem_us = Anomalia(classe="seguranca", titulo="De /dev, sem US", explicacao="x", detetada_em=AGORA)
    for a in (ativa, resolvida, sem_us):
        anomalias.guardar(a)
    registar_us(ativa.id, "US08")
    registar_us(resolvida.id, "US11")

    c, _ = ciclo.real(_RelogioFixo())

    assert set(c.ocorrencias) == {"US08"}
    assert c.ocorrencias["US08"].anomalia.id == ativa.id


class _RelogioFixo:
    def agora(self) -> datetime:
        return AGORA
