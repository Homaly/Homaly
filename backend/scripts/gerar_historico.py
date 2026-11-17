"""Gera dados/historico.csv: quatro semanas de uma família que trabalha.

- Dias úteis: sai entre as 7h30 e as 8h30, chega entre as 18h00 e as 19h30;
  às vezes uma saída curta ao fim da tarde, ainda antes das 19h30.
- Fins de semana: a primeira abertura entre as 9h30 e as 11h00, a última até às 23h00.
- Nunca abre de madrugada.
- Na tomada, um desumidificador: ligado no máximo uma hora seguida, algumas vezes por dia,
  com a família em casa.
- A semana de FERIAS_DO_HISTORICO: a porta não abre e a tomada não gasta.

Só se escrevem as mudanças (porta a abrir e a fechar, tomada a ligar e a desligar).
A semente é fixa: voltar a correr gera o mesmo ficheiro.

Uso (em backend/): uv run python scripts/gerar_historico.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta

from backend.habitual import FERIAS_DO_HISTORICO, HISTORICO

INICIO = date(2026, 10, 19)  # segunda
FIM = date(2026, 11, 15)  # domingo
SEMENTE = 2026


def hora(dia: date, h: int, m: int) -> datetime:
    return datetime.combine(dia, time(h, m))


def entre(rng: random.Random, dia: date, de: tuple[int, int], ate: tuple[int, int]) -> datetime:
    """Uma hora ao acaso entre de e ate, em passos de 5 minutos."""
    a, b = hora(dia, *de), hora(dia, *ate)
    passos = int((b - a).total_seconds() // 300)
    return a + timedelta(minutes=5 * rng.randint(0, passos))


def dia_util(rng: random.Random, dia: date, n: int) -> tuple[list[datetime], list[tuple[datetime, int]]]:
    saida = hora(dia, 7, 30) if n == 0 else entre(rng, dia, (7, 30), (8, 30))
    chegada = hora(dia, 19, 30) if n == 1 else entre(rng, dia, (18, 0), (19, 30))
    aberturas = [saida, chegada]
    if chegada <= hora(dia, 18, 50) and rng.random() < 0.4:  # saída curta, de volta até às 19h30
        sai = chegada + timedelta(minutes=rng.choice([10, 15, 20]))
        aberturas += [sai, sai + timedelta(minutes=rng.choice([10, 15, 20]))]

    tomada = [(chegada + timedelta(minutes=rng.choice([15, 30, 45])), rng.choice([30, 40, 50, 60]))]
    if rng.random() < 0.6:
        tomada.append((entre(rng, dia, (21, 30), (22, 0)), rng.choice([30, 40, 50])))
    return aberturas, tomada


def fim_de_semana(rng: random.Random, dia: date, n: int) -> tuple[list[datetime], list[tuple[datetime, int]]]:
    primeira = hora(dia, 9, 30) if n == 0 else entre(rng, dia, (9, 30), (11, 0))
    regresso = entre(rng, dia, (12, 30), (13, 30))
    saida = entre(rng, dia, (15, 0), (17, 0))
    ultima = hora(dia, 23, 0) if n == 1 else entre(rng, dia, (20, 0), (23, 0))
    aberturas = [primeira, regresso, saida, ultima]

    tomada = [(hora(dia, 8, 0) + timedelta(minutes=rng.choice([0, 15, 30])), rng.choice([30, 40, 50]))]
    tomada.append((regresso + timedelta(minutes=rng.choice([20, 40])), rng.choice([30, 45, 60])))
    return aberturas, tomada


def gerar() -> list[tuple[str, str, str, datetime]]:
    rng = random.Random(SEMENTE)
    linhas: list[tuple[str, str, str, datetime]] = []
    contagem = {"util": 0, "fim_de_semana": 0}
    dia = INICIO
    while dia <= FIM:
        if not (FERIAS_DO_HISTORICO[0] <= dia <= FERIAS_DO_HISTORICO[1]):
            tipo = "util" if dia.weekday() < 5 else "fim_de_semana"
            fazer = dia_util if tipo == "util" else fim_de_semana
            aberturas, tomada = fazer(rng, dia, contagem[tipo])
            contagem[tipo] += 1
            for a in aberturas:
                linhas.append(("porta", "sensorState", "alarm", a))
                linhas.append(("porta", "sensorState", "normal", a + timedelta(minutes=1)))
            for inicio, minutos in tomada:
                linhas.append(("tomada", "instantPower", str(rng.randint(190, 230)), inicio))
                linhas.append(("tomada", "instantPower", "0", inicio + timedelta(minutes=minutos)))
        dia += timedelta(days=1)
    linhas.sort(key=lambda l: l[3])
    return linhas


def main() -> None:
    HISTORICO.parent.mkdir(exist_ok=True)
    with open(HISTORICO, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dispositivo", "tipo", "valor", "em"])
        for dispositivo, tipo, valor, em in gerar():
            w.writerow([dispositivo, tipo, valor, em.isoformat()])
    print(f"escrito {HISTORICO}")


if __name__ == "__main__":
    main()
