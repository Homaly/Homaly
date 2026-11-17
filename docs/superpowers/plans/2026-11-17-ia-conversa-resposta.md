# IA, conversa e resposta (Simão: US01, US02) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A parte do Simão no backend: os formatos da secção 1 da `DIVISAO.md`, `ia.avaliar()` atrás de um modelo trocável, a conversa (US01, `/conversa`, `Contexto` guardado em SQLite) e a resposta às anomalias com proposta de silêncio (US02).

**Architecture:** Assenta no backend do Benny (commit `0f08a8d`): `backend.main:app`, `contrato.py` (a `Anomalia` e os outros modelos do `contract.ts`), `db.py` (um SQLite; cada módulo regista as suas tabelas com `db.esquema` e usa `with db.ligar() as con:`) e `anomalias.obter/guardar`. Cada parte do Simão é um subpacote com funções testáveis e, quando expõe pedidos, um `APIRouter` com uma linha em `main.py`. O fornecedor de IA fica atrás de um `Protocol` `Modelo`; por agora só existe `ModeloFalso` (devolve `None`) e todo o código cai num recurso determinístico quando o modelo não responde. O fornecedor real escolhe-se depois (decisão do Simão, 2026-11-17).

**Tech Stack:** Python 3.12, uv, FastAPI e pydantic v2 (já no `pyproject.toml`), sqlite3 via `backend.db`, pytest, httpx (TestClient).

**Spec:** `DIVISAO.md` na versão do commit `e1b7093` (secção 1, formatos fixados na reunião de terça, com `contacto_externo.resolvida`; secção 2, "toda a mudança a uma anomalia passa por `avisos.publicar`"; secção 3, Simão e a US14 da Vila); `USER_STORIES.md` (US01, US02); `DECISIONS.md` ("Silenciar avisos depois de uma resposta", "Proposta de silêncio"); `docs/frontend-design.md` (pedidos); `backend/README.md` ("Como ligar o teu módulo"); `backend/src/backend/contrato.py`.

## Global Constraints

- Comandos a partir de `backend/`: `uv run pytest`.
- Nomes de código em português. Os formatos da secção 1 exatamente como lá estão (nomes e campos).
- **Não duplicar o que o Benny fez.** A `Anomalia`, `AcaoProposta`, `TextoEm`, `PropostaSilencio`, `MensagemConversa`, `Classe`, `agora()` e `novo_id()` vêm de `backend.contrato`. Em Python os campos são snake_case (`detetada_em`, `acao_proposta`, `proposta_silencio`); para JSON usa-se `para_json()` ou `response_model_exclude_none=True`.
- **Datas sempre com fuso**, como no `contrato.py` (`Instante`, `agora()`). Nos testes: `LX = ZoneInfo("Europe/Lisbon")` e `datetime(..., tzinfo=LX)`. No SQLite guardam-se em ISO com o offset.
- **Base de dados só através de `backend.db`:** `db.esquema("CREATE TABLE IF NOT EXISTS ...")` no módulo, `with db.ligar() as con:` para ler e escrever. Não abrir ligações próprias.
- Toda a função que depende da hora recebe `agora: datetime` explícito.
- Nunca chamar um fornecedor de IA real; nunca escrever chaves em código. Variável nova: `IA_FORNECEDOR` (por omissão `falso`).
- Nos ficheiros do Benny (`main.py`, `contrato.py`, `anomalias.py`, `db.py`, `README.md`) só se mexe onde uma task o diz.
- Trabalhar num ramo próprio, não no `main`. Commits pequenos, mensagem em português (`feat: ...`), sempre com o trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Não fazer push sem o OK do Simão.

## Review Focus

1. **O modelo devolve lixo** (JSON com chaves em falta, tipos errados, `None`): nunca um erro 500; cai no recurso determinístico. Testes nas Tasks 2, 4 e 5.
2. **Silêncio expirado** (`ate` antes de `agora`) não pode calar um desvio. Teste na Task 2.
3. **Férias com `fim` antes de `inicio`** ou datas inválidas vindas do modelo: a casa diz que não percebeu e não guarda nada. Teste na Task 4.
4. **Responder duas vezes, ou aceitar o silêncio duas vezes ou sem proposta:** 409, sem mudar nada. Testes na Task 5.
5. **Anomalia de segurança com motivo temporário:** fica resolvida só a ocorrência, sem proposta de silêncio. Teste na Task 5.

---

### Task 1: Formatos, modelo trocável e testes a correr

**Files:**
- Modify: `backend/pyproject.toml`, `backend/uv.lock` (via `uv add --dev pytest httpx`; `[tool.pytest.ini_options] testpaths = ["tests"]`)
- Create: `backend/src/backend/formatos.py`
- Create: `backend/src/backend/ia/__init__.py`, `backend/src/backend/ia/modelo.py`
- Create: `backend/tests/__init__.py` (vazio), `backend/tests/conftest.py`, `backend/tests/test_formatos.py`, `backend/tests/test_modelo.py`
- Modify: `.env.example` (raiz)

**Interfaces:**
- Produces (`backend.formatos`): as dataclasses `Leitura`, `Periodo`, `Rotina`, `Silencio`, `Contexto`, `Desvio` exatamente como na secção 1 da `DIVISAO.md`, com `Classe` importada de `backend.contrato`. Única extensão: `Contexto` ganha no fim `aparelho_tomada: str | None = None` (o nome do aparelho dito na conversa, para a US14 da Vila); com valor por omissão, quem constrói `Contexto` com os quatro campos não parte.
- Produces (`backend.ia.modelo`): `class Modelo(Protocol): def completar_json(self, sistema: str, mensagem: str) -> dict | None`; `class ModeloFalso` (devolve sempre `None`); `def obter_modelo() -> Modelo` (lê `IA_FORNECEDOR`; `"falso"` ou ausente → `ModeloFalso`; outro valor → `ValueError`). O nome `Modelo` colide com `contrato.Modelo` (a base pydantic); quem precisar dos dois importa um com alias.
- Produces (`tests/conftest.py`):
  - `class ModeloFixo` com `__init__(self, resposta: dict | None)`; guarda as chamadas em `self.chamadas: list[tuple[str, str]]` e devolve `resposta`.
  - fixture `bd` (autouse): `monkeypatch.setattr(db, "CAMINHO", str(tmp_path / "teste.db"))` e `monkeypatch.setattr(db, "_aplicados", 0)`, para cada teste ter um ficheiro novo com todas as tabelas registadas.
  - `LX = ZoneInfo("Europe/Lisbon")` e `AGORA = datetime(2026, 11, 17, 15, 0, tzinfo=LX)` (uma terça-feira).

- [ ] **Step 0:** `git pull --rebase`. Se `backend/src/backend/formatos.py` já existir (outra pessoa pode tê-lo criado), usá-lo e acrescentar só o que falta, sem mudar o que lá está.
- [ ] **Step 1:** `uv add --dev pytest httpx` e a secção do pytest no `pyproject.toml`.
- [ ] **Step 2: testes que falham**

```python
# tests/test_formatos.py
def test_desvio_imediato_por_omissao_falso():
    d = Desvio(us="US08", classe="seguranca", resumo="r", habitual=None)
    assert d.imediato is False

def test_contexto_com_quatro_campos_continua_a_funcionar():
    assert Contexto([], [], [], False).aparelho_tomada is None

# tests/test_modelo.py
def test_obter_modelo_por_omissao_e_falso(monkeypatch):
    monkeypatch.delenv("IA_FORNECEDOR", raising=False)
    assert obter_modelo().completar_json("s", "m") is None

def test_obter_modelo_desconhecido_falha(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "xpto")
    with pytest.raises(ValueError):
        obter_modelo()
```

- [ ] **Step 3:** `uv run pytest` → FAIL (import errors).
- [ ] **Step 4:** Implementar `formatos.py`, `ia/modelo.py`, `conftest.py`. `ia/__init__.py` fica vazio por agora (a Task 2 exporta `avaliar`).
- [ ] **Step 5:** `uv run pytest` → PASS.
- [ ] **Step 6:** Em `.env.example`, nova secção `# --- IA ---` com `IA_FORNECEDOR=falso` e o comentário `# falso: sem modelo, a casa usa o resumo do desvio. O fornecedor real escolhe-se depois.`
- [ ] **Step 7: Commit** `feat: formatos partilhados e modelo de IA trocável`

### Task 2: `ia.avaliar()`

**Files:**
- Create: `backend/src/backend/ia/avaliar.py`; Modify: `backend/src/backend/ia/__init__.py` (`from .avaliar import avaliar`)
- Test: `backend/tests/test_avaliar.py`

**Interfaces:**
- Consumes: `Desvio`, `Contexto`, `Silencio` (Task 1); `Anomalia`, `AcaoProposta` de `backend.contrato`; `Modelo`, `obter_modelo` (Task 1).
- Produces: `def avaliar(desvio: Desvio, contexto: Contexto, *, agora: datetime | None = None, modelo: Modelo | None = None) -> Anomalia | None`. `agora=None` → `contrato.agora()`; `modelo=None` → `obter_modelo()`.
- Produces: `def us_da_anomalia(anomalia_id: str) -> str | None` (no mesmo ficheiro). A `Anomalia` do contrato não tem a user story que a gerou, e a US02 precisa dela para silenciar. `avaliar` regista o par numa tabela própria, `anomalia_us (anomalia_id TEXT PRIMARY KEY, us TEXT NOT NULL)`, registada com `db.esquema`, sempre que devolve uma `Anomalia`.

Regras (por esta ordem):
1. Se algum `Silencio` do contexto tem `us == desvio.us` e (`ate is None` ou `agora <= ate`) → `None`, sem chamar o modelo.
2. Chama `modelo.completar_json(SISTEMA, mensagem)`; a mensagem leva o desvio (us, classe, resumo, habitual, imediato), o contexto (férias, rotinas, casa_vazia, aparelho_tomada) e `agora`. O `SISTEMA` (constante em português) pede JSON `{"avisar": bool, "titulo": str, "explicacao": str, "acao": str | null}` e explica: título curto; explicação em português simples com o que aconteceu e o que é habitual; não inventar factos fora do resumo; `acao` só se houver algo que a casa possa fazer (apagar a lâmpada, desligar a tomada).
3. Resposta válida = dict com `avisar` bool, `titulo` e `explicacao` strings não vazias, `acao` string ou `None`/ausente. Válida, `avisar is False` e não `imediato` → `None`.
4. Resposta inválida ou `None` → recurso: `titulo = TITULO_POR_CLASSE[desvio.classe]`, `explicacao = resumo` (+ `" Habitual: " + habitual` se houver), sem ação.
5. Com `imediato=True` devolve sempre `Anomalia`, mesmo com `avisar: false` (só se usa o texto).
6. `Anomalia(classe=desvio.classe, titulo=..., explicacao=..., detetada_em=agora, acao_proposta=...)`; o `id` vem do `novo_id()` do contrato.

`TITULO_POR_CLASSE = {"seguranca": "Alerta de segurança", "bem_estar": "A rotina mudou", "saude_conforto": "Conforto da casa", "eficiencia": "Energia a mais"}`.

- [ ] **Step 1: testes que falham** (usar `ModeloFixo` e `AGORA`; `contexto_vazio = Contexto([], [], [], False)`)
  - `test_modelo_decide_avisar`: resposta `{"avisar": True, "titulo": "Porta aberta", "explicacao": "x", "acao": None}` → `titulo == "Porta aberta"`, `explicacao == "x"`, `acao_proposta is None`, `estado == "ativa"`, `detetada_em == AGORA`, `us_da_anomalia(a.id) == "US08"`.
  - `test_modelo_decide_nao_avisar`: `{"avisar": False, ...}` → `None`.
  - `test_imediato_avisa_mesmo_que_modelo_diga_que_nao`: desvio `imediato=True`, `{"avisar": False, "titulo": "T", "explicacao": "E"}` → Anomalia com `titulo == "T"`.
  - `test_sem_modelo_usa_resumo`: `ModeloFixo(None)`, desvio `classe="eficiencia", resumo="Luz acesa há 5 h.", habitual="Costuma estar acesa 1 h."` → `titulo == "Energia a mais"`, `explicacao == "Luz acesa há 5 h. Habitual: Costuma estar acesa 1 h."`.
  - `test_resposta_malformada_usa_resumo`: `{"avisar": "sim"}` → título do recurso.
  - `test_acao_proposta`: `"acao": "Apagar a lâmpada"` → `acao_proposta.descricao == "Apagar a lâmpada"`.
  - `test_silencio_ativo_cala_sem_chamar_modelo`: `Silencio("US08", AGORA + timedelta(hours=1), "m")` → `None` e `modelo.chamadas == []`.
  - `test_silencio_permanente_cala`: `ate=None` → `None`.
  - `test_silencio_expirado_nao_cala`: `ate = AGORA - timedelta(minutes=1)` → Anomalia.
  - `test_silencio_de_outra_us_nao_cala`: `us="US10"` → Anomalia.
  - `test_us_desconhecida`: `us_da_anomalia("nao-existe") is None`.
- [ ] **Step 2:** `uv run pytest tests/test_avaliar.py` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest` → PASS.
- [ ] **Step 5: Commit** `feat: ia.avaliar com recurso ao resumo do desvio`
- [ ] **Paragem:** depois desta task, parar e perguntar ao Simão se faz push, para os formatos e o `ia.avaliar()` chegarem à junção das 18:00 (o ciclo da Vila chama-os).

### Task 3: Guardar e carregar o `Contexto`

**Files:**
- Create: `backend/src/backend/contexto/__init__.py`, `backend/src/backend/contexto/repositorio.py`
- Test: `backend/tests/test_contexto.py`

**Interfaces:**
- Consumes: `Periodo`, `Rotina`, `Silencio`, `Contexto` (Task 1); `MensagemConversa` de `backend.contrato`; `backend.db`.
- Produces (`backend.contexto.repositorio`), sem parâmetro de ligação (cada função abre `with db.ligar() as con:`):
  - Tabelas registadas com `db.esquema`: `ferias`, `rotinas`, `silencios`, `mensagens`, `aparelho_tomada` (uma só linha), `propostas_silencio` (`anomalia_id TEXT PRIMARY KEY, dados TEXT` com JSON; usada na Task 5).
  - `guardar_periodo(p: Periodo) -> None`, `guardar_rotina(r: Rotina) -> None`, `guardar_silencio(s: Silencio) -> None`
  - `guardar_aparelho(nome: str) -> None` — substitui o anterior (só há uma tomada).
  - `carregar_contexto(agora: datetime) -> Contexto` — `casa_vazia` é `True` se `agora` cai dentro de algum período de férias (`inicio <= agora <= fim`). Devolve todos os períodos, rotinas e silêncios (filtrar os expirados é de quem os lê) e `aparelho_tomada` (ou `None`).
  - `guardar_mensagem(m: MensagemConversa) -> None`, `listar_mensagens() -> list[MensagemConversa]` (por `em`, crescente).
  - `guardar_proposta(anomalia_id: str, dados: dict) -> None`, `ler_proposta(anomalia_id: str) -> dict | None`, `apagar_proposta(anomalia_id: str) -> None`.
- Datas em ISO com offset; `Rotina.dias` em JSON; `hora` como `"HH:MM"` ou NULL.

- [ ] **Step 1: testes que falham** (a fixture `bd` dá um ficheiro novo a cada teste)
  - `test_contexto_vazio`: `carregar_contexto(AGORA) == Contexto([], [], [], False)`.
  - `test_ferias_dentro_do_periodo_casa_vazia`: período 17→24 nov (com `LX`), `agora` 20 nov → `casa_vazia is True` e o período volta igual (round-trip de datas com fuso).
  - `test_ferias_fora_do_periodo`: `agora` 25 nov → `casa_vazia is False`.
  - `test_rotina_round_trip`: `Rotina("empregada", [1], time(14, 0))` e `Rotina("x", [0, 2], None)` voltam iguais.
  - `test_silencio_round_trip`: com `ate` e com `ate=None`.
  - `test_aparelho_substitui`: `guardar_aparelho("aquecedor")` e depois `"desumidificador"` → `aparelho_tomada == "desumidificador"`.
  - `test_mensagens_por_ordem`: guardar duas fora de ordem, `listar_mensagens` devolve por `em`.
  - `test_proposta_guardar_ler_apagar`: round-trip do dict; depois de apagar, `None`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** `uv run pytest` → PASS.
- [ ] **Step 5: Commit** `feat: contexto da casa guardado em SQLite`

### Task 4: Conversa (US01) e `/conversa`

**Files:**
- Create: `backend/src/backend/conversa/__init__.py`, `backend/src/backend/conversa/interpretar.py`, `backend/src/backend/conversa/router.py`
- Create: `backend/src/backend/dependencias.py`
- Modify: `backend/src/backend/main.py` (uma linha: `app.include_router(conversa.router)`)
- Test: `backend/tests/test_interpretar.py`, `backend/tests/test_conversa_api.py`

**Interfaces:**
- Consumes: Task 1 (`Modelo`, `obter_modelo`, formatos), Task 3 (`guardar_periodo`, `guardar_rotina`, `guardar_aparelho`, `guardar_mensagem`, `listar_mensagens`); `MensagemConversa` e `agora` de `backend.contrato`.
- Produces (`backend.dependencias`): `def obter_modelo_dep() -> Modelo` (chama `obter_modelo()`) e `def obter_agora() -> datetime` (chama `contrato.agora()`). Os testes substituem-nas com `app.dependency_overrides`.
- Produces (`backend.conversa.interpretar`): `@dataclass Interpretacao(resposta: str, periodo: Periodo | None = None, rotina: Rotina | None = None, aparelho: str | None = None)` e `def interpretar(texto: str, agora: datetime, modelo: Modelo) -> Interpretacao`.
- Produces (`backend.conversa.router`): `router = APIRouter(tags=["conversa"])` com `GET /conversa -> list[MensagemConversa]` e `POST /conversa` corpo `{"texto": str}` `-> MensagemConversa` (a resposta da casa), ambos com `response_model_exclude_none=True`.

`interpretar`: o `SISTEMA` diz a data e o dia da semana de `agora` (para "amanhã", "terças") e pede um destes JSON:
- `{"tipo": "ferias", "inicio": ISO, "fim": ISO, "motivo": str, "resposta": str}` — datas sem fuso recebem o fuso de `agora`.
- `{"tipo": "rotina", "descricao": str, "dias": [int 0..6, 0 = segunda], "hora": "HH:MM" | null, "resposta": str}`
- `{"tipo": "aparelho", "nome": str, "resposta": str}` — "na tomada está o aquecedor" (US14)
- `{"tipo": "nao_percebi"}`

Válido → `Interpretacao(resposta=<resposta do modelo>, periodo|rotina|aparelho=...)`. Qualquer outra coisa (None, tipo desconhecido, datas que não se leem, `fim <= inicio`, dias fora de 0..6 ou lista vazia, hora inválida, nome do aparelho vazio) → `Interpretacao(resposta=NAO_PERCEBI)` com `NAO_PERCEBI = "Não percebi bem. Podes dizer de outra forma?"`.

`POST /conversa`: guarda a mensagem da pessoa, interpreta, guarda o período, a rotina ou o aparelho se houver, guarda e devolve a mensagem da casa (`em = agora`). Texto vazio ou só espaços → 422.

- [ ] **Step 1: testes que falham** (`AGORA` é terça, 17 nov, 15:00)
  - `test_ferias`: modelo devolve férias 18→25 nov com `resposta "Boas férias! Até dia 25."` → `periodo.inicio == datetime(2026,11,18,tzinfo=LX)`, `periodo.fim == datetime(2026,11,25,tzinfo=LX)`, `resposta` igual; a mensagem enviada ao modelo contém `"2026-11-17"` e `"terça"`.
  - `test_rotina`: `dias [1], hora "14:00"` → `Rotina(..., [1], time(14, 0))`.
  - `test_rotina_sem_hora`: `hora None` → `rotina.hora is None`.
  - `test_aparelho`: `{"tipo": "aparelho", "nome": "aquecedor", "resposta": "Combinado."}` → `aparelho == "aquecedor"`; `nome ""` → `NAO_PERCEBI`.
  - `test_nao_percebi`, `test_modelo_sem_resposta`, `test_ferias_ao_contrario` (`fim` antes de `inicio`), `test_dia_invalido` (`dias [7]`), `test_data_ilegivel` (`inicio "amanhã"`) → `resposta == NAO_PERCEBI`, sem período, rotina nem aparelho.
  - API (`TestClient(app)` com `backend.main.app` e overrides para `ModeloFixo` e `AGORA`):
    - `test_post_conversa_ferias_guarda_contexto`: POST → 200, `autor == "casa"`; depois `carregar_contexto(datetime(2026,11,20,tzinfo=LX)).casa_vazia is True`; `GET /conversa` devolve 2 mensagens, `pessoa` e depois `casa`.
    - `test_post_conversa_aparelho_guarda_contexto`: depois do POST, `carregar_contexto(AGORA).aparelho_tomada == "aquecedor"`.
    - `test_post_conversa_nao_percebi_nao_guarda`: `ModeloFixo(None)` → texto `NAO_PERCEBI`, contexto vazio.
    - `test_post_conversa_texto_vazio`: `{"texto": "   "}` → 422.
- [ ] **Step 2:** FAIL. **Step 3:** implementar e acrescentar a linha em `main.py`. **Step 4:** `uv run pytest` → PASS.
- [ ] **Step 5: Commit** `feat: conversa com a casa (US01)`

### Task 5: Resposta às anomalias e proposta de silêncio (US02)

**Files:**
- Create: `backend/src/backend/resposta/__init__.py`, `backend/src/backend/resposta/responder.py`, `backend/src/backend/resposta/router.py`
- Modify: `backend/src/backend/main.py` (uma linha: `app.include_router(resposta.router)`)
- Modify (só no Step 5, com OK): `backend/src/backend/contrato.py`, `frontend/src/types/contract.ts`, `docs/frontend-design.md`
- Test: `backend/tests/test_responder.py`, `backend/tests/test_resposta_api.py`

**Interfaces:**
- Consumes: Tasks 1, 2 (`us_da_anomalia`), 3 (`guardar_silencio`, `guardar_rotina`, `guardar_proposta`, `ler_proposta`, `apagar_proposta`), 4 (`dependencias`); `backend.anomalias.obter`; `Anomalia`, `TextoEm`, `PropostaSilencio` de `backend.contrato`.
- Produces (`backend.resposta.router`): `def obter_publicar() -> Callable[[Anomalia], None]` — **toda a mudança a uma anomalia passa por `avisos.publicar`** (`DIVISAO.md`): devolve `backend.avisos.publicar` se o módulo existir (`try: import ... except ImportError`), senão uma função que faz o que o `backend/README.md` descreve: `anomalias.guardar(a)` e `tempo_real.enviar_anomalia(a)`. É o `publicar` da Vila que chama `contacto_externo.resolvida` (pára o tempo de espera e, se já houve SMS, envia a de resolvido). Este módulo não chama `contacto_externo` diretamente.
- Produces (`backend.resposta.responder`):
  - `@dataclass Decisao(anomalia: Anomalia, proposta: dict | None)` — `proposta` é o que se aplica se for aceite: `{"tipo": "silencio", "us", "ate": ISO, "motivo"}` ou `{"tipo": "rotina", "descricao", "dias", "hora"}`.
  - `def responder(anomalia: Anomalia, us: str | None, texto: str, agora: datetime, modelo: Modelo) -> Decisao`
  - `def aplicar(proposta: dict) -> None` (guarda o `Silencio` ou a `Rotina`).
- Produces: `router = APIRouter(prefix="/anomalias", tags=["anomalias"])` com `POST /{id}/resposta` `{"texto": str}` e `POST /{id}/silencio` `{"aceitar": bool}`, ambos `-> Anomalia` com `response_model_exclude_none=True`.

`responder`: pede ao modelo `{"motivo": "nenhum" | "temporario" | "recorrente", "rotina": {"descricao", "dias", "hora"} | null}`, dizendo-lhe a anomalia e o texto. A anomalia fica sempre `estado="resolvida"`, `resposta=TextoEm(texto, agora)`, `resolucao=TextoEm("Resolvida por quem responde: " + texto, agora)`. Depois:
- `nenhum`, modelo sem resposta ou inválida → sem proposta.
- `temporario`, classe **não** `seguranca` e `us` conhecida → `proposta_silencio = PropostaSilencio(texto=f"Não volto a avisar sobre «{titulo}» até ao fim do dia, ok?", ate=agora.replace(hour=23, minute=59, second=59, microsecond=0), estado="pendente")`; proposta `silencio` com essa `us` e `motivo = texto`. Com `us` desconhecida (anomalia criada à mão em `/dev`) → sem proposta.
- `temporario` e classe `seguranca` → sem proposta (DECISIONS: segurança nunca silenciada para além da ocorrência sem regra recorrente).
- `recorrente` com rotina válida (mesmas regras da Task 4) → `proposta_silencio` com `texto=f"Passo a contar com isto: {descricao}. Não aviso enquanto não o removeres, ok?"` e proposta `rotina`. Enquanto o Step 5 não estiver feito, `ate` é obrigatório no contrato: usar `ate = agora.replace(year=agora.year + 10)` como "sem fim", e trocar por `None` no Step 5. Rotina inválida → sem proposta.

Router:
- `/resposta`: 404 se `anomalias.obter(id)` é `None`; 409 se `estado != "ativa"`; texto vazio → 422. Chama `responder(anomalia, us_da_anomalia(id), ...)`, guarda a proposta (`guardar_proposta`) se houver e chama `publicar(anomalia)` uma vez (a anomalia já vai `resolvida`).
- `/silencio`: 404 se não existe; 409 se não há `proposta_silencio` pendente. `aceitar=true` → `aplicar` + estado `aceite`; `false` → `recusada`. Em ambos apaga a proposta guardada e chama `publicar(anomalia)`.
- O `publicar` entra com `Depends(obter_publicar)`; nos testes é substituído por uma função que chama `anomalias.guardar` e regista as chamadas numa lista.

- [ ] **Step 1: testes que falham** (`AGORA`; anomalia `classe="bem_estar"`, `titulo="A porta não abriu"`, gravada com `anomalias.guardar` e com `us` `"US09"` registada como na Task 2)
  - `test_sem_motivo_resolve_sem_proposta`: `{"motivo": "nenhum"}` → `estado == "resolvida"`, `resposta.texto == "está tudo bem"`, `proposta_silencio is None`, `proposta is None`.
  - `test_modelo_sem_resposta_resolve_sem_proposta`: `ModeloFixo(None)`.
  - `test_temporario_propoe_silencio_ate_fim_do_dia`: `ate == datetime(2026,11,17,23,59,59,tzinfo=LX)`, `estado == "pendente"`, texto contém `«A porta não abriu»`; `proposta["tipo"] == "silencio"`, `proposta["us"] == "US09"`.
  - `test_temporario_sem_us_nao_propoe`: `us=None` → sem proposta.
  - `test_temporario_em_seguranca_nao_propoe`: classe `seguranca` → sem proposta.
  - `test_recorrente_propoe_rotina`: `rotina {"descricao": "a empregada vem às terças à tarde", "dias": [1], "hora": "14:00"}` → `proposta["tipo"] == "rotina"` e há `proposta_silencio` pendente.
  - `test_recorrente_em_seguranca_propoe`: classe `seguranca` → há proposta.
  - `test_aplicar_silencio_e_rotina`: `aplicar` e `carregar_contexto` mostra o `Silencio("US09", ...)` / a `Rotina`.
  - API (`TestClient(backend.main.app)`, overrides para publicar, modelo, agora):
    - `test_resposta_e_aceitar_silencio`: POST resposta (temporário) → 200 com `propostaSilencio.estado == "pendente"`; `publicar` chamado uma vez, com `estado == "resolvida"`; POST silencio `{"aceitar": true}` → `propostaSilencio.estado == "aceite"`; `avaliar(desvio US09, carregar_contexto(AGORA), agora=AGORA, modelo=ModeloFixo(None)) is None`.
    - `test_recusar_silencio_nao_aplica`: `aceitar false` → `recusada`, contexto sem silêncios.
    - `test_responder_duas_vezes_409`, `test_silencio_sem_proposta_409`, `test_aceitar_duas_vezes_409`, `test_anomalia_inexistente_404` (nos dois pedidos).
- [ ] **Step 2:** FAIL. **Step 3:** implementar e acrescentar a linha em `main.py`. **Step 4:** `uv run pytest` → PASS.
- [ ] **Step 5 (só com OK do Simão, que o combina com o Benny):** `PropostaSilencio.ate` passa a opcional: `ate: Instante | None = None` em `contrato.py`; `ate?: string;` em `contract.ts` com o comentário `/** ISO 8601: até quando a casa deixa de avisar; sem valor, até o responsável remover (rotina). */`; o mesmo em `docs/frontend-design.md`. Na proposta `rotina`, `ate=None`, e o teste `test_recorrente_propoe_rotina` passa a verificar `proposta_silencio.ate is None`. Correr `uv run pytest` e `npm run build` em `frontend/` → sem erros.
- [ ] **Step 6: Commit** `feat: resposta às anomalias e proposta de silêncio (US02)`

### Task 6: Documentação do estado

**Files:** Modify `backend/README.md` (tabela "Módulos": `formatos.py`, `ia/`, `contexto/`, `conversa/`, `resposta/`, `dependencias.py`; tabela "Variáveis": `IA_FORNECEDOR`; secção "Testes": `uv run pytest`) e `AGENTS.md` ("Current state": a IA atrás de um modelo falso, `/conversa`, `/resposta` e `/silencio`; "Tests": pytest no backend).

- [ ] **Step 1:** atualizar os dois ficheiros (AGENTS.md em inglês, README em português).
- [ ] **Step 2:** `uv run pytest` → tudo PASS.
- [ ] **Step 3: Commit** `docs: estado do backend (IA, conversa, resposta)`

## A combinar com a equipa (não é código)

- **Com Benny:** a `DIVISAO.md` ainda diz que ele chama `contacto_externo.cancelar` "quando o responsável responde", mas esse pedido (`/resposta`) é do Simão, e responder resolve sempre a anomalia, por isso o `publicar` → `resolvida` da Vila já pára a espera. Propor tirar essa linha (ou ele explicar para que serve o `cancelar`). O `ate` opcional em `contrato.py` e `contract.ts` (Task 5, Step 5).
- **Com Vila:** o `publicar` dela também é chamado pelos pedidos `/resposta` e `/silencio`, com anomalias que já existem; o nome do aparelho para a US14 vem em `contexto.aparelho_tomada`. A user story de cada anomalia fica na tabela `anomalia_us`, escrita pelo `ia.avaliar`; se o ciclo dela publicar sem passar pelo `avaliar` (recurso), tem de a registar também, ou a US02 não consegue propor silêncio.
- **Com Vila e Xuta:** `carregar_contexto` só põe `casa_vazia` com férias. O alarme armado em modo ausente também conta (DECISIONS); combinar quem o lê (Xuta lê o alarme) e quem o junta ao `casa_vazia`.
- **Com toda a equipa:** `Contexto.aparelho_tomada` (campo novo, com valor por omissão); `formatos.py` é o ficheiro único com os formatos da secção 1; os testes do backend usam a fixture `bd` do `tests/conftest.py`.
- **Fica de fora:** remover uma rotina (US02 "até eu o remover"; não há pedido no contrato); o fornecedor real de IA.
