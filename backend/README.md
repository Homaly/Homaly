# Backend

A API do Homaly em FastAPI, com uma base de dados SQLite e o WebSocket que avisa a PWA. O contrato com a PWA está em `docs/frontend-design.md` e `frontend/src/types/contract.ts`.

## Arrancar

Com Docker, a partir da raiz do repositório (o backend fica em http://localhost:8000):

```bash
docker compose up --build
```

Sem Docker, a partir de `backend/`:

```bash
uv sync
HOMALY_DEV=1 uv run backend
```

A documentação dos pedidos, onde se pode experimentá-los, fica em http://localhost:8000/docs.

## Variáveis

| Variável | Para quê | Por omissão |
|----------|----------|-------------|
| `DB_PATH` | O ficheiro SQLite | `homaly.db`, na pasta onde o backend arranca |
| `HOMALY_DEV` | Com `1`, liga os pedidos `/dev` | Desligado; o `docker-compose.yml` liga-o |

## Módulos

| Ficheiro | O quê |
|----------|-------|
| `main.py` | A app (`backend.main:app`). Cada pessoa acrescenta aqui uma linha com o seu router. |
| `contrato.py` | O contrato com a PWA (`Anomalia`, `Evento`, ...), igual ao `contract.ts`. Em Python os campos são snake_case; no JSON saem em camelCase. |
| `db.py` | A ligação ao SQLite. |
| `anomalias.py` | A tabela das anomalias, `guardar`, `obter`, `listar`; `GET /anomalias` e `GET /anomalias/{id}`. |
| `eventos.py` | A tabela dos eventos, `registar`, `listar`; `GET /eventos`. |
| `tempo_real.py` | O WebSocket `/ws`; `enviar_anomalia` e `enviar_evento`. |
| `dev.py` | `/dev`: pôr anomalias e eventos à mão, enquanto o ciclo das regras não existe. |

## Como ligar o teu módulo

**As tuas tabelas.** Regista-as no teu módulo; são criadas na primeira ligação:

```python
from backend import db

db.esquema("CREATE TABLE IF NOT EXISTS definicoes (...)")

with db.ligar() as con:      # commit no fim do bloco, rollback se houver exceção
    con.execute("INSERT INTO definicoes ...", (...))
```

**Publicar uma anomalia** (o que faz o `avisos.publicar`):

```python
from backend import anomalias, tempo_real
from backend.contrato import AcaoProposta, Anomalia

a = Anomalia(
    classe="eficiencia",
    titulo="Luz da sala acesa há 5 horas",
    explicacao="...",
    acao_proposta=AcaoProposta(descricao="Apagar a luz da sala"),
)                              # id e detetada_em são preenchidos sozinhos
anomalias.guardar(a)           # guardar com o mesmo id atualiza
tempo_real.enviar_anomalia(a)  # pode chamar-se de qualquer thread
```

**Um evento do histórico:** `eventos.registar(Evento(dispositivo="Porta da rua", descricao="Abriu"))` grava-o e envia-o pelo WebSocket.

**Os teus pedidos.** Um `APIRouter` no teu módulo, e uma linha em `main.py`:

```python
app.include_router(definicoes.router)
```

Nos pedidos que devolvem modelos do contrato, usa `response_model_exclude_none=True`: os campos opcionais vazios não vão no JSON, como no `contract.ts`.

## Pedidos `/dev`

Só existem com `HOMALY_DEV=1`, porque não pedem login.

```bash
curl -X POST localhost:8000/dev/exemplo
```

```bash
curl -X POST localhost:8000/dev/anomalias -H 'Content-Type: application/json' -d '{"classe": "seguranca", "titulo": "Porta aberta", "explicacao": "Teste"}'
```

- `POST /dev/exemplo` carrega os mesmos dados dos mocks da PWA (pode correr-se várias vezes).
- `POST /dev/anomalias` grava uma `Anomalia` e envia-a pelo WebSocket; com um `id` que já existe, atualiza-a.
- `POST /dev/eventos` grava um `Evento` e envia-o pelo WebSocket.
