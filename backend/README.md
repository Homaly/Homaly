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
| `RECARREGAR` | Com `0`, o backend arranca sem `--reload` (no Docker e no `uv run backend`). Na demo, gravar um ficheiro não o reinicia | `1` |
| `MCP_URL`, `MCP_CLIENT_ID`, `MCP_CLIENT_TYPE`, `MCP_API_KEY`, `KEYCLOAK_USER`, `KEYCLOAK_PASSWORD` | A ligação ao MCP (`dispositivos`) | Obrigatórias para ler a casa real |
| `CICLO` | Com `1`, a app corre o ciclo das regras numa thread, com as peças reais (`ciclo.arrancar`) | Desligado |
| `RELOGIO_INICIO`, `RELOGIO_FATOR` | O relógio do ciclo e da API (um só por processo): começa a esta hora simulada (ISO 8601) e anda este número de vezes mais depressa, para a demo | A hora real |
| `POLLING_SEGUNDOS` | De quanto em quanto tempo ler a casa (`dispositivos.intervalo_s()`) | `10` |
| `SENSOR_SILENCIO_MINUTOS` | Um dispositivo que não comunica há mais do que isto não dá leituras (o MCP repetiria o último valor); `0` desliga | `60` |
| `PORTA_MINUTOS`, `PORTA_QUEDA_GRAUS`, `PORTA_DIFERENCA_GRAUS` | Os limites da regra da porta e das janelas (US08, US12): minutos aberta; descida da divisão; quanto a divisão tem de descer mais do que as outras (só quando há sensores noutras divisões) | `5` minutos, `2` °C, `1` °C |
| `SAIDA_MINUTOS` | A saída de casa (`saida.py`, US09, US11, US14, US15): a porta da rua abre e, durante estes minutos, nenhuma câmara interior vê movimento | `5` |
| `DISPOSITIVOS_CSV` | O inventário: o nome e a divisão de cada dispositivo (`id,nome,divisao`; `inventario.py`) | `dados/dispositivos.csv` |
| `AGUA_LIMITE_LMIN`, `AGUA_MINUTOS`, `FUGA_LMIN`, `CANO_LMIN`, `CANO_MINUTOS`, `AGUA_SINAIS_MINUTOS` | Os limites da água (US15): o que conta como a correr; a hora a correr; o fio de água; o cano rebentado; e a água a correr sem nenhum sinal de vida (bem-estar) | `0.1` L/min, `60` min, `2` L/min, `12` L/min, `5` min, `30` min |
| `US09_HORAS`, `US09_LACUNA_MINUTOS` | Os limites da regra dos sinais de vida (US09): horas de silêncio nas horas ativas; buraco nas leituras que recomeça a vigilância (conta no relógio acelerado: `RELOGIO_FATOR` × (polling + uma volta) tem de ficar abaixo, ou sobe-se o valor na demo). Demo: para a manhã, arrancar o relógio antes das 07:15 num dia útil (ex.: 06:30); para "a atividade parou", baixar `US09_HORAS`; resolve-se com `POST /dev/leituras` `{"dispositivo":"camara","tipo":"motionDetected","valor":"<um valor novo de cada vez>"}`. `dispositivos.COMANDO_SEGUNDOS` (60 s reais) pressupõe `POLLING_SEGUNDOS` bem abaixo disso | `3` horas, `30` minutos |
| `FRIO_LIMITE_GRAUS`, `FRIO_MINUTOS` | Os limites da casa fria (US10) | `16` °C, `120` minutos |
| `TEXTBEE_API_KEY`, `TEXTBEE_DEVICE_ID` | O textbee, que envia as SMS ao contacto externo (US05). Sem a chave, as SMS não saem: ficam no registo e em `GET /dev/sms` | Sem textbee |
| `SMS_MAXIMO_HORA` | No máximo estas SMS por hora. Só contam as que o textbee aceitou (as recusadas, as sem ligação e as sem chave não gastam tarifário). No limite, a SMS volta a tentar de minuto a minuto, sem gastar as 3 tentativas, até a hora libertar um lugar. A app não tem login, e isto impede que alguém gaste o tarifário do telemóvel do textbee | `10` (`0` tira o limite) |
| `HOMALY_URL_PUBLICO` | O início do link da SMS, para a página do alerta; o telemóvel do contacto tem de o alcançar | `http://localhost:8000` |
| `IA_FORNECEDOR` | Que modelo de IA a casa usa: `groq` (recomendado), `gemini`, `openrouter` (pago) ou `falso`, que não usa nenhum (a casa fica com o resumo do desvio). Groq e Gemini têm plano grátis; cada pessoa cria a sua chave (links no `.env.example`). Se o modelo falhar ou demorar mais de 10 s, a casa usa o resumo do desvio | `falso` |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | A chave do fornecedor escolhido | — |
| `IA_MODELO` | Troca o modelo do fornecedor. O plano grátis do Groq dá 8 000 tokens por minuto (umas 6 a 10 avaliações) | `openai/gpt-oss-120b` (groq), `gemini-3.5-flash-lite` (gemini), `anthropic/claude-haiku-5.5` (openrouter) |
| `LUZ_HORAS` | US11: ao fim de quantas horas acesa a casa pergunta pela luz (na demo, por exemplo `0.05` = 3 min) | `5` |
| `PRESENCA_MINUTOS`, `SAIU_MINUTOS`, `AUSENCIA_MINUTOS` | US14: movimento na divisão da tomada há menos disto quer dizer que alguém usa o aparelho; saíram de casa (`saida.py`) há isto; ninguém na divisão da tomada há isto. Afinados com o histórico (até 47 min sem movimento com o aparelho em uso); na demo, por exemplo `2` e `3` | `10`, `20`, `60` minutos |

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
| `ia/` | `dispositivos.py`: a IA lê os dispositivos do MCP que não estão no CSV do inventário e diz o nome, a divisão e o papel de cada um; valida a resposta e guarda-a na tabela `dispositivos_ia`, com a assinatura do que o MCP dizia (só volta a perguntar se o MCP mudar; se a IA falhar, só no próximo arranque). `modelo.py`: o `Modelo` (trocável), o `ModeloFalso`, o `ModeloOpenAI` (Groq e Gemini, pela API no formato da OpenAI, em modo JSON) e `obter_modelo`, que lê `IA_FORNECEDOR`. `avaliar.py`: `avaliar(desvio, contexto)` dá uma `Anomalia` (ou nada), com o resumo do desvio se o modelo falhar. A IA não pode calar a US08 (`AVISA_SEMPRE`: a porta esquecida aberta avisa sempre) nem um aviso de segurança sem uma rotina de hoje que lhe dê razão (a hora da rotina a menos de duas horas; sem hora, nunca de madrugada); `us_da_anomalia`; `registar_us(a.id, us)`: quem publicar uma anomalia sem passar por `avaliar` tem de a chamar, senão a US02 não consegue propor silenciá-la. |
| `contexto/` | `repositorio.py`: o que a pessoa disse à casa (férias, rotinas, silêncios, conversa), guardado em SQLite. |
| `conversa/` | `GET /conversa` e `POST /conversa`: a pessoa fala com a casa (US01). Diz-lhe férias, rotinas e o aparelho na tomada, ou pergunta ("está tudo bem?", "o que aconteceu hoje?"); `estado.py` junta o que a casa sabe (a última leitura, `dispositivos.ultimas()`, os avisos ativos, os eventos de hoje e o contexto) e a IA responde só com isso. A casa não cumpre ordens pela conversa. |
| `resposta/` | `POST /anomalias/{id}/resposta` e `POST /anomalias/{id}/silencio`: a pessoa responde a uma anomalia e aceita ou recusa deixar de ser avisada (US02). |
| `acoes.py` | `POST /anomalias/{id}/acao` (US03): aceitar executa a ação e resolve a anomalia; recusar resolve-a sem agir e, na US11 e na US14, não volta a perguntar até ao fim do dia. O comando é fixo por user story (`ACOES`: US11 apaga a lâmpada, US14 desliga a tomada), nunca vem do texto da IA. Quando a regra diz de que dispositivo fala (`Desvio.dispositivo`, guardado em `anomalia_dispositivo`), a ação muda esse id; senão, o dispositivo desse tipo. Usa `dispositivos.executar`; sem ele, um falso que só regista (só com `HOMALY_DEV=1`). |
| `dependencias.py` | O que os routers recebem por `Depends` (o modelo, a hora); os testes substituem-no. |
| `regras/` | Uma regra por história, cada uma com `verificar(leituras, contexto, agora) -> list[Desvio | Resolucao]` (a `Resolucao` diz como o problema acabou). `us11.py`: a luz acesa há `LUZ_HORAS` e a pessoa saiu depois de ela acender (`saida.py`; sem câmaras, basta a porta abrir e fechar); o movimento na câmara da divisão da luz desfaz a saída. Cada lâmpada tem o seu estado, na tabela `estado_lampadas` (uma linha por lâmpada acesa); há um aviso de cada vez, da lâmpada que passou primeiro a merecê-lo, com o id dela em `Desvio.dispositivo`. Os casos de teste estão em `dados/us11.csv`. |
| `ciclo.py` | O ciclo das regras: a cada volta, `dispositivos.ler()`, todas as regras, `ia.avaliar` para cada desvio novo e `avisos.publicar`. Com `CICLO=1`, corre numa thread da app; antes de mexer numa anomalia, lê-a da base de dados, para não reescrever uma que o responsável já resolveu. No arranque, reconstrói as ocorrências a partir das anomalias ativas (`Ciclo.restaurar`), para um reinício não criar outra anomalia (e outra SMS) por cima da antiga; uma reconstruída só se fecha com a `Resolucao` da regra ou com a resposta. A US07 não se reconstrói: só dispara num momento e não duplica; a US09 guarda o estado na base de dados (`estado_us09`) e só se reconstrói se a regra tiver um desvio pendente (`us09.tem_pendente`); sem ele, a anomalia antiga fica ativa e o próximo desvio avisa de novo. `python -m backend.ciclo dados/usNN.csv` (ou `--ao-vivo`) corre-o no terminal, só com as peças falsas de `falsos/` e com uma base de dados temporária (não mexe no `homaly.db`). |
| `avisos.py` | `avisos.publicar`: `anomalias.guardar`, `tempo_real.enviar_anomalia` e o contacto externo (`agendar`, com `imediato` quando a casa está vazia, e `resolvida`). Uma anomalia que chega já resolvida sem ter sido vista não agenda nada. |
| `definicoes.py` | US04: `GET` e `PUT /definicoes` (contacto externo, tempo de espera e nome da casa); `definicoes.obter()`. O telemóvel fica no formato internacional (`+351912345678`). |
| `contacto_externo/` | US05: `ContactoExterno` (o que o `avisos` usa) agenda a SMS para o fim do tempo de espera; `arrancar()` (com `CICLO=1`) envia de 5 em 5 s o que está na hora, pelo textbee (`sms.py`). Na hora de enviar volta a ver a anomalia: com resposta, resolvida, de outra classe ou sem contacto, não envia. Quem recebeu o alerta recebe a SMS de resolvido. O textbee que falha tenta outra vez 30 s e 60 s depois. A thread arranca com o ciclo (`CICLO=1`) ou com `HOMALY_DEV=1`, para os alertas de `/dev/anomalias?contacto=true` também saírem. Mesmo com o relógio acelerado (`RELOGIO_FATOR`), o tempo de espera, as novas tentativas e as 24 horas da página contam em tempo real: são o tempo de pessoas e do textbee, que não andam mais depressa. O texto das SMS fica com as horas (simuladas) da anomalia. `pagina.py`: `GET /a/{codigo}`, a página do alerta, sem login, válida 24 horas depois da última SMS. |
| `habitual.py`, `relogio.py`, `afinacao.py` | O habitual da casa, do histórico simulado em `dados/historico.csv` (US07, US09, US14: a hora do primeiro sinal de vida do dia e as horas com atividade); o relógio, talvez acelerado; e a passagem do histórico pelas regras para contar falsos alarmes (`scripts/afinar.py`). |
| `dev.py` | `/dev`: pôr anomalias e eventos à mão, para testar a PWA sem esperar pelo ciclo das regras (`POST /dev/exemplo` carrega os dados dos mocks). |
| `dispositivos/` | A casa pelo MCP: `ler()` (um só `get_home_devices`, devolve `Leitura`s e grava um evento quando a porta, a lâmpada ou a tomada mudam), `ultimas()` (a última leitura, sem ir ao MCP), `executar(dispositivo, tipo, valor, id="")` (a do `id` do MCP, ou a desse tipo; lâmpada e tomada: `power` on/off; lâmpada: `brightness` 1–100; confirma lendo de novo), `alarme()`, `intervalo_s()` e `em_silencio()` (os dispositivos calados, cujas leituras ficam de fora). Falhas levantam `ErroDispositivos`. |
| `dispositivos/simulacao.py` | `/dev/leituras`: leituras injetadas para a demo, por cima das reais. |
| `regras/porta.py` | US08 e US12: cada abertura (a porta da rua e cada janela) tem o seu estado, na tabela `estado_aberturas`, e no máximo um aviso. A US12 compara a descida da divisão da abertura com a das outras divisões; uma janela nunca passa a segurança (US08). Devolve `Resolucao` quando a abertura fecha. Há um só aviso de cada US de cada vez: uma segunda abertura espera que a primeira feche. |
| `regras/us15.py` | US15: a água a correr sem parar (o contador `agua`/`caudal` só existe injetado). Com o resto da casa: saíram com a água a correr (eficiência, logo); `AGUA_SINAIS_MINUTOS` a correr sem nenhum sinal de vida (bem-estar, pode ter acontecido alguma coisa no banho). |
| `inventario.py` | O nome e a divisão de cada dispositivo, por esta ordem (o papel também, campo a campo): `dados/dispositivos.csv` (`id,nome,divisao`: o kit, com os nomes da equipa, e os dispositivos simulados); o `name` e o `roomName` que o MCP dá, registados por `dispositivos.ler()` em memória (`registar()`; um dispositivo novo vai uma vez para o log), para uma casa nova funcionar sem escrever nada. Antes das regras deste módulo, a IA (`ia/dispositivos.py`) diz o nome em português, a divisão e o papel dos dispositivos do MCP que não estão no CSV (`classificar()`, chamado por `ler()` quando há dispositivos novos ou mudados); o que não identifica, ou sem IA, fica com as regras; os valores do tipo. Do MCP só se usa o que diz alguma coisa: um nome de fábrica ("Contact sensor", "Light 2") ou uma divisão desconhecida ("Hack 4") contam como não preenchidos, e o kit fica como no MVP. Uma divisão conhecida ganha o artigo ("Sala" -> "a sala"); sem nome, o nome faz-se do tipo, do papel e da divisão ("Câmara do quarto", "Janela do quarto"). O papel (`porta_da_rua`, `janela`, `interior`, `exterior`) não tem coluna: `papel()` deduz-o do tipo, do nome e da divisão ("Porta da rua", "Porta de entrada" ou um sensor de contacto no hall é a porta da rua; "Porta da varanda" e as janelas são outras aberturas; uma câmara com "jardim", "garagem", "entrada de veículos"... no nome ou na divisão é exterior). Um sensor com um nome genérico ("Contact sensor") é a porta da rua se nenhum sensor da casa do MCP o for claramente. `python -m backend.dispositivos` mostra o que a casa deduziu de cada dispositivo e de onde veio. Cada `Leitura` traz o `id` do dispositivo; um que não está no inventário (ou sem `id`, como nos CSV) fica com os valores do seu tipo: na sala, a porta da rua, uma câmara interior. |
| `saida.py` | A saída de casa: a porta da rua abre e, nos `SAIDA_MINUTOS` seguintes, nenhuma câmara interior vê movimento. Sem nenhuma câmara interior a dar leituras, não conclui nada. Cada regra que precisa dela (US09, US11, US14, US15) tem o seu `Vigia`. |
| `regras/temperatura.py` | US10: abaixo de 16 °C durante duas horas; devolve `Resolucao` quando volta a subir. |
| `regras/us07.py`, `us09.py`, `us14.py` | US07: a porta abre a uma hora anormal ou com a casa vazia (só se resolve com resposta). US09: a casa não vê sinais de vida (movimento ou som numa câmara interior, lâmpada, tomada a gastar, porta da rua; `sinais.py`, cada dispositivo comparado com a sua leitura anterior): ainda nenhum à hora habitual do primeiro sinal mais 1 h 30, ou `US09_HORAS` sem nenhum nas horas ativas, com a pessoa em casa (não conta depois de uma saída, `saida.py`); devolve `Resolucao` no próximo sinal, ou quando a casa fica vazia. O estado fica na tabela `estado_us09`. US14: o aparelho na tomada a gastar sem ninguém a usá-lo. Junta a saída de casa (`saida.py`) e o movimento das câmaras de dentro (`regras/presenca.py`, o último movimento por divisão, com a divisão de cada câmara e da tomada no inventário): com alguém na divisão da tomada não avisa; um aparelho que precisa de alguém por perto (todos menos os de `SOZINHOS`, como a máquina de lavar) avisa quando saíram há `SAIU_MINUTOS` (a porta a abrir outra vez suspende a saída) ou quando não há ninguém na divisão há `AUSENCIA_MINUTOS`; sem câmaras de dentro, ou com um aparelho que pode ficar sozinho, avisa como antes, a 3× o habitual. Devolve `Resolucao` quando deixa de gastar ou quando volta a haver alguém na divisão. Cada tomada tem o seu estado (em memória) e há um aviso de cada vez, com o id da tomada em `Desvio.dispositivo`; com várias tomadas, o aparelho é o nome da tomada no inventário, não o da conversa. Um silêncio temporário nunca cala um desvio de segurança. |

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
- `POST /dev/anomalias` grava uma `Anomalia` e envia-a pelo WebSocket; com um `id` que já existe, atualiza-a. Com `?us=US11`, regista a user story (a US02 e a US03 precisam dela). Por omissão não avisa o contacto externo; com `?contacto=true` passa pelo `avisos.publicar`, como o ciclo, e uma de segurança ou de bem-estar agenda a SMS (US05). Assim mostra-se a US05 sem `CICLO=1` nem `/dev/leituras`.
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

Com `id`, a leitura muda só esse dispositivo, ou acrescenta-o se o kit não o tem. O inventário (`dados/dispositivos.csv`) já tem, para a demo das várias divisões, a janela e o sensor de temperatura do quarto (`janela-quarto`, `temperatura-quarto`), as câmaras do quarto e da cozinha (`camara-quarto`, `camara-cozinha`) e a da entrada de veículos, exterior (`camara-entrada`):

```bash
curl -X POST localhost:8000/dev/leituras -H 'Content-Type: application/json' -d '{"dispositivo": "porta", "tipo": "sensorState", "valor": "alarm", "id": "janela-quarto"}'
curl -X POST localhost:8000/dev/leituras -H 'Content-Type: application/json' -d '{"dispositivo": "temperatura", "tipo": "temperatureValue", "valor": 17.5, "id": "temperatura-quarto"}'
curl -X DELETE 'localhost:8000/dev/leituras/porta/sensorState?id=janela-quarto'
```

Uma janela injetada começa já aberta: a casa só conta a abertura a partir da volta em que a vê. Para a US12 da janela, injeta-se primeiro o quarto à temperatura inicial, depois a janela aberta e, por fim, a temperatura a descer.

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

Para provocar um alerta ao contacto à mão (com `HOMALY_DEV=1`; o contacto e o tempo de espera vêm das Definições):

```bash
curl -X POST 'localhost:8000/dev/anomalias?contacto=true&us=US08' -H 'Content-Type: application/json' -d '{"classe": "seguranca", "titulo": "Porta aberta", "explicacao": "A porta da rua está aberta há mais de 5 minutos."}'
```

As anomalias que nascem do ciclo (com `CICLO=1`, por exemplo a partir de `/dev/leituras`) avisam o contacto sozinhas.
