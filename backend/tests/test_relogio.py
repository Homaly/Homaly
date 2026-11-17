from datetime import datetime, timedelta

from backend.relogio import Relogio


class Real:
    def __init__(self):
        self.t = datetime(2026, 11, 18, 14, 0)

    def __call__(self):
        return self.t


def test_sem_inicio_e_a_hora_real():
    real = Real()
    r = Relogio(real=real)
    real.t += timedelta(minutes=5)
    assert r.agora() == datetime(2026, 11, 18, 14, 5)


def test_com_inicio_e_fator_acelera():
    real = Real()
    r = Relogio(datetime(2026, 11, 19, 8, 50), fator=60, real=real)
    assert r.agora() == datetime(2026, 11, 19, 8, 50)
    real.t += timedelta(seconds=10)
    assert r.agora() == datetime(2026, 11, 19, 9, 0)


def test_do_ambiente(monkeypatch):
    monkeypatch.setenv("RELOGIO_INICIO", "2026-11-19T08:50:00")
    monkeypatch.setenv("RELOGIO_FATOR", "30")
    r = Relogio.do_ambiente()
    assert (r.inicio, r.fator) == (datetime(2026, 11, 19, 8, 50).astimezone(), 30.0)
    assert r.inicio.tzinfo is not None  # com fuso, como o resto do backend (contrato.py)
    monkeypatch.delenv("RELOGIO_INICIO")
    assert Relogio.do_ambiente().inicio is None


def test_a_api_e_o_ciclo_partilham_o_mesmo_relogio(monkeypatch):
    """Com RELOGIO_INICIO, a hora da API (obter_agora) é a hora simulada do ciclo."""
    from backend import relogio
    from backend.dependencias import obter_agora

    monkeypatch.setattr(relogio, "_partilhado", None)
    monkeypatch.setenv("RELOGIO_INICIO", "2026-11-19T08:50:00")
    monkeypatch.setenv("RELOGIO_FATOR", "1")
    r = relogio.partilhado()
    assert relogio.partilhado() is r
    assert abs(obter_agora() - datetime(2026, 11, 19, 8, 50).astimezone()) < timedelta(seconds=5)
    monkeypatch.setattr(relogio, "_partilhado", None)
