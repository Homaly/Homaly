# Divisão do trabalho

Versão de 2026-11-17. Proposta, até a equipa a aceitar. Base: `USER_STORIES.md`, `PLANO.md`, `DECISIONS.md` e a arquitetura C4 em `docs/diagramas/c4-arquitetura.drawio`.

## A ideia

Cada pessoa fica com algumas user stories e faz cada uma de ponta a ponta: a regra, a parte da IA, o que a aplicação mostra e o caso de teste no dataset.

**Ninguém fica à espera de ninguém.** Na primeira manhã fixam-se os formatos que passam entre as partes, e cada pessoa programa contra esses formatos, não contra o código de um colega. Até a peça de outra pessoa existir, usa-se uma versão falsa dela. O código continua ligado, porque é um só produto, mas ninguém fica parado.

## 1. Os formatos, fixados na terça de manhã

Meia hora, os cinco juntos. O que está abaixo é a proposta para essa reunião; depois de fixado, só muda avisando todos.

```python
@dataclass
class Leitura:          # o que a ligação ao MCP produz (e o dataset, no mesmo formato)
    dispositivo: str    # "porta", "temperatura", "lampada", "tomada", "camara"
    tipo: str           # o type da capability: "sensorState", "temperatureValue", ...
    valor: str | float | bool
    em: datetime        # hora da leitura (do polling), não da mudança

@dataclass
class Periodo:          # férias ditas à casa
    inicio: datetime
    fim: datetime
    motivo: str

@dataclass
class Rotina:           # "a empregada vem às terças"
    descricao: str
    dias: list[int]     # 0 = segunda
    hora: time | None

@dataclass
class Silencio:         # resposta a uma anomalia (US02)
    us: str
    ate: datetime | None   # None: até ser removido
    motivo: str

@dataclass
class Contexto:         # o que o responsável disse à casa (US01, US02)
    ferias: list[Periodo]
    rotinas: list[Rotina]
    silencios: list[Silencio]
    casa_vazia: bool
    aparelho_tomada: str | None = None   # "o desumidificador", dito na conversa (US14)

@dataclass
class Desvio:           # o que uma regra produz
    us: str             # "US08"
    classe: Classe      # os mesmos valores de contract.ts
    resumo: str         # os factos, em português simples
    habitual: str | None
    imediato: bool = False   # casa vazia: alerta já, a IA não decide

# Funções que todos podem chamar, com estes nomes:
dispositivos.ler() -> list[Leitura]
dispositivos.executar(dispositivo, tipo, valor) -> bool
regra.verificar(leituras, contexto, agora) -> list[Desvio]   # um ficheiro por história
ia.avaliar(desvio, contexto) -> Anomalia | None              # a Anomalia de contract.ts
avisos.publicar(anomalia, imediato=False)
contacto_externo.agendar(anomalia, imediato=False)  # anomalia nova: começa o tempo de espera;
                                                    # imediato (casa vazia): avisa já, sem esperar
contacto_externo.cancelar(anomalia_id)   # o responsável respondeu: pára o tempo de espera
contacto_externo.resolvida(anomalia)     # resolvida, pelo responsável ou sozinha: pára a espera e,
                                         # se já houve SMS, envia a de resolvido
```

- **Dataset:** ficheiros CSV com as colunas de `Leitura` (`dispositivo,tipo,valor,em`). Cada dono escreve os casos das suas histórias em `dados/usNN.csv`; Vila escreve o histórico de várias semanas em `dados/historico.csv`.
- **Base de dados:** um só ficheiro SQLite. Cada pessoa cria as suas tabelas com `CREATE TABLE IF NOT EXISTS` no seu módulo, por isso ninguém espera por um esquema.
- **Pedidos da API:** cada pessoa escreve os seus num router FastAPI no seu módulo. O contrato entre a PWA e o backend já está fixado em `docs/frontend-design.md` e `frontend/src/types/contract.ts`.
- **A explicação tem sempre recurso:** se `ia.avaliar()` ainda não existir, ou o modelo falhar na demo, a anomalia mostra o `resumo` do desvio.

## 2. Quem fica com o quê

| Pessoa | Faz | User stories | Enquanto a peça de outra pessoa não existe |
|--------|-----|--------------|--------------------------------------------|
| Xuta | `dispositivos`: token, polling, `executar`, stream RTSP | US08, US10, US12, US13 | Para as regras, os seus ficheiros do dataset; para a US13, uma fotografia guardada |
| Vila | O ciclo que corre as regras, o histórico do dataset, `avisos.publicar` | US07, US09, US14 | O dataset em vez de `ler()`; o `resumo` em vez de `avaliar()` |
| Benny | `main.py`, a base de dados, `/anomalias`, `/eventos`, WebSocket, PWA ligada ao backend real | US03, US06, US11 | Um `executar` falso que só regista; o dataset transformado em eventos |
| Simão | `ia.avaliar`, a escolha do modelo | US01, US02 | Desvios escritos à mão; o seu router `/conversa` e as suas tabelas |
| Candeias | `contacto_externo`: tempo de espera, SMS pelo textbee, página do alerta | US04, US05, mais a demo, o pitch e o sumário executivo | Anomalias escritas à mão; o seu router `/definicoes` e as suas tabelas |

Porquê estes grupos:

- **Xuta:** a porta e a temperatura. A US08 e a US12 partilham um só aviso por cada abertura da porta, por isso ficam com a mesma pessoa. A US13 começa por captar a imagem da câmara, que é ler um dispositivo.
- **Vila:** as histórias que dependem do "habitual" que sai do histórico (a que horas a porta costuma abrir, quanto tempo o aparelho na tomada costuma estar ligado) e da casa vazia, que a US07 e a US14 tratam da mesma forma.
- **Benny:** a lâmpada (a US11 propõe apagá-la e a US03 executa a ação) e o histórico, que é sobretudo API e ecrã.
- **Simão:** as duas histórias em que a IA interpreta o que o responsável escreve.
- **Candeias:** tudo o que chega ao contacto externo, incluindo o tempo de espera. Tem menos histórias porque coordena a demo e as entregas.

O tempo de espera passa para Candeias, com a US05. Toda a mudança a uma anomalia (nova, mudada ou resolvida) passa por `avisos.publicar`, por isso Vila acrescenta lá duas linhas: `contacto_externo.agendar` quando a anomalia é nova e `contacto_externo.resolvida` quando passa a resolvida. Benny acrescenta uma: `contacto_externo.cancelar` quando o responsável responde.

## 3. O que cada pessoa faz

### Xuta: US08, US10, US12, US13

- **`dispositivos`:** o token no Keycloak como faz `scripts/mcp_headers.sh` (`grant_type=password`), o User-Agent `homaly-backend/0.1`, o polling com `get_home_devices` (tudo numa só chamada), `executar` com `update_device_capabilities` e a confirmação com `get_device_details`. O alarme do kit é só de fumo, por isso não se lê o estado do alarme.
- **US08:** a regra dos cinco minutos. Quando a porta fecha depois do aviso, a anomalia resolve-se sozinha, com a hora a que a porta fechou na `resolucao`.
- **US10:** abaixo de 16 °C durante duas horas, e a anomalia que se resolve sozinha. Se a proposta das leituras simuladas for aceite, a forma de as injetar na demo.
- **US12:** porta aberta com a temperatura a cair, junta ao aviso da US08.
- **US13:** captar imagens do stream RTSP, pedir a descrição ao modelo de visão e comparar com os veículos conhecidos. É o maior risco do MVP: se não funcionar a tempo, sai, e Xuta ajuda noutras histórias.
- **Fechar:** o intervalo de polling; como a casa reconhece um veículo.

### Vila: US07, US09, US14, o ciclo e o histórico

- **O ciclo:** a cada polling, chama `ler()`, corre todas as regras, passa cada desvio a `avaliar()` e publica. Escreve-se no primeiro dia com versões falsas de tudo; quando as reais chegam, substituem as falsas.
- **Histórico simulado:** várias semanas da casa em `dados/historico.csv`, e o "habitual": a que horas a porta costuma abrir.
- **`avisos.publicar`:** grava a anomalia, envia-a pelo WebSocket e chama `contacto_externo.agendar` (anomalia nova) ou `contacto_externo.resolvida` (anomalia resolvida).
- **US07:** porta aberta a uma hora anormal. Com a casa vazia (férias ditas à casa), o desvio é `imediato` e não é a IA que decide.
- **US09:** a porta não abriu até à hora habitual.
- **US14:** o aparelho na tomada a gastar (potência acima de um limite baixo, por exemplo 10 W) há muito mais tempo do que é costume. A casa pergunta se desliga, e a ação de desligar é a da US03. Com a casa vazia, o desvio é `imediato` e de segurança. Resolve-se sozinha quando o aparelho deixa de gastar. O nome do aparelho vem da conversa (US01); se a casa não o souber, diz "o aparelho na tomada".
- **Propostas a levar à equipa:** histórico pré-carregado e relógio acelerado na demo.

### Benny: US03, US06, US11

- **O backend:** FastAPI e uvicorn no `pyproject.toml`, `backend.main:app` (o que o `docker-compose.yml` já arranca), o ficheiro SQLite, `/anomalias` e `/ws`, e a PWA com `VITE_USE_MOCKS=false`.
- **US03:** aceitar ou recusar a ação na lâmpada ou na tomada, chamando `dispositivos.executar`.
- **US11:** a luz acesa há muito mais tempo do que é costume, com a pergunta e a ação.
- **US06:** `/eventos` e o ecrã do histórico.
- **Fechar:** a proposta do SQLite.
- Segundo `docs/frontend-design.md`, um colega diz já ter endpoints feitos sem push. Se não for Benny, passa-os a Benny.

### Simão: US01, US02

- **Logo na terça:** escolher o modelo e o fornecedor (créditos da organização ou plano gratuito) e acrescentar as variáveis ao `.env.example`.
- **`ia.avaliar`:** decidir se vale a pena avisar, escrever o título e a explicação, e propor uma ação quando houver. Com um desvio `imediato`, só escreve a explicação.
- **US01:** a conversa: férias, rotinas recorrentes e mensagens que a casa não percebe; o pedido `/conversa`; guardar o `Contexto` que as regras leem.
- **US02:** as respostas às anomalias: fechar a ocorrência, silenciar até ao fim do dia ou criar uma rotina. A casa diz o que vai ignorar na `propostaSilencio` da anomalia, e o silêncio só se aplica depois de aceite. Os pedidos `POST /anomalias/{id}/resposta` e `POST /anomalias/{id}/silencio` são de Simão; o resto de `/anomalias` é de Benny.

### Candeias: US04, US05, demo e entregas

- **US04:** o pedido `/definicoes`: o contacto externo e o tempo de espera.
- **US05:** `contacto_externo.agendar`, `cancelar` e `resolvida`; a SMS pelo textbee, só para segurança e para bem-estar e rotina, imediata com a casa vazia; a SMS de resolvido, também quando a anomalia se resolve sozinha. As variáveis do textbee vão para o `.env.example`.
- **Página do alerta:** servida pelo backend em `GET /a/{codigo}`, como HTML simples, fora da PWA e sem login. O código é aleatório e longo, criado quando a SMS é enviada, nunca o id da anomalia. Funciona 24 horas depois do envio, mesmo com a anomalia resolvida; depois só diz que expirou.
- **Demo:** a cena, o guião e os telemóveis. O que envia as SMS tem de estar ligado, com internet e com a app do textbee aberta.
- **Entregas:** coordenar o sumário executivo e a apresentação, com os modelos em `templates/`. Cada pessoa escreve a parte das suas histórias.
- **Fechar:** a US04 ainda fala em "moradores" (lacuna 4 de `docs/diagramas/README.md`); o passo 4 do `PLANO.md` sem as exceções do contacto externo (lacuna 5).
- **Propõe, e a equipa decide:** a cena da demo, o papel das ideias 1 e 3 no pitch, e se se pode reaproveitar código de antes do evento.

## 4. Calendário

As datas são as da secção "Decidido" do `DECISIONS.md`: checkpoint e sumário executivo na quarta, apresentação final na sexta. O calendário do `PLANO.md` ainda conta com quatro dias e apresentação na quinta; está desatualizado nesse ponto.

Em vez de esperar uns pelos outros, junta-se o trabalho a horas marcadas. Em cada junção, o ciclo corre com o que já é real e com versões falsas do resto.

- **Terça 17, de manhã:** fixar os formatos (meia hora).
- **Terça 17, 18:00:** primeira junção.
- **Quarta 18, 12:00:** segunda junção, antes do checkpoint.
- **Quarta 18:** checkpoint com os mentores das 14:00 às 18:30; entrega do sumário executivo até às 19:00 (coordena Candeias).
- **Sexta 20:** ensaio de manhã; avaliação intermédia às 16:00; entrega da apresentação até às 17:30; apresentações às 18:00.

| Dia | Xuta | Vila | Benny | Simão | Candeias |
|-----|------|------|-------|-------|----------|
| **Terça 17** | `dispositivos.ler()`; regra da US08 | O ciclo com versões falsas; histórico simulado | Backend, base de dados, `/anomalias`, `/ws`; PWA ligada | Escolher o modelo; `ia.avaliar()` | Tempo de espera e SMS pelo textbee; US04 |
| **Quarta 18 (até ao checkpoint)** | `dispositivos.executar`; US10 e US12 | US07 e US14 | US03 | US02 | US05 e a página do alerta |
| **Quinta 19** | US13 | US09; afinar a deteção com o histórico | US11 e US06 | US01 | Escolher e ensaiar a cena da demo |

## 5. Onde ainda se mexe no mesmo

- **`main.py`:** cada pessoa acrescenta uma linha para incluir o seu router.
- **`frontend/src/pages/Anomalia.tsx`:** Simão (a resposta, US02) e Benny (a ação, US03) mexem nos dois. Combinam quem mexe em que parte.
- **Os formatos da secção 1:** mudá-los depois obriga a avisar todos. É o preço de ninguém esperar.
- **Ficheiros partilhados** (`contract.ts`, `docker-compose.yml`, `.env.example`): mudam-se avisando a equipa.
- `git pull --rebase` antes de cada push, e commits pequenos.
- O `docs/diagramas/c4-arquitetura.drawio` é uma só linha de texto, por isso o git não junta alterações de duas pessoas. Edita-o uma pessoa de cada vez.
- Os commits feitos com agentes de IA levam a linha `Co-Authored-By` (ver `AGENTS.md`). O `.env` nunca vai para o repositório.
