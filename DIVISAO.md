# Divisão do trabalho

Versão de 2026-11-17. Proposta, até a equipa a aceitar. Base: `USER_STORIES.md`, `PLANO.md`, `DECISIONS.md` e a arquitetura C4 em `docs/diagramas/c4-arquitetura.drawio`.

## A ideia

Cada pessoa fica com algumas user stories e faz cada uma de ponta a ponta: a regra, a parte da IA, o que a aplicação mostra e o caso de teste no dataset. Assim cada um avança sem esperar pelos outros, e cada história tem um só dono.

Há uma exceção. Todas as histórias assentam na mesma base: a ligação ao MCP, o backend, a base de dados, o cliente do modelo de IA e o envio dos avisos. Se cada pessoa fizesse a sua, havia cinco ligações ao MCP e cinco formas de guardar uma anomalia. Por isso, **na terça cada pessoa faz uma peça da base**, só o mínimo para a US08 (porta esquecida aberta) funcionar de ponta a ponta. **A partir de quarta, trabalha-se por user stories.**

## Quem fica com o quê

| Pessoa | Nome | Peça da base (terça) | User stories (a partir de quarta) |
|--------|------|----------------------|-----------------------------------|
| A | Xuta | Ligação ao MCP | US08, US10, US12, US13 |
| B | Vila | Motor de regras, dataset simulado e Avisos | US07, US09 |
| C | Benny | Backend, base de dados, API, WebSocket e PWA ligada | US03, US06, US11 |
| D | Simão | Cliente do modelo de IA | US01, US02 |
| E | Candeias | SMS pelo textbee | US04, US05, mais a demo, o pitch e o sumário executivo |

Porquê estes grupos:

- **A:** a porta e a temperatura. A US08 e a US12 partilham um só aviso por cada abertura da porta, por isso ficam com a mesma pessoa. A US13 começa por captar a imagem da câmara, que é ler um dispositivo.
- **B:** as duas histórias que dependem do "habitual" da porta, que sai do dataset.
- **C:** a lâmpada (a US11 propõe apagá-la e a US03 executa a ação) e o histórico, que é sobretudo API e ecrã.
- **D:** as duas histórias em que a IA interpreta o que o responsável escreve.
- **E:** tudo o que chega ao contacto externo. Tem menos histórias porque coordena a demo e as entregas.

## A base, na terça

De manhã, combina-se em meia hora o que passa entre as peças (as setas da página 3 do C4). Depois, cada pessoa faz a sua peça, só até ao que a US08 precisa:

| Peça | Mínimo para a US08 | Quem |
|------|--------------------|------|
| Ligação ao MCP | Token no Keycloak como faz `scripts/mcp_headers.sh`; polling com `get_home_devices`; um evento quando a porta muda | A |
| Motor de regras | Onde se encaixa uma regra; a regra da US08; o começo do dataset | B |
| Backend e aplicação | FastAPI e uvicorn no `pyproject.toml`; `backend.main:app`, que o `docker-compose.yml` já arranca; base de dados; `/anomalias` e `/ws`; PWA com `VITE_USE_MOCKS=false` | C |
| IA | Escolher o modelo; transformar um desvio numa anomalia com título e explicação | D |
| Avisos | Publicar a anomalia na aplicação; tempo de espera | B |
| SMS | Uma SMS enviada pelo textbee | E |

Até a peça de outro estar pronta, cada um trabalha com dados falsos: a B com o dataset, a D com desvios escritos à mão, a C com os mocks que a PWA já tem, a E com anomalias escritas à mão.

**Ao fim do dia:** a porta aberta mais de cinco minutos chega como notificação ao telemóvel. A pessoa A junta as peças.

Depois de terça, quem fez uma peça é o guardião dela. Os outros acrescentam-lhe o que as suas histórias precisam, mas avisam o guardião, e é ele que resolve o que se partir.

## O que cada pessoa faz

### A: US08, US10, US12, US13

- **US08:** a regra dos cinco minutos, e o que acontece ao aviso quando a porta fecha depois de ele ser enviado (lacuna 7 de `docs/diagramas/README.md`).
- **US10:** abaixo de 16 °C durante duas horas, e a anomalia que se resolve sozinha. Se a proposta das leituras simuladas for aceite, a forma de as injetar na demo.
- **US12:** porta aberta com a temperatura a cair, junta ao aviso da US08.
- **US13:** captar imagens do stream RTSP, pedir a descrição ao modelo de visão (com o cliente da D) e comparar com os veículos conhecidos. É o maior risco do MVP: se não funcionar a tempo, sai, e a A ajuda noutras histórias.
- **Fechar:** se `sensorState: alarm` quer dizer porta aberta; o intervalo de polling; como a casa reconhece um veículo.

### B: US07, US09 e o dataset

- **Dataset simulado:** semanas de histórico da casa e um caso de teste para cada anomalia. Cada dono acrescenta os casos das suas histórias.
- **O "habitual":** a que horas a porta costuma abrir.
- **US07:** porta aberta a uma hora anormal. Com a casa vazia (férias ditas à casa, ou alarme armado lido com `get_home_security_status`), o alerta é imediato e não é a IA que decide.
- **US09:** a porta não abriu até à hora habitual.
- **Propostas a levar à equipa:** histórico pré-carregado e relógio acelerado na demo.
- **Fechar:** o nome errado da ferramenta do alarme na US07 (lacuna 3).

### C: US03, US06, US11

- **US03:** aceitar ou recusar a ação; executá-la com `update_device_capabilities` e confirmar lendo de novo com `get_device_details`.
- **US11:** a luz acesa há muito mais tempo do que é costume, com a pergunta e a ação.
- **US06:** `/eventos` e o ecrã do histórico.
- **Fechar:** se a lâmpada está ligada à rede (não comunica desde 4 de novembro; se não se conseguir ler, a US11 sai); para que serve a tomada (lacuna 6); a proposta do SQLite.
- Segundo `docs/frontend-design.md`, um colega diz já ter endpoints feitos sem push. Se não for a C, passa-os à C.

### D: US01, US02

- **Primeiro, na terça:** escolher o modelo e o fornecedor (créditos da organização ou plano gratuito) e acrescentar as variáveis ao `.env.example`.
- **US01:** a conversa: férias, rotinas recorrentes e mensagens que a casa não percebe; o pedido `/conversa`. O motor usa o que a conversa guarda.
- **US02:** as respostas às anomalias: fechar a ocorrência, silenciar até ao fim do dia ou criar uma rotina, dizendo sempre o que vai ignorar e esperando confirmação.
- **Fechar:** a proposta de silêncio não tem campo no contrato nem pedido para confirmar (lacuna 2); decide-se com a C.

### E: US04, US05, demo e entregas

- **US04:** o pedido `/definicoes`: o contacto externo e o tempo de espera.
- **US05:** a SMS pelo textbee, só para segurança e para bem-estar e rotina, imediata com a casa vazia; a página do alerta, só de leitura; a SMS de resolvido.
- **Demo:** a cena, o guião e os telemóveis. O que envia as SMS tem de estar ligado, com internet e com a app do textbee aberta.
- **Entregas:** coordenar o sumário executivo e a apresentação, com os modelos em `templates/`. Cada pessoa escreve a parte das suas histórias.
- **Fechar:** a rota da página do alerta (lacuna 1); a SMS de resolvido quando a anomalia se resolve sozinha (lacuna 8); a US04 ainda fala em "moradores" (lacuna 4); o passo 4 do `PLANO.md` sem as exceções do contacto externo (lacuna 5).
- **Propõe, e a equipa decide:** a cena da demo, o papel das ideias 1 e 3 no pitch, e se se pode reaproveitar código de antes do evento.

## Calendário

As datas são as da secção "Decidido" do `DECISIONS.md`: checkpoint e sumário executivo na quarta, apresentação final na sexta. O calendário do `PLANO.md` ainda conta com quatro dias e apresentação na quinta; está desatualizado nesse ponto. A primeira anomalia de ponta a ponta estava marcada para segunda à tarde e passa para terça.

Momentos de toda a equipa:

- **Terça 17, de manhã:** combinar o que passa entre as peças da base (meia hora).
- **Terça 17, ao fim do dia:** a US08 de ponta a ponta, do sensor à notificação.
- **Quarta 18:** checkpoint com os mentores das 14:00 às 18:30; entrega do sumário executivo até às 19:00 (coordena a E).
- **Sexta 20:** ensaio de manhã; avaliação intermédia às 16:00; entrega da apresentação até às 17:30; apresentações às 18:00.

O que cada pessoa faz em cada dia:

| Dia | A | B | C | D | E |
|-----|---|---|---|---|---|
| **Terça 17** | Ligação ao MCP | Motor de regras, dataset e avisos | Backend e PWA ligada | Modelo de IA e explicação | SMS pelo textbee |
| **Quarta 18 (até ao checkpoint)** | US10 e US12 | US07 | US03 | US02 | US04 e US05 |
| **Quinta 19** | US13 | US09; afinar a deteção com o dataset | US11 e US06 | US01 | Página do alerta; escolher e ensaiar a cena da demo |

## Para não se atropelarem

- Cada história nos seus próprios ficheiros (por exemplo, `backend/src/backend/motor/regras/us08.py`), para duas pessoas raramente mexerem no mesmo.
- Mexer numa peça da base, ou nos ficheiros partilhados (`main.py`, `contract.ts`, `docker-compose.yml`, `.env.example`), só avisando o guardião ou a equipa.
- O contrato entre a PWA e o backend (`docs/frontend-design.md` e `frontend/src/types/contract.ts`) só muda com o acordo da C.
- `git pull --rebase` antes de cada push, e commits pequenos.
- O `docs/diagramas/c4-arquitetura.drawio` é uma só linha de texto, por isso o git não junta alterações de duas pessoas. Edita-o uma pessoa de cada vez.
- Os commits feitos com agentes de IA levam a linha `Co-Authored-By` (ver `AGENTS.md`). O `.env` nunca vai para o repositório.
