# Diagramas

Versão de 2026-11-17. Base: `DECISIONS.md` (só a secção "Decidido"), `USER_STORIES.md` (US01–US13), `PLANO.md`, `docs/frontend-design.md` e `docs/mcp-dispositivos.md`.

Esta pasta tem dois tipos de diagrama:

- **Diagramas de sequência**, na sintaxe do [sequencediagram.org](https://sequencediagram.org). Para ver um, abrir o site, apagar o exemplo do editor e colar o conteúdo do ficheiro. Todos foram verificados no próprio site, sem erros de sintaxe.
- **Arquitetura C4**, em `c4-arquitetura.drawio`, feita a partir dos diagramas de sequência. Ver a secção "Arquitetura C4" mais abaixo.

## Ficheiros

| Ficheiro | O que mostra |
|----------|--------------|
| `c4-arquitetura.drawio` | A arquitetura C4 em três páginas: contexto, contentores e componentes do backend |
| `00-visao-geral.txt` | O ciclo completo: ligação ao MCP, conversa, leitura dos sensores, regras, IA, notificação, resposta, ação e SMS |
| `us01-contar-a-casa.txt` | US01: conversa por texto com a casa (férias, rotinas recorrentes, mensagem não percebida) |
| `us02-receber-e-responder.txt` | US02: notificação, resposta, proposta de silêncio e confirmação |
| `us03-autorizar-acao.txt` | US03: aceitar, recusar ou ignorar a ação proposta (apagar a lâmpada) |
| `us04-escolher-contacto-externo.txt` | US04: indicar, mudar ou remover o contacto externo e o tempo de espera |
| `us05-aviso-contacto-externo.txt` | US05: tempo de espera, SMS pelo textbee, página do alerta e SMS de resolvido |
| `us06-historico.txt` | US06: histórico de eventos e detalhe de uma anomalia |
| `us07-porta-hora-anormal.txt` | US07: porta aberta a uma hora anormal ou com a casa vazia |
| `us08-porta-esquecida-aberta.txt` | US08: porta aberta mais de cinco minutos, e a junção com a US12 |
| `us09-porta-nao-abriu.txt` | US09: a porta não abriu até à hora habitual |
| `us10-casa-fria.txt` | US10: abaixo de 16 °C durante duas horas, e a resolução sozinha |
| `us11-luz-acesa.txt` | US11: luz acesa há demasiado tempo, com a pergunta e a ação |
| `us12-porta-aberta-a-arrefecer.txt` | US12: porta aberta com a sala a arrefecer, e a junção com a US08 |
| `us13-veiculo-desconhecido.txt` | US13: veículo desconhecido na entrada (câmara, stream RTSP e modelo de visão) |

## Participantes

| Participante | O que é |
|--------------|---------|
| Responsável da casa | A única pessoa com a aplicação |
| PWA Homaly | O frontend (React), no telemóvel |
| API REST + WebSocket | Os pedidos do contrato em `docs/frontend-design.md` e o WebSocket `/ws` |
| Dispositivos (cliente MCP) | Lê os sensores por polling, compara com a leitura anterior e executa as ações |
| Motor de anomalias | As regras simples que detetam o desvio |
| Agente de IA | Avalia o contexto, decide se avisa, escreve a explicação e interpreta as mensagens |
| Avisos (espera e SMS) | Publica as anomalias na aplicação, gere o tempo de espera e pede as SMS |
| Base de dados | Histórico, eventos, anomalias, conversa, rotinas, silêncios e definições |
| Modelo de IA | O fornecedor ainda está por decidir; na US13 também faz de modelo de visão |
| Servidor MCP Altice | O servidor obrigatório do desafio |
| textbee | A API e a app Android que envia as SMS a partir do telemóvel de um colega |
| Página do alerta | A página só de leitura que o contacto externo abre a partir da SMS |
| Contacto externo | Recebe as SMS; não tem a aplicação |

Os documentos só dizem que o backend é "um único serviço em Python, com o agente de IA ligado ao servidor MCP, e uma base de dados simples". A divisão do backend em Dispositivos, Motor, Agente de IA e Avisos é lógica e segue as frentes de trabalho do `PLANO.md`; ainda não existe em código.

## Arquitetura C4

O ficheiro `c4-arquitetura.drawio` abre-se no [diagrams.net](https://app.diagrams.net) (Ficheiro, Abrir de, Dispositivo) ou na extensão Draw.io do VS Code. Tem uma página por nível:

| Página | O que mostra |
|--------|--------------|
| 1. Contexto | O Homaly como uma caixa só, as duas pessoas (responsável e contacto externo) e os sistemas externos: servidor MCP, Keycloak, dispositivos da casa, modelo de IA e textbee |
| 2. Contentores | O que corre dentro do Homaly: a PWA, a página do alerta, o backend e a base de dados |
| 3. Componentes do backend | Os cinco componentes dos diagramas de sequência (API, Dispositivos, Motor, Agente de IA, Avisos) e quem fala com quem |

Os nomes, as setas e as tecnologias são os mesmos dos diagramas de sequência. Cores e formas seguem a biblioteca C4 do draw.io; a legenda está no fundo de cada página.

O que o C4 assume e os documentos ainda não fixam:

- **FastAPI e uvicorn no backend:** o `docker-compose.yml` já arranca `uvicorn backend.main:app`, mas o `backend/pyproject.toml` ainda não tem dependências.
- **SQLite:** está em "Proposto, ainda não aceite" no `DECISIONS.md`; o diagrama marca-o como "proposto".
- **Página do alerta como contentor à parte:** desenhada assim porque o contacto externo não tem a aplicação. Quem a serve está por definir (lacuna 1, mais abaixo); pode ser o próprio backend.
- **Token com `grant_type=password`:** o backend obtém o token no Keycloak da mesma forma que `scripts/mcp_headers.sh`, como pede o `AGENTS.md`.
- **Quem lê a câmara:** o componente Dispositivos capta as imagens do stream RTSP, tal como na US13; o Agente de IA passa-as ao modelo de visão.

## Convenções dos diagramas de sequência

- Seta a cheio: pedido. Seta tracejada: resposta. Seta aberta (`->>`): mensagem pelo WebSocket.
- `ref over`: remete para outro diagrama.
- "Por confirmar" e "por definir": o que os documentos deixam em aberto.

## O que os diagramas acrescentam aos documentos

- **Polling com `get_home_devices`:** devolve todos os dispositivos com os valores numa só chamada (confirmado a 2026-11-17), por isso cada ciclo de leitura é um único pedido ao MCP.
- **Confirmar a ação (US03):** depois de apagar a lâmpada, a casa lê o estado de novo com `get_device_details` para confirmar o resultado.
- **Quem decide na casa vazia (US07):** a IA escreve a explicação, mas não decide se avisa; o alerta é sempre imediato.
- **Na US13 quem chama o modelo de visão é o Agente de IA**, e o Motor compara a descrição com os veículos conhecidos.

## Lacunas e inconsistências encontradas

1. **Página do alerta (US05):** o contrato em `docs/frontend-design.md` não tem rota nem pedido para ela, nem diz quem a serve ou como o link identifica o alerta.
2. **Proposta de silêncio (US02):** a casa diz o que vai deixar de avisar e espera confirmação, mas a `Anomalia` não tem campo para a resposta da casa e não há pedido para confirmar.
3. **Nome da ferramenta do alarme:** a US07 refere `GET_HOME_SECURITY_STATE`; no servidor chama-se `get_home_security_status`.
4. **US04:** diz "a aplicação funciona normalmente, só com os moradores", mas a decisão é que só o responsável tem a aplicação.
5. **`PLANO.md`, "Como funciona", passo 4:** diz que o contacto é avisado se não houver resposta em cinco minutos, sem as exceções decididas: só segurança e bem-estar e rotina, tempo de espera configurável (pode ser zero) e aviso imediato com a casa vazia.
6. **Dispositivo comandável:** a US03 diz que a lâmpada é o único; a tomada inteligente também se comanda e está em aberto.
7. **US08:** não diz o que acontece ao aviso quando a porta fecha depois de ele ser enviado; a US12 diz que fica resolvido.
8. **US05, SMS de resolvido:** só fala da anomalia "resolvida pelo responsável". Fica por decidir se também se envia quando a anomalia se resolve sozinha (por exemplo, a porta fecha depois de um aviso da US12 ter passado a segurança).
