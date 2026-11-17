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
| `MCP_URL`, `MCP_CLIENT_ID`, `MCP_CLIENT_TYPE`, `MCP_API_KEY`, `KEYCLOAK_USER`, `KEYCLOAK_PASSWORD` | A ligação ao MCP (`dispositivos`) | Obrigatórias para ler a casa real |
| `CICLO` | Com `1`, a app corre o ciclo das regras numa thread, com as peças reais (`ciclo.arrancar`) | Desligado |
| `RELOGIO_INICIO`, `RELOGIO_FATOR` | O relógio do ciclo e da API (um só por processo): começa a esta hora simulada (ISO 8601) e anda este número de vezes mais depressa, para a demo | A hora real |
| `POLLING_SEGUNDOS` | De quanto em quanto tempo ler a casa (`dispositivos.intervalo_s()`) | `10` |
| `PORTA_MINUTOS`, `PORTA_QUEDA_GRAUS` | Os limites da regra da porta (US08, US12) | `5` minutos, `2` °C |
| `FRIO_LIMITE_GRAUS`, `FRIO_MINUTOS` | Os limites da casa fria (US10) | `16` °C, `120` minutos |
| `TEXTBEE_API_KEY`, `TEXTBEE_DEVICE_ID` | O textbee, que envia as SMS ao contacto externo (US05). Sem a chave, as SMS não saem: ficam no registo e em `GET /dev/sms` | Sem textbee |
| `SMS_MAXIMO_HORA` | No máximo estas SMS por hora; acima disso, a SMS espera pela tentativa seguinte. A app não tem login, e isto impede que alguém gaste o tarifário do telemóvel do textbee | `10` (`0` tira o limite) |
| `HOMALY_URL_PUBLICO` | O início do link da SMS, para a página do alerta; o telemóvel do contacto tem de o alcançar | `http://localhost:8000` |
| `IA_FORNECEDOR` | Que modelo de IA a casa usa. Só existe `falso`, que não usa nenhum: a casa fica com o resumo do desvio | `falso` |
| `LUZ_HORAS` | US11: ao fim de quantas horas acesa a casa pergunta pela luz (na demo, por exemplo `0.05` = 3 min) | `5` |

## Módulos

| Ficheiro | O quê |
|----------|-------|
| `main.py` | A app (`backend.main:app`). Cada pessoa acrescenta aqui uma linha com o seu router. |
| `contrato.py` | O contrato com a PWA (`Anomalia`, `Evento`, ...), igual ao `contract.ts`. Em Python os campos são snake_case; no JSON saem em camelCase. |
| `db.py` | A ligação ao SQLite. |
| `anomalias.py` | A tabela das anomalias, `guardar`, `obter`, `listar`; `GET /anomalias` e `GET /anomalias/{id}`. |
| `eventos.py` | A tabela dos eventos, `registar`, `listar`; `GET /eventos`. |
| `historico.py` | O resto do histórico (US06), como eventos: a anomalia nova e a anomalia resolvida, com `anomaliaId` (o `anomalias.guardar` chama `anomalia_mudou` sozinho), e `registar_desvio(desvio, motivo, agora)`, o desvio que a casa viu e não avisou: é o `registar_historico` do ciclo. |
| `tempo_real.py` | O WebSocket `/ws`; `enviar_anomalia` e `enviar_evento`. |
| `formatos.py` | Os formatos partilhados entre as peças (`Leitura`, `Desvio`, `Contexto`, ...); mudar um campo obriga a avisar a equipa. |
| `ia/` | `modelo.py`: o `Modelo` (trocável), o `ModeloFalso` e `obter_modelo`, que lê `IA_FORNECEDOR`. `avaliar.py`: `avaliar(desvio, contexto)` dá uma `Anomalia` (ou nada), com o resumo do desvio se o modelo falhar; `us_da_anomalia`; `registar_us(a.id, us)`: quem publicar uma anomalia sem passar por `avaliar` tem de a chamar, senão a US02 não consegue propor silenciá-la. |
| `contexto/` | `repositorio.py`: o que a pessoa disse à casa (férias, rotinas, silêncios, conversa), guardado em SQLite. |
| `conversa/` | `GET /conversa` e `POST /conversa`: a pessoa fala com a casa (US01). |
| `resposta/` | `POST /anomalias/{id}/resposta` e `POST /anomalias/{id}/silencio`: a pessoa responde a uma anomalia e aceita ou recusa deixar de ser avisada (US02). |
| `acoes.py` | `POST /anomalias/{id}/acao` (US03): aceitar executa a ação e resolve a anomalia; recusar resolve-a sem agir e, na US11 e na US14, não volta a perguntar até ao fim do dia. O comando é fixo por user story (`ACOES`: US11 apaga a lâmpada, US14 desliga a tomada), nunca vem do texto da IA. Usa `dispositivos.executar`; sem ele, um falso que só regista (só com `HOMALY_DEV=1`). |
| `dependencias.py` | O que os routers recebem por `Depends` (o modelo, a hora); os testes substituem-no. |
| `regras/` | Uma regra por história, cada uma com `verificar(leituras, contexto, agora) -> list[Desvio | Resolucao]` (a `Resolucao` diz como o problema acabou). `us11.py`: a luz acesa há `LUZ_HORAS` e a porta abriu e fechou depois de ela acender; o que lembra entre voltas fica na tabela `estado_luz`. Os casos de teste estão em `dados/us11.csv`. |
| `ciclo.py` | O ciclo das regras: a cada volta, `dispositivos.ler()`, todas as regras, `ia.avaliar` para cada desvio novo e `avisos.publicar`. Com `CICLO=1`, corre numa thread da app; antes de mexer numa anomalia, lê-a da base de dados, para não reescrever uma que o responsável já resolveu. `python -m backend.ciclo dados/usNN.csv` (ou `--ao-vivo`) corre-o no terminal, só com as peças falsas de `falsos/` e com uma base de dados temporária (não mexe no `homaly.db`). |
| `avisos.py` | `avisos.publicar`: `anomalias.guardar`, `tempo_real.enviar_anomalia` e o contacto externo (`agendar`, com `imediato` quando a casa está vazia, e `resolvida`). Uma anomalia que chega já resolvida sem ter sido vista não agenda nada. |
| `definicoes.py` | US04: `GET` e `PUT /definicoes` (contacto externo, tempo de espera e nome da casa); `definicoes.obter()`. O telemóvel fica no formato internacional (`+351912345678`). |
| `contacto_externo/` | US05: `ContactoExterno` (o que o `avisos` usa) agenda a SMS para o fim do tempo de espera; `arrancar()` (com `CICLO=1`) envia de 5 em 5 s o que está na hora, pelo textbee (`sms.py`). Na hora de enviar volta a ver a anomalia: com resposta, resolvida, de outra classe ou sem contacto, não envia. Quem recebeu o alerta recebe a SMS de resolvido. O textbee que falha tenta outra vez 30 s e 60 s depois. A thread só arranca com o ciclo, porque sem ele não nascem alertas. Com o relógio acelerado (`RELOGIO_FATOR`), o tempo de espera e as 24 horas da página também correm mais depressa. `pagina.py`: `GET /a/{codigo}`, a página do alerta, sem login, válida 24 horas depois da última SMS. |
| `habitual.py`, `relogio.py`, `afinacao.py` | O habitual da casa, do histórico simulado em `dados/historico.csv` (US07, US09, US14); o relógio, talvez acelerado; e a passagem do histórico pelas regras para contar falsos alarmes (`scripts/afinar.py`). |
| `dev.py` | `/dev`: pôr anomalias e eventos à mão, para testar a PWA sem esperar pelo ciclo das regras (`POST /dev/exemplo` carrega os dados dos mocks). |
| `dispositivos/` | A casa pelo MCP: `ler()` (um só `get_home_devices`, devolve `Leitura`s e grava um evento quando a porta, a lâmpada ou a tomada mudam), `executar(dispositivo, tipo, valor)` (lâmpada e tomada: `power` on/off; lâmpada: `brightness` 1–100; confirma lendo de novo), `alarme()` e `intervalo_s()`. Falhas levantam `ErroDispositivos`. |
| `dispositivos/simulacao.py` | `/dev/leituras`: leituras injetadas para a demo, por cima das reais. |
| `regras/porta.py` | US08 e US12 num só aviso por abertura da porta; devolve `Resolucao` quando a porta fecha. |
| `regras/temperatura.py` | US10: abaixo de 16 °C durante duas horas; devolve `Resolucao` quando volta a subir. |
| `regras/us07.py`, `us09.py`, `us14.py` | US07: a porta abre a uma hora anormal ou com a casa vazia (só se resolve com resposta). US09: a porta não abriu até à hora habitual; devolve `Resolucao` quando abre, ou quando a casa fica vazia. US14: a tomada a gastar há muito mais do que é costume; devolve `Resolucao` quando deixa de gastar. Um silêncio temporário nunca cala um desvio de segurança. |

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
- `POST /dev/anomalias` grava uma `Anomalia` e envia-a pelo WebSocket; com um `id` que já existe, atualiza-a. Com `?us=US11`, regista a user story (a US02 e a US03 precisam dela).
- `POST /dev/eventos` grava um `Evento` e envia-o pelo WebSocket.

## Testes

A partir de `backend/`:

```bash
uv run pytest
```

Os testes ficam em `tests/` e importam os auxiliares com `from tests.conftest import ...` (por exemplo `ModeloFixo`, um modelo que devolve sempre a resposta combinada, e `AGORA`). A fixture `bd` (automática) dá a cada teste um ficheiro SQLite novo, com as tabelas criadas.

### Ler a casa real

A partir de `backend/`, só lê, não muda nada:

```bash
set -a; . ../.env; set +a; uv run python -m backend.dispositivos
```

### Leituras injetadas (demo)

Sobrepõem uma leitura real até serem removidas; o resto da casa continua real.

```bash
curl -X POST localhost:8000/dev/leituras -H 'Content-Type: application/json' -d '{"dispositivo": "temperatura", "tipo": "temperatureValue", "valor": 15}'
curl localhost:8000/dev/leituras                                     # as que estão injetadas
curl -X DELETE localhost:8000/dev/leituras/temperatura/temperatureValue
curl -X DELETE localhost:8000/dev/leituras                           # todas
```

Para a US10 na demo, junta-se `FRIO_MINUTOS=2` no `.env`.

### SMS ao contacto externo (textbee)

O textbee envia as SMS a partir de um telemóvel Android com cartão SIM (gasta o tarifário desse telemóvel). Para o ligar:

1. Criar uma conta em [textbee.dev](https://textbee.dev).
2. No telemóvel Android, instalar a app a partir de [textbee.dev/download](https://textbee.dev/download) (não está na Play Store) e dar-lhe as permissões de SMS.
3. No painel do textbee, **Add device** e ler o código QR com a app: isso regista o telemóvel e cria a chave da API.
4. Pôr a chave em `TEXTBEE_API_KEY` no `.env` (e `TEXTBEE_DEVICE_ID`, se houver mais de um telemóvel).
5. Confirmar com uma SMS de teste:

```bash
set -a; . ../.env; set +a; uv run python -m backend.contacto_externo.teste_sms 912345678
```

O telemóvel tem de estar ligado, com internet e com a app aberta. No telemóvel que recebe, grava-se o número dele como "Homaly".

O link da SMS começa por `HOMALY_URL_PUBLICO`. Na demo, com o contacto na mesma rede Wi-Fi, é o IP do portátil (ex.: `http://192.168.1.20:8000`). Fora da rede, só com um túnel público, e aí muda-se só esta variável.

Sem `TEXTBEE_API_KEY`, as SMS ficam em `GET /dev/sms` (com `HOMALY_DEV=1`), para se ver o texto e abrir o link.
