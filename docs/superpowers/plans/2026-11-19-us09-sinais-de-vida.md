# US09 — A casa não vê sinais de vida — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refazer a US09: em vez de "a porta não abriu até à hora habitual", a casa avisa quando não vê sinais de vida (câmara, lâmpada, tomada, porta), de manhã ou quando a atividade pára com a pessoa em casa, e resolve-se sozinha com o próximo sinal.

**Architecture:** Um módulo puro novo, `backend/sinais.py`, diz o que é um sinal de vida (comparando cada leitura com a anterior); serve a regra e o `habitual`, que passa a aprender do histórico a hora do primeiro sinal do dia e as horas com atividade. O histórico simulado ganha a câmara e a lâmpada. A regra `regras/us09.py` é reescrita com o estado em SQLite (como a US11), para sobreviver a um reinício; por isso a US09 deixa de estar em `ciclo.NAO_RECONSTRUIR`. Os comandos da própria casa (apagar a luz na US11) ficam registados em `dispositivos` e não contam como sinal.

**Tech Stack:** Python 3.12, uv, pytest, sqlite3 via `backend.db`.

**Spec:** `USER_STORIES.md`, secção "US09 — A casa não vê sinais de vida" (alterações ainda por commitar no `main`, junto com `PLANO.md`, `DIVISAO.md`, `docs/diagramas/us09-sem-sinais-de-vida.txt` e `docs/diagramas/us01-contar-a-casa.txt`).

## Global Constraints

- Comandos a partir de `backend/`: `uv run pytest`.
- Código, nomes, textos e mensagens de commit em português de Portugal.
- Trabalhar num ramo próprio (`vila/us09-sinais-de-vida`), não no `main`. Os documentos da especificação, ainda por commitar, vão no primeiro commit do ramo, se a Vila concordar.
- Cada commit termina com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nada de push sem o OK da Vila.
- Base de dados só por `backend.db` (`db.esquema(...)`, `with db.ligar() as con:`), datas guardadas em ISO com o offset (`regras._comum.com_fuso`).
- Os formatos de `formatos.py` não mudam (`Leitura`, `Desvio`, `Resolucao`, `Contexto`).
- Sinal de vida, pela spec: movimento ou som na câmara (`camara`/`motionDetected`, `camara`/`soundDetected`), a lâmpada ligada, desligada ou com o brilho mudado (`lampada`/`power`, `lampada`/`brightness`), a tomada a começar a gastar (`tomada`/`instantPower` a passar `LIMITE_W` = 10 W) ou a porta a abrir (`porta`/`sensorState` a passar a `alarm`).
- Textos dos sinais (usados no resumo e na resolução): `"movimento na câmara"`, `"som na câmara"`, `"a luz ligada"`, `"a luz desligada"`, `"o brilho da luz mudado"`, `"a tomada a gastar"`, `"a porta aberta"`.
- Valores a afinar (spec: "a margem da manhã e as três horas são valores a afinar"): `MARGEM_US09 = 1 h 30` (o exemplo da spec: habitual antes das 9h, limite 10h30), `US09_HORAS` = 3 (ambiente, para a demo), `ATIVIDADE_FRACAO = 0.25`, `US09_LACUNA_MINUTOS` = 30 (ambiente).
- O formato de `motionDetected` com movimento não está confirmado (a 2026-11-19 vinha `""`): conta como sinal **um valor não vazio diferente do anterior**. Fica isolado numa função de `sinais.py`, para mudar num só sítio quando se confirmar.

## Review Focus

1. **A casa apaga a luz com o aviso ativo** (a US11 e a US09 juntas são o cenário da queda: luz acesa e ninguém a mexer): a lâmpada a mudar por um comando da casa não é sinal de vida e não resolve a US09. Testes nas Tasks 2 e 5.
2. **Reinício do backend (cada push ao `main` faz deploy) com o aviso ativo:** não cria outra anomalia nem outra SMS, e o próximo sinal resolve a antiga. Testes na Task 5.
3. **O ciclo esteve parado ou o MCP falhou de manhã:** a casa não sabe se houve sinais, por isso não avisa "manhã sem atividade" nem conta esse tempo como silêncio. Testes na Task 5.
4. **Deitar-se depois da meia-noite:** às 07:00 já houve um sinal "hoje" (00:30) e passaram seis horas, mas as horas de sono não contam; não avisa "a atividade parou". Testes nas Tasks 3 e 5.
5. **`motionDetected` fica com o mesmo valor não vazio** (o formato por confirmar pode ser a hora do último movimento): conta uma vez, não a cada polling, senão a casa nunca avisaria. Teste na Task 1.

---

### Task 1: O que é um sinal de vida (`sinais.py`)

**Files:**
- Create: `backend/src/backend/sinais.py`
- Modify: `backend/src/backend/habitual.py` (`LIMITE_W` passa a vir de `sinais`: `from backend.sinais import LIMITE_W`, para `habitual.LIMITE_W` continuar a funcionar na US14)
- Test: `backend/tests/test_sinais.py`

**Interfaces:**
- Produces:
  - `LIMITE_W: float = 10.0`
  - `CHAVES: frozenset[tuple[str, str]]` — os sete pares (dispositivo, tipo) da Global Constraints.
  - `@dataclass(frozen=True) class Sinal: dispositivo: str; descricao: str; em: datetime`
  - `sinal(dispositivo: str, tipo: str, valor, anterior) -> str | None` — a descrição, ou None. `anterior is None` (não se sabe) nunca dá sinal.
  - `comunica(leituras: list[Leitura]) -> bool` — há pelo menos uma leitura de uma das `CHAVES`.
  - `class Detetor: __init__(self, anteriores: dict[tuple[str, str], object] | None = None, comandado: Callable[[str, str], bool] = lambda d, t: False)`; `ver(self, leituras: list[Leitura]) -> list[Sinal]` pela ordem das leituras, com `em` da leitura; guarda cada valor como o novo anterior. Uma mudança de um par para o qual `comandado(dispositivo, tipo)` é True guarda o valor mas não dá sinal.
  - `BASE: dict[tuple[str, str], object]` — o estado de partida do histórico: porta `"normal"`, lâmpada `power` `"off"`, tomada `instantPower` `0.0`, câmara `motionDetected` e `soundDetected` `""`.

- [ ] **Step 1: Escrever os testes**

```python
def test_cada_tipo_de_sinal():
    assert sinal("camara", "motionDetected", "2026-11-20T11:05", "") == "movimento na câmara"
    assert sinal("camara", "soundDetected", "x", "") == "som na câmara"
    assert sinal("lampada", "power", "on", "off") == "a luz ligada"
    assert sinal("lampada", "power", "off", "on") == "a luz desligada"
    assert sinal("lampada", "brightness", 40, 100) == "o brilho da luz mudado"
    assert sinal("tomada", "instantPower", 190.0, 0.0) == "a tomada a gastar"
    assert sinal("porta", "sensorState", "alarm", "normal") == "a porta aberta"

def test_o_que_nao_e_sinal():
    assert sinal("camara", "motionDetected", "", "2026-11-20T11:05") is None
    assert sinal("camara", "motionDetected", "2026-11-20T11:05", "2026-11-20T11:05") is None  # Review Focus 5
    assert sinal("tomada", "instantPower", 200.0, 190.0) is None  # já gastava
    assert sinal("tomada", "instantPower", 0.0, 190.0) is None
    assert sinal("porta", "sensorState", "normal", "alarm") is None  # fechar não conta
    assert sinal("lampada", "power", "on", None) is None  # sem anterior
    assert sinal("temperatura", "temperatureValue", 15.0, 20.0) is None

def test_detetor_compara_com_a_volta_anterior():
    d = Detetor()
    assert d.ver([Leitura("lampada", "power", "off", T0)]) == []  # a primeira volta é o ponto de partida
    assert d.ver([Leitura("lampada", "power", "on", T1)]) == [Sinal("lampada", "a luz ligada", T1)]
    assert d.ver([Leitura("lampada", "power", "on", T2)]) == []

def test_um_dispositivo_que_falta_numa_volta_guarda_o_anterior():
    d = Detetor(anteriores=BASE)
    assert d.ver([Leitura("porta", "sensorState", "normal", T1)]) == []
    assert d.ver([Leitura("lampada", "power", "on", T2)]) == [Sinal("lampada", "a luz ligada", T2)]

def test_um_comando_da_casa_nao_e_sinal():
    d = Detetor(anteriores=BASE, comandado=lambda disp, tipo: (disp, tipo) == ("lampada", "power"))
    assert d.ver([Leitura("lampada", "power", "on", T1)]) == []
    assert d.ver([Leitura("camara", "motionDetected", "a", T2)]) == [Sinal("camara", "movimento na câmara", T2)]

def test_comunica():
    assert comunica([Leitura("porta", "sensorState", "normal", T0)])
    assert not comunica([Leitura("temperatura", "temperatureValue", 20.0, T0)])
    assert not comunica([])
```

(`T0`, `T1`, `T2`: três `datetime` seguidos de 2026-11-20.)

- [ ] **Step 2:** `uv run pytest tests/test_sinais.py -v` → FAIL (`ModuleNotFoundError: backend.sinais`).
- [ ] **Step 3:** Escrever `sinais.py` com as interfaces acima. A tomada compara `float(valor) > LIMITE_W` com `float(anterior) <= LIMITE_W`; a câmara usa `valor != "" and valor != anterior`. Docstring: o que é um sinal de vida e a nota sobre o formato por confirmar de `motionDetected`.
- [ ] **Step 4:** `uv run pytest` → tudo PASS (inclui a US14, que lê `habitual.LIMITE_W`).
- [ ] **Step 5: Commit** — `feat: sinais de vida (US09) a partir das leituras`

---

### Task 2: Os comandos da casa ficam registados (`dispositivos`)

**Files:**
- Modify: `backend/src/backend/dispositivos/__init__.py` (`executar`, novo `comandado_ha_pouco`, `__all__`)
- Test: `backend/tests/test_dispositivos.py`

**Interfaces:**
- Produces: `COMANDO_SEGUNDOS = 60.0`; `comandado_ha_pouco(dispositivo: str, tipo: str) -> bool` — True se `executar` mandou esse (dispositivo, tipo) há menos de `COMANDO_SEGUNDOS` segundos **reais** (`time.monotonic()`, não o relógio acelerado: o polling também corre em segundos reais).

- [ ] **Step 1: Escrever os testes** (com o fixture `falso` que já existe)

```python
def test_um_comando_fica_registado_um_minuto(falso, monkeypatch):
    falso.detalhes[LAMPADA] = [detalhes("power", "off")]
    agora = [1000.0]
    monkeypatch.setattr(dispositivos.time, "monotonic", lambda: agora[0])
    assert not dispositivos.comandado_ha_pouco("lampada", "power")
    dispositivos.executar("lampada", "power", "off")
    assert dispositivos.comandado_ha_pouco("lampada", "power")
    assert not dispositivos.comandado_ha_pouco("lampada", "brightness")
    agora[0] += 61
    assert not dispositivos.comandado_ha_pouco("lampada", "power")
```

- [ ] **Step 2:** `uv run pytest tests/test_dispositivos.py -v -k comando` → FAIL (`AttributeError: comandado_ha_pouco`).
- [ ] **Step 3:** Em `executar`, antes de chamar o MCP (e depois de `_validar`), guardar `time.monotonic()` num `dict` `_comandos[(dispositivo, tipo)]`, sob o `_trinco`. Uma linha na docstring do módulo.
- [ ] **Step 4:** `uv run pytest tests/test_dispositivos.py -v` → PASS.
- [ ] **Step 5: Commit** — `feat: dispositivos lembra os comandos da casa`

---

### Task 3: Histórico com a câmara e a lâmpada, e o habitual dos sinais de vida

**Files:**
- Modify: `backend/scripts/gerar_historico.py`
- Regenerate: `backend/dados/historico.csv` (`uv run python scripts/gerar_historico.py`)
- Modify: `backend/src/backend/habitual.py`
- Test: `backend/tests/test_habitual.py`

**Interfaces:**
- Consumes: `sinais.Detetor`, `sinais.BASE`, `sinais.Sinal`.
- Produces (em `habitual`):
  - `MARGEM_US09 = timedelta(hours=1, minutes=30)`, `ATIVIDADE_FRACAO = 0.25`
  - `sinais_de_vida(caminho: Path | str = HISTORICO, excluir: Container[date] = ()) -> list[Sinal]` — o histórico passado por um `Detetor(anteriores=BASE)`, uma linha de cada vez, sem a semana de férias nem os dias em `excluir`.
  - Novos campos de `Habitual`: `primeiro_sinal: dict[str, time]` (por tipo de dia, o primeiro sinal do dia mais tardio) e `atividade: dict[str, frozenset[int]]` (por tipo de dia, as horas 0–23 com sinais em pelo menos `ATIVIDADE_FRACAO` dos dias desse tipo com sinais).
  - `Habitual.limite_sem_sinais(quando: datetime | date) -> time | None` — `primeiro_sinal + MARGEM_US09`; None se esse tipo de dia não tem sinais.
  - `Habitual.texto_primeiro_sinal(quando) -> str` — `"Nos dias úteis, o primeiro sinal de vida costuma chegar até às 07:15."`
  - `Habitual.com_atividade(quando: datetime) -> bool` — a hora de `quando` está em `atividade[tipo_de_dia(quando)]`.
  - `Habitual.tempo_ativo(desde: datetime, ate: datetime) -> timedelta` — a parte de `[desde, ate]` que cai em horas com atividade (cada hora conta pelo tipo do seu dia).
  - `Habitual.texto_atividade(quando) -> str` — as horas com atividade em intervalos seguidos: `"Nos dias úteis, costuma haver atividade das 06:00 às 09:00 e das 18:00 às 24:00."` (o fim de um intervalo é a hora seguinte à última; `24:00` para a meia-noite).
- Os campos e métodos da porta para a US09 (`primeira_abertura`, `limite_porta_nao_abriu`, `texto_primeira_abertura`) ficam até à Task 5, que os remove.

- [ ] **Step 1: Mudar o gerador.** Os sinais novos usam um segundo gerador, `random.Random(SEMENTE + 1)`, para a porta e a tomada ficarem iguais ao ficheiro atual (os testes da porta e da US14 não mudam). Só se escrevem mudanças. A câmara escreve `camara,motionDetected,<hora ISO do movimento>`. Em cada dia fora das férias:
  - **Dias úteis:** acorda entre as 06:45 e as 07:15 (lâmpada `on`); movimento a cada 10–40 min até à saída; lâmpada `off` um minuto antes da saída. Na chegada, movimento 5 min depois, lâmpada `on`, movimento a cada 15–50 min (incluindo durante a saída curta, que já é porta); deita-se entre as 22:30 e as 23:30 (lâmpada `off`), depois da tomada da noite.
  - **Fins de semana:** acorda entre as 07:30 e as 08:00 (lâmpada `on`); movimento a cada 15–50 min sempre que está em casa (do acordar à primeira abertura, do regresso à saída da tarde, da última abertura até se deitar); deita-se 30–60 min depois da última abertura (lâmpada `off`).
  - Extremos forçados num dia de cada, como já se faz com a porta: acordar às 07:15 (útil, `n == 2`) e às 08:00 (fim de semana, `n == 2`).
  - Atualizar a docstring do gerador.
- [ ] **Step 2:** `uv run python scripts/gerar_historico.py` e confirmar com `git diff --stat dados/historico.csv` que só há linhas acrescentadas (`lampada` e `camara`); `grep -c "^porta\|^tomada" dados/historico.csv` dá 194, como antes.
- [ ] **Step 3: Escrever os testes**

```python
def test_primeiro_sinal_e_limite_da_us09():
    h = habitual.padrao()
    assert h.primeiro_sinal == {"util": time(7, 15), "fim_de_semana": time(8, 0)}
    assert h.limite_sem_sinais(datetime(2026, 11, 20)) == time(8, 45)  # sexta
    assert h.limite_sem_sinais(datetime(2026, 11, 21)) == time(9, 30)  # sábado
    assert h.texto_primeiro_sinal(datetime(2026, 11, 20)) == (
        "Nos dias úteis, o primeiro sinal de vida costuma chegar até às 07:15."
    )

def test_horas_com_atividade():
    h = habitual.padrao()
    assert {7, 19, 20, 21, 22} <= h.atividade["util"]
    assert not {3, 12, 15} & h.atividade["util"]  # a dormir ou no trabalho
    assert {13, 14} <= h.atividade["fim_de_semana"]
    assert 3 not in h.atividade["fim_de_semana"]

def test_tempo_ativo_so_conta_as_horas_com_atividade():
    h = habitual.Habitual(porta={}, tomada_max=timedelta(0), primeira_abertura={},
                          primeiro_sinal={}, atividade={"util": frozenset({6, 7, 19, 20, 21, 22}),
                                                        "fim_de_semana": frozenset()})
    sexta = lambda hh, mm=0: datetime(2026, 11, 20, hh, mm)
    assert h.tempo_ativo(sexta(19, 30), sexta(22, 30)) == timedelta(hours=3)
    assert h.tempo_ativo(sexta(0, 30), sexta(7, 0)) == timedelta(hours=1)  # Review Focus 4: o sono não conta
    assert h.tempo_ativo(sexta(22, 30), datetime(2026, 11, 21, 9, 0)) == timedelta(minutes=30)  # sábado sem atividade
    assert h.texto_atividade(sexta(10)) == (
        "Nos dias úteis, costuma haver atividade das 06:00 às 08:00 e das 19:00 às 23:00."
    )

def test_os_sinais_das_ferias_nao_contam(tmp_path):
    csv = tmp_path / "h.csv"
    csv.write_text(
        "dispositivo,tipo,valor,em\n"
        "lampada,power,on,2026-10-20T06:50:00\n"
        "lampada,power,off,2026-11-03T03:00:00\n"  # dentro das férias do histórico
    )
    assert habitual.sinais_de_vida(csv) == [Sinal("lampada", "a luz ligada", datetime(2026, 10, 20, 6, 50))]
    assert habitual.carregar(csv).primeiro_sinal == {"util": time(6, 50)}
```

- [ ] **Step 4:** `uv run pytest tests/test_habitual.py -v` → FAIL nos testes novos.
- [ ] **Step 5:** Implementar em `habitual.py`. `carregar` calcula `primeiro_sinal` e `atividade` a partir de `sinais_de_vida(caminho, excluir)`. Atualizar a docstring do módulo (o que é habitual para a US09).
- [ ] **Step 6:** `uv run pytest` → tudo PASS. Se `test_horas_com_atividade` ou os limites falharem, o gerador é que não cumpre o Step 1: corrigir o gerador, não os valores do teste.
- [ ] **Step 7: Commit** — `feat: histórico com câmara e lâmpada, e o habitual dos sinais de vida`

---

### Task 4: A afinação passa todos os dispositivos pelas regras

**Files:**
- Modify: `backend/src/backend/afinacao.py`
- Test: `backend/tests/test_afinacao.py`

**Interfaces:**
- Consumes: `habitual.sinais_de_vida`, `habitual.Habitual.limite_sem_sinais`, `sinais.BASE`.
- Produces: `_mudancas(caminho) -> list[tuple[datetime, str, str, str]]` (em, dispositivo, tipo, valor); `pollings` passa a levar uma `Leitura` por cada par (dispositivo, tipo) do histórico, partindo de `sinais.BASE` (com `("tomada", "instantPower")` como `float`).

- [ ] **Step 1: Escrever o teste**

```python
def test_os_pollings_levam_a_camara_e_a_lampada():
    mudancas = afinacao._mudancas(habitual.HISTORICO)
    _, leituras = next(afinacao.pollings(mudancas, [date(2026, 10, 21)]))
    assert {(l.dispositivo, l.tipo) for l in leituras} >= {
        ("porta", "sensorState"), ("tomada", "instantPower"), ("lampada", "power"), ("camara", "motionDetected")
    }
```

- [ ] **Step 2:** `uv run pytest tests/test_afinacao.py -v` → FAIL.
- [ ] **Step 3:** Mudar `_mudancas`, `pollings` e `folgas` (que passa a ler o tipo). A folga da US09 passa a ser `limite_sem_sinais(dia) - primeiro sinal desse dia`, com os sinais de `habitual.sinais_de_vida(caminho)` nos dias do bloco. Atualizar a docstring.
- [ ] **Step 4:** `uv run pytest` → tudo PASS (a US09 ainda é a da porta: a mudança das leituras não lhe mexe).
- [ ] **Step 5: Commit** — `refactor: afinação com todos os dispositivos do histórico`

---

### Task 5: A regra nova da US09

**Files:**
- Rewrite: `backend/src/backend/regras/us09.py`
- Rewrite: `backend/dados/us09.csv`
- Rewrite: `backend/tests/test_us09.py`
- Modify: `backend/src/backend/ciclo.py` (`NAO_RECONSTRUIR = {"US07"}` e o seu comentário)
- Modify: `backend/tests/test_ciclo_reinicio.py` (`test_us07_e_us09_nao_se_reconstroem` passa a ser só da US07; teste novo da US09)
- Modify: `backend/src/backend/habitual.py`, `backend/tests/test_habitual.py` (remover `primeira_abertura`, `limite_porta_nao_abriu`, `texto_primeira_abertura` e os seus testes: já ninguém os usa)
- Modify: `backend/src/backend/regras/__init__.py` (a docstring: `casa_vazia` e `ferias_agora` continuam a servir a US09)

**Interfaces:**
- Consumes: `sinais.Detetor`, `sinais.comunica`, `sinais.Sinal`; `dispositivos.comandado_ha_pouco`; `habitual.padrao()` e os métodos da Task 3; `regras.casa_vazia`, `regras.ferias_agora`; `_comum.numero`, `_comum.hora`, `_comum.com_fuso`.
- Produces: `verificar(leituras, contexto, agora) -> list[Desvio | Resolucao]` e `reiniciar() -> None` (apaga o estado em SQLite e a memória do detetor).

**Estado:** tabela `estado_us09 (id INTEGER PRIMARY KEY CHECK (id = 1), dados TEXT NOT NULL)`, com um JSON de `Estado(ultimo: Sinal | None, vigia_desde: datetime | None, lida_em: datetime | None, pendente: Desvio | None)`. O `Detetor` (valores anteriores) fica em memória, criado com `comandado=dispositivos.comandado_ha_pouco`: depois de um reinício, a primeira volta é o ponto de partida. Um estado com `lida_em` depois de `agora` (um CSV de outro dia corrido contra esta base de dados) deita-se fora, como na US11. As contas fazem-se com `com_fuso(agora)`; a `Resolucao.em` é o `agora` recebido.

**Algoritmo de `verificar`** (por esta ordem):
1. Sem `comunica(leituras)`: a casa não sabe nada. Devolve `[pendente]` se houver, senão `[]`; não mexe em `lida_em`.
2. Se `lida_em` é None ou `agora - lida_em > US09_LACUNA_MINUTOS`: `vigia_desde = agora` (houve um buraco: o que aconteceu nele não se sabe). `lida_em = agora`.
3. Sinais desta volta (`Detetor.ver`): o último passa a `ultimo`. Se havia `pendente`: limpa-o e devolve `[Resolucao("US09", f"{descricao} às {HH:MM}", agora)]`.
4. `casa_vazia(contexto, agora)`: com `pendente`, limpa-o e devolve `Resolucao` `"a casa ficou vazia (motivo): já não se espera atividade"` (sem o motivo: `"a casa ficou vazia: já não se espera atividade"`); senão `[]`.
5. Com `pendente`: devolve `[pendente]` (o resumo não muda enquanto dura, mesmo depois da meia-noite).
6. **Manhã sem atividade**, se `limite = h.limite_sem_sinais(agora)` existe, `agora.time() >= limite`, não houve sinal hoje (`ultimo` None ou de outro dia) e `vigia_desde <= hoje às h.primeiro_sinal[tipo]` (a casa está a ver desde antes da hora habitual). Resumo: `f"Ainda não houve nenhum sinal de vida hoje até às {limite:%H:%M}. O último foi {descricao} às {quando}."`, onde `quando` é `"23:40 de ontem"` ou `"10:00 de 21/11"`; sem `ultimo`, só a primeira frase. `habitual = h.texto_primeiro_sinal(agora)`.
7. **A atividade parou**, se `ultimo` é de hoje, não é da porta, `h.com_atividade(agora)` e `h.tempo_ativo(max(ultimo.em, vigia_desde), agora) >= US09_HORAS`. Resumo: `f"O último sinal de vida foi {descricao} às {HH:MM} e, desde então, passaram {duracao} sem nenhum, a horas em que costuma haver atividade."` (`duracao` = `habitual.duracao(US09_HORAS)`, ex.: `"3 h"`). `habitual = h.texto_atividade(agora)`.
8. O desvio (classe `bem_estar`, nunca `imediato`) fica em `pendente`. Grava o estado e devolve-o.

- [ ] **Step 1: Escrever `dados/us09.csv`** (exatamente isto; quinta normal, sexta com os dois casos, sábado que sai pela porta, segunda das férias)

```csv
dispositivo,tipo,valor,em
porta,sensorState,normal,2026-11-19T06:50:00
lampada,power,off,2026-11-19T06:50:00
tomada,instantPower,0,2026-11-19T06:50:00
camara,motionDetected,,2026-11-19T06:50:00
lampada,power,on,2026-11-19T07:00:00
lampada,power,off,2026-11-19T07:40:00
porta,sensorState,alarm,2026-11-19T07:40:00
porta,sensorState,normal,2026-11-19T07:41:00
porta,sensorState,alarm,2026-11-19T19:00:00
porta,sensorState,normal,2026-11-19T19:01:00
camara,motionDetected,2026-11-19T19:05:00,2026-11-19T19:05:00
lampada,power,on,2026-11-19T19:10:00
camara,motionDetected,2026-11-19T21:00:00,2026-11-19T21:00:00
camara,motionDetected,2026-11-19T22:30:00,2026-11-19T22:30:00
lampada,power,off,2026-11-19T23:40:00
porta,sensorState,normal,2026-11-20T07:00:00
porta,sensorState,normal,2026-11-20T08:45:00
porta,sensorState,normal,2026-11-20T09:00:00
camara,motionDetected,2026-11-20T11:05:00,2026-11-20T11:05:00
porta,sensorState,normal,2026-11-20T14:30:00
camara,motionDetected,2026-11-20T19:30:00,2026-11-20T19:30:00
porta,sensorState,normal,2026-11-20T21:00:00
porta,sensorState,normal,2026-11-20T22:30:00
porta,sensorState,normal,2026-11-21T00:30:00
lampada,power,on,2026-11-21T07:50:00
camara,motionDetected,2026-11-21T08:10:00,2026-11-21T08:10:00
porta,sensorState,alarm,2026-11-21T10:00:00
porta,sensorState,normal,2026-11-21T10:01:00
porta,sensorState,normal,2026-11-21T14:00:00
porta,sensorState,normal,2026-11-23T07:00:00
porta,sensorState,normal,2026-11-23T08:45:00
porta,sensorState,normal,2026-11-23T09:00:00
```

- [ ] **Step 2: Escrever os testes do CSV** em `tests/test_us09.py`. Um fixture `autouse` põe `US09_LACUNA_MINUTOS=1440` (o CSV tem voltas espaçadas de horas) e `CONTEXTO` tem férias de 23/11 a 29/11 ("férias no Algarve"), como hoje.

```python
def test_casos_da_us09():
    r = Registo(us09, CONTEXTO).correr("us09.csv")
    assert [q for q, _ in r.avaliados] == [datetime(2026, 11, 20, 8, 45), datetime(2026, 11, 20, 22, 30)]
    assert all(d.classe == "bem_estar" and not d.imediato for _, d in r.avaliados)
    assert r.publicadas == [
        (datetime(2026, 11, 20, 8, 45), "ativa", "bem_estar"),
        (datetime(2026, 11, 20, 11, 5), "resolvida", "bem_estar"),
        (datetime(2026, 11, 20, 22, 30), "ativa", "bem_estar"),  # atravessa a meia-noite
        (datetime(2026, 11, 21, 7, 50), "resolvida", "bem_estar"),
    ]
    assert r.resolucoes == ["movimento na câmara às 11:05", "a luz ligada às 07:50"]

def test_resumo_e_habitual():
    r = Registo(us09, CONTEXTO).correr("us09.csv")
    manha, parou = r.avaliados[0][1], r.avaliados[1][1]
    assert manha.resumo == ("Ainda não houve nenhum sinal de vida hoje até às 08:45. "
                            "O último foi a luz desligada às 23:40 de ontem.")
    assert manha.habitual == "Nos dias úteis, o primeiro sinal de vida costuma chegar até às 07:15."
    assert parou.resumo == ("O último sinal de vida foi movimento na câmara às 19:30 e, desde então, "
                            "passaram 3 h sem nenhum, a horas em que costuma haver atividade.")
    assert parou.habitual == habitual.padrao().texto_atividade(datetime(2026, 11, 20, 22, 30))

def test_sem_ferias_avisa_e_diz_o_ultimo_sinal_de_outro_dia():
    r = Registo(us09, Contexto([], [], [], False)).correr("us09.csv")
    assert [q for q, _ in r.avaliados][2:] == [datetime(2026, 11, 23, 8, 45)]
    assert r.avaliados[2][1].resumo.endswith("O último foi a porta aberta às 10:00 de 21/11.")
    assert r.publicadas[4:] == [(datetime(2026, 11, 23, 8, 45), "ativa", "bem_estar")]

def test_casa_vazia_nao_avisa():
    assert Registo(us09, Contexto([], [], [], casa_vazia=True)).correr("us09.csv").avaliados == []
```

O sábado às 14:00 (o último sinal foi a porta) e a sexta às 14:30 (hora sem atividade) não avisam: já está nas listas exatas acima. Manter `test_o_contacto_externo_e_informado_quando_a_porta_abre`, renomeado para `..._quando_ha_um_sinal`, com as linhas de sexta até às 11:05 (o aviso da manhã e o movimento que o resolve): `contacto.chamadas == ["agendar ativa", "resolvida resolvida"]`.

- [ ] **Step 3: Escrever os testes diretos** (chamam `us09.verificar`, numa sexta, 2026-11-20, sem férias; `voltas(*horas)` é uma ajuda do teste que dá uma volta só com a porta fechada a cada hora e devolve a saída da última)

```python
def test_arranque_depois_da_hora_habitual_nao_avisa_de_manha():  # Review Focus 3
    assert us09.verificar(porta_fechada(sexta(9)), SEM_FERIAS, sexta(9)) == []

def test_um_buraco_nas_leituras_de_manha_nao_avisa(monkeypatch):  # Review Focus 3
    monkeypatch.setenv("US09_LACUNA_MINUTOS", "30")
    assert us09.verificar(porta_fechada(sexta(6)), SEM_FERIAS, sexta(6)) == []
    assert us09.verificar(porta_fechada(sexta(9)), SEM_FERIAS, sexta(9)) == []  # 3 h sem ler

def test_um_buraco_nao_conta_como_silencio(monkeypatch):  # Review Focus 3
    # movimento às 19:00, buraco das 19:10 às 21:50, voltas às 22:00 e 22:10: não avisa "parou"

def test_sem_nenhum_dispositivo_a_comunicar_nao_avisa():
    # voltas às 06:00 e 08:00 com a porta; às 08:45 só a temperatura -> []
    # com o desvio já ativo, uma volta só com a temperatura devolve o mesmo desvio, não uma Resolucao

def test_com_a_camara_calada_continua_a_vigiar():
    # voltas só com a porta (a câmara não comunica) às 06:00, 07:00, 08:00, 08:45 -> um Desvio às 08:45

def test_deitar_depois_da_meia_noite_nao_e_atividade_parada():  # Review Focus 4
    # sexta 23:00 movimento; sábado 00:30 luz desligada; voltas a cada hora até às 07:00 de sábado -> []

def test_a_casa_apagar_a_luz_nao_resolve(monkeypatch):  # Review Focus 1
    monkeypatch.setattr(us09.dispositivos, "comandado_ha_pouco", lambda d, t: (d, t) == ("lampada", "power"))
    # luz acesa às 06:00 (volta de partida), desvio às 08:45; a luz apaga às 09:00 -> [o mesmo Desvio]

def test_ferias_a_meio_resolvem_com_o_motivo():
    # desvio às 08:45; às 09:10 com férias a começar às 09:05 ->
    # [Resolucao("US09", "a casa ficou vazia (férias no Algarve): já não se espera atividade", sexta(9, 10))]
    # às 09:20 -> []

def test_o_estado_sobrevive_a_um_reinicio():  # Review Focus 2
    # desvio às 08:45; us09._detetor = sinais.Detetor() (um processo novo); às 09:00 -> [o mesmo Desvio]
    # às 09:05 a luz liga (a volta das 09:00 foi o ponto de partida) -> Resolucao "a luz ligada às 09:05"

def test_um_estado_do_futuro_e_esquecido():
    # um desvio a 2026-11-25 08:45; depois uma volta a 2026-11-20 06:00 -> [], e o estado já não tem o desvio
```

Em `test_ciclo_reinicio.py`, o teste novo:

```python
def test_us09_reconstroi_se_e_nao_volta_a_avisar():  # Review Focus 2
    m = Montagem()
    m.ciclo.restaurar([("US09", m.ativa("US09", classe="bem_estar"))])
    m.saidas[:] = [Desvio(us="US09", classe="bem_estar", resumo="Ainda não houve…", habitual=None)]
    m.ciclo.passo([], AGORA)
    assert m.avaliadas == [] and m.publicadas == []
```

- [ ] **Step 4:** `uv run pytest tests/test_us09.py tests/test_ciclo_reinicio.py -v` → FAIL.
- [ ] **Step 5:** Reescrever `regras/us09.py` com o estado e o algoritmo acima. `US09_HORAS` e `US09_LACUNA_MINUTOS` leem-se com `_comum.numero` em cada volta (a demo muda-os no ambiente). Docstring: os dois casos, o que não conta, a casa vazia, os dispositivos calados, "vou ficar em casa" não cala, o reinício. Mudar `NAO_RECONSTRUIR` e o seu comentário. Remover de `habitual.py` o que era da porta para a US09 e os seus testes, e o argumento `primeira_abertura={}` de `test_tempo_ativo_so_conta_as_horas_com_atividade`.
- [ ] **Step 6:** `uv run pytest` → tudo PASS, incluindo `test_afinacao.py` (0 falsos alarmes e folgas ≥ 0 com a regra nova sobre o histórico novo). Se a afinação der falsos alarmes da US09, mostra-os `uv run python scripts/afinar.py`: o histórico gerado tem um silêncio de mais de 3 h com a pessoa em casa, a corrigir no gerador (Task 3), não na regra.
- [ ] **Step 7: Commit** — `feat: US09 passa a vigiar os sinais de vida da casa`

---

### Task 6: Textos e documentação que ainda falam da porta

**Files:**
- Modify: `backend/src/backend/ia/avaliar.py` (`SISTEMA`)
- Modify: `backend/src/backend/resposta/padrao.py` (`DESCRICAO_POR_US["US09"] = "a casa acorda mais tarde"`)
- Modify: `backend/src/backend/historico.py` (tirar a US09 de `DISPOSITIVO_POR_US`: vários dispositivos, fica `"Casa"`)
- Modify: `backend/README.md` (linhas da US09, de `ciclo.py` — a US09 já se reconstrói — e de `habitual.py`), `AGENTS.md` ("Current state": `sinais.py`; o histórico tem a câmara e a lâmpada; a US09 vigia sinais de vida)
- Test: `backend/tests/test_avaliar.py`

- [ ] **Step 1: Escrever o teste**

```python
def test_ficar_em_casa_nao_explica_a_falta_de_sinais_de_vida():
    assert "ficar em casa" in SISTEMA and "sinais de vida" in SISTEMA
```

- [ ] **Step 2:** `uv run pytest tests/test_avaliar.py -v -k ficar` → FAIL.
- [ ] **Step 3:** Acrescentar a `SISTEMA` uma linha: `- A falta de sinais de vida (US09) nunca se explica por a pessoa ter dito que ia ficar em casa: é com ela em casa que uma queda pode acontecer.` Mudar os outros textos e os documentos. Procurar o que sobra com `grep -rn "porta não abriu\|porta ainda não\|primeira_abertura" src tests ../AGENTS.md README.md` → nada.
- [ ] **Step 4:** `uv run pytest` → tudo PASS; `uv run python scripts/afinar.py` mostra a US09 com 0 falsos alarmes.
- [ ] **Step 5: Commit** — `docs: a US09 nos textos da IA, da resposta e da documentação`
