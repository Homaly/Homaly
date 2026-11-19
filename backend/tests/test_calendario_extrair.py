from datetime import datetime, time

from backend.calendario.extrair import Evento, extrair, ler_eventos, sem_ia
from backend.formatos import Compromisso, Periodo, Rotina
from tests.conftest import AGORA, LX, ModeloFixo

# AGORA é uma terça, 17 de novembro de 2026, às 15:00.
EMPREGADA = {
    "summary": "Empregada",
    "start": {"dateTime": "2026-09-01T10:00:00+01:00"},
    "end": {"dateTime": "2026-09-01T12:00:00+01:00"},
    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TU"],
}
FERIAS = {"summary": "Férias Algarve", "start": {"date": "2026-12-01"}, "end": {"date": "2026-12-09"}}
DENTISTA = {
    "summary": "Dentista",
    "start": {"dateTime": "2026-11-17T16:00:00Z"},
    "end": {"dateTime": "2026-11-17T17:00:00Z"},
}


def test_ler_eventos_na_hora_local():
    empregada, ferias, dentista = ler_eventos([EMPREGADA, FERIAS, DENTISTA], LX)
    assert empregada.inicio == datetime(2026, 9, 1, 10, 0, tzinfo=LX)
    assert empregada.repete == "RRULE:FREQ=WEEKLY;BYDAY=TU"
    assert ferias.dia_todo and ferias.inicio == datetime(2026, 12, 1, tzinfo=LX)
    assert dentista.inicio.hour == 16  # em novembro Lisboa está em UTC+0


def test_eventos_sem_titulo_ou_datas_ficam_de_fora():
    assert ler_eventos([{"start": {}, "end": {}}, {"summary": "x", "start": {"date": "ontem"}, "end": {}}], LX) == []


def test_para_ia_o_dia_inteiro_acaba_no_ultimo_dia():
    (ferias,) = ler_eventos([FERIAS], LX)
    assert ferias.para_ia() == {
        "titulo": "Férias Algarve", "inicio": "2026-12-01", "fim": "2026-12-08", "dia_todo": True, "repete": None
    }  # fmt: skip


def test_a_ia_tira_ferias_rotinas_e_compromissos():
    modelo = ModeloFixo(
        {
            "ferias": [{"inicio": "2026-12-01", "fim": "2026-12-08", "motivo": "Férias no Algarve"}],
            "rotinas": [{"descricao": "a empregada vem", "dias": [1], "hora": "10:00"}],
            "compromissos": [{"descricao": "Dentista", "inicio": "2026-11-17T16:00", "fim": "2026-11-17T17:00"}],
        }
    )
    itens = extrair(ler_eventos([EMPREGADA, FERIAS, DENTISTA], LX), AGORA, modelo)
    assert itens.ferias == [
        Periodo(datetime(2026, 12, 1, tzinfo=LX), datetime.combine(datetime(2026, 12, 8).date(), time.max, tzinfo=LX), "Férias no Algarve")
    ]
    assert itens.rotinas == [Rotina("a empregada vem", [1], time(10, 0))]
    assert itens.compromissos == [
        Compromisso("Dentista", datetime(2026, 11, 17, 16, tzinfo=LX), datetime(2026, 11, 17, 17, tzinfo=LX))
    ]
    sistema, mensagem = modelo.chamadas[0]
    assert "Empregada" in mensagem and "terça-feira, 2026-11-17" in mensagem


def test_o_que_a_ia_inventa_mal_fica_de_fora():
    modelo = ModeloFixo(
        {
            "ferias": [{"inicio": "2026-12-08", "fim": "2026-12-01", "motivo": "ao contrário"}, "texto"],
            "rotinas": [{"descricao": "x", "dias": [9], "hora": None}],
            "compromissos": [{"descricao": "", "inicio": "2026-11-17T16:00", "fim": "2026-11-17T17:00"}],
        }
    )
    assert len(extrair(ler_eventos([FERIAS], LX), AGORA, modelo)) == 0


def test_sem_ia_rotinas_e_compromissos_saem_dos_eventos():
    itens = extrair(ler_eventos([EMPREGADA, FERIAS, DENTISTA], LX), AGORA, ModeloFixo(None))
    assert itens.rotinas == [Rotina("Empregada", [1], time(10, 0))]
    assert [c.descricao for c in itens.compromissos] == ["Dentista"]
    assert [p.motivo for p in itens.ferias] == ["Férias Algarve"]
    assert itens.ferias[0].fim.date().day == 8


def test_sem_eventos_nao_chama_a_ia():
    modelo = ModeloFixo({})
    assert len(extrair([], AGORA, modelo)) == 0
    assert modelo.chamadas == []


def _repete(regra: str, dia_todo: bool = False) -> Evento:
    inicio = datetime(2026, 9, 2, 8, 30, tzinfo=LX)  # uma quarta
    return Evento("Ginásio", inicio, inicio, dia_todo, regra)


def test_sem_ia_regras_de_repeticao():
    assert sem_ia([_repete("RRULE:FREQ=DAILY")]).rotinas == [Rotina("Ginásio", list(range(7)), time(8, 30))]
    assert sem_ia([_repete("RRULE:FREQ=WEEKLY")]).rotinas[0].dias == [2]
    assert sem_ia([_repete("RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR")]).rotinas[0].dias == [0, 2, 4]
    assert sem_ia([_repete("RRULE:FREQ=WEEKLY;BYDAY=TU", dia_todo=True)]).rotinas[0].hora is None
    assert sem_ia([_repete("RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU")]).rotinas == []
    assert sem_ia([_repete("RRULE:FREQ=MONTHLY;BYMONTHDAY=1")]).rotinas == []


def test_sem_ia_dia_inteiro_que_nao_e_ferias_fica_de_fora():
    aniversario = {"summary": "Anos da Ana", "start": {"date": "2026-11-20"}, "end": {"date": "2026-11-21"}}
    assert len(sem_ia(ler_eventos([aniversario], LX))) == 0


def test_o_que_se_repete_fica_a_hora_de_relogio_do_evento():
    # Criado em setembro (UTC+1), lido em novembro com a casa num desvio fixo de UTC+0.
    from datetime import timedelta, timezone

    inverno = timezone(timedelta(0))
    (sem_nome,) = ler_eventos([EMPREGADA], inverno)
    assert sem_nome.inicio.time() == time(10, 0)
    com_nome = {**EMPREGADA, "start": {**EMPREGADA["start"], "timeZone": "Europe/Lisbon"}}
    assert ler_eventos([com_nome], inverno)[0].inicio.time() == time(10, 0)
    # Um evento que não se repete passa para o fuso da casa.
    assert ler_eventos([DENTISTA], inverno)[0].inicio.tzinfo == inverno


def test_diario_so_em_alguns_dias():
    assert sem_ia([_repete("RRULE:FREQ=DAILY;BYDAY=SA,SU")]).rotinas[0].dias == [5, 6]
