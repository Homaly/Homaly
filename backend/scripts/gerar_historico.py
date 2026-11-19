"""Gera dados/historico.csv: quatro semanas de uma família que trabalha, até à véspera da demo.

- Dias úteis: sai entre as 7h30 e as 8h30, chega entre as 18h00 e as 19h30;
  às vezes uma saída curta ao fim da tarde, ainda antes das 19h30.
- Fins de semana: a primeira abertura entre as 9h30 e as 11h00, a última até às 23h00.
- Nunca abre de madrugada.
- Na tomada, um desumidificador: ligado no máximo uma hora seguida, algumas vezes por dia,
  com a família em casa.
- Sinais de vida (US09), com a lâmpada e o movimento na câmara (a hora do movimento):
  - Dias úteis: acorda entre as 6h45 e as 7h15 (luz ligada) e há movimento a cada
    10–40 min até sair; apaga a luz um minuto antes de sair. Ao chegar, movimento e luz
    ligada 5 min depois, e movimento a cada 15–50 min (também na saída curta) até se
    deitar, entre as 22h30 e as 23h30 e depois da tomada da noite (luz desligada).
  - Fins de semana: acorda entre as 7h30 e as 8h00 (luz ligada); movimento a cada
    15–50 min sempre que está em casa; deita-se 30–60 min depois da última abertura
    (luz desligada).
- A semana de FERIAS_DO_HISTORICO: a porta não abre, a tomada não gasta e não há sinais.

Só se escrevem as mudanças (porta a abrir e a fechar, tomada a ligar e a desligar, luz
a ligar e a desligar, cada movimento). Os extremos (07:30, 08:30, 19:30; 09:30, 11:00,
23:00; acordar às 07:15 e às 08:00) são forçados num dia de cada, para o habitual ficar
exato. A porta e a tomada usam a semente SEMENTE e os sinais novos um gerador à parte
(SEMENTE + 1), para a porta e a tomada não mudarem. A semente é fixa: voltar a correr
gera o mesmo ficheiro.

Uso (em backend/): uv run python scripts/gerar_historico.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta

from backend.habitual import FERIAS_DO_HISTORICO, HISTORICO

INICIO = date(2026, 10, 21)  # quarta
FIM = date(2026, 11, 17)  # terça, véspera da demo (18/11)
SEMENTE = 2026


def hora(dia: date, h: int, m: int) -> datetime:
    return datetime.combine(dia, time(h, m))


def entre(rng: random.Random, dia: date, de: tuple[int, int], ate: tuple[int, int]) -> datetime:
    """Uma hora ao acaso entre de e ate, em passos de 5 minutos."""
    a, b = hora(dia, *de), hora(dia, *ate)
    passos = int((b - a).total_seconds() // 300)
    return a + timedelta(minutes=5 * rng.randint(0, passos))


def dia_util(rng: random.Random, dia: date, n: int) -> tuple[list[datetime], list[tuple[datetime, int]]]:
    saida = {0: hora(dia, 7, 30), 2: hora(dia, 8, 30)}.get(n) or entre(rng, dia, (7, 30), (8, 30))
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
    primeira = {0: hora(dia, 9, 30), 2: hora(dia, 11, 0)}.get(n) or entre(rng, dia, (9, 30), (11, 0))
    regresso = entre(rng, dia, (12, 30), (13, 30))
    saida = entre(rng, dia, (15, 0), (17, 0))
    ultima = hora(dia, 23, 0) if n == 1 else entre(rng, dia, (20, 0), (23, 0))
    aberturas = [primeira, regresso, saida, ultima]

    tomada = [(hora(dia, 8, 0) + timedelta(minutes=rng.choice([0, 15, 30])), rng.choice([30, 40, 50]))]
    tomada.append((regresso + timedelta(minutes=rng.choice([20, 40])), rng.choice([30, 45, 60])))
    return aberturas, tomada


Linha = tuple[str, str, str, datetime]


def movimentos(rng: random.Random, desde: datetime, ate: datetime, passo: tuple[int, int]) -> list[Linha]:
    """Movimento na câmara a cada passo[0]–passo[1] minutos, depois de desde e antes de ate."""
    linhas = []
    t = desde + timedelta(minutes=rng.randint(*passo))
    while t < ate:
        linhas.append(("camara", "motionDetected", t.isoformat(), t))
        t += timedelta(minutes=rng.randint(*passo))
    return linhas


def luz(valor: str, em: datetime) -> Linha:
    return ("lampada", "power", valor, em)


def sinais_util(rng: random.Random, dia: date, n: int, aberturas: list[datetime],
                tomada: list[tuple[datetime, int]]) -> list[Linha]:
    saida, chegada = aberturas[0], aberturas[1]
    acorda = hora(dia, 7, 15) if n == 2 else entre(rng, dia, (6, 45), (7, 15))
    linhas = [luz("on", acorda)]
    linhas += movimentos(rng, acorda, saida - timedelta(minutes=1), (10, 40))
    linhas.append(luz("off", saida - timedelta(minutes=1)))

    em_casa = chegada + timedelta(minutes=5)
    fim_da_tomada = max(inicio + timedelta(minutes=minutos) for inicio, minutos in tomada)
    deita = max(entre(rng, dia, (22, 30), (23, 30)), fim_da_tomada + timedelta(minutes=5))
    linhas += [("camara", "motionDetected", em_casa.isoformat(), em_casa), luz("on", em_casa)]
    linhas += movimentos(rng, em_casa, deita, (15, 50))
    linhas.append(luz("off", deita))
    return linhas


def sinais_fim_de_semana(rng: random.Random, dia: date, n: int, aberturas: list[datetime]) -> list[Linha]:
    primeira, regresso, saida, ultima = aberturas
    acorda = hora(dia, 8, 0) if n == 2 else entre(rng, dia, (7, 30), (8, 0))
    deita = ultima + timedelta(minutes=rng.randint(30, 60))
    linhas = [luz("on", acorda)]
    for chega, sai in ((acorda, primeira), (regresso, saida), (ultima, deita)):
        linhas += movimentos(rng, chega, sai, (15, 50))
    linhas.append(luz("off", deita))
    return linhas


def gerar() -> list[Linha]:
    rng = random.Random(SEMENTE)
    rng_sinais = random.Random(SEMENTE + 1)
    linhas: list[Linha] = []
    contagem = {"util": 0, "fim_de_semana": 0}
    dia = INICIO
    while dia <= FIM:
        if not (FERIAS_DO_HISTORICO[0] <= dia <= FERIAS_DO_HISTORICO[1]):
            tipo = "util" if dia.weekday() < 5 else "fim_de_semana"
            fazer = dia_util if tipo == "util" else fim_de_semana
            aberturas, tomada = fazer(rng, dia, contagem[tipo])
            for a in aberturas:
                linhas.append(("porta", "sensorState", "alarm", a))
                linhas.append(("porta", "sensorState", "normal", a + timedelta(minutes=1)))
            for inicio, minutos in tomada:
                linhas.append(("tomada", "instantPower", str(rng.randint(190, 230)), inicio))
                linhas.append(("tomada", "instantPower", "0", inicio + timedelta(minutes=minutos)))
            if tipo == "util":
                linhas += sinais_util(rng_sinais, dia, contagem[tipo], aberturas, tomada)
            else:
                linhas += sinais_fim_de_semana(rng_sinais, dia, contagem[tipo], aberturas)
            contagem[tipo] += 1
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
