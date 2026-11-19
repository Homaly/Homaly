# Decisões

Hackathon by Aveiro Tech City, Desafio #3 (Altice Labs): "Connected Home, Reimagined".
Última atualização: 2026-11-16.

Cada entrada indica o grau de certeza. Só a secção "Decidido" reflete escolhas feitas pela equipa; as entradas em "Proposto" são sugestões ainda não aceites nem rejeitadas. As user stories do MVP estão em `USER_STORIES.md`.

## Numeração das ideias

| # | Ideia | O que faz |
|---|-------|-----------|
| 1 | Intenção, não comandos | A pessoa diz o que quer ou o que a preocupa em linguagem normal; a IA decide o que fazer com os dispositivos disponíveis. |
| 2 | A casa que repara | A casa aprende o que é habitual e repara quando algo foge a isso. |
| 3 | Missões para os miúdos | Objetivos da casa transformados em missões com gamificação e recompensas. |
| 4 | Automações que se escrevem sozinhas | A casa repara no que se faz à mão e propõe automatizar. |

## Decidido

### Foco

- **Ideia 2, a casa que repara, centrada na deteção de anomalias.**
- **Automatizações (ideia 4): fora do MVP.** Não são descartadas; ficam para o futuro.

### Classes de anomalias

| Classe | Anomalias | Dispositivos |
|--------|-----------|--------------|
| Segurança | Porta aberta a uma hora em que nunca abre; porta esquecida aberta; alguém visto com a casa vazia; veículo desconhecido na entrada de veículos | Porta, câmara |
| Bem-estar e rotina | Nenhuma atividade até à hora habitual; ninguém na cozinha às horas das refeições; vários dias sem sair; movimento repetido de madrugada; saiu e não voltou à hora de sempre | Porta, câmara, lâmpada |
| Saúde e conforto | Casa fria ou quente demais durante horas | Temperatura |
| Eficiência energética | Lâmpada acesa há demasiado tempo; porta aberta com a temperatura a cair; aparelho esquecido ligado na tomada | Lâmpada, porta, temperatura, tomada |
| Estado da própria casa | Um sensor deixou de comunicar; o gateway ficou sem ligação | Gateway, todos |

- **Entram no MVP quatro classes:** segurança, bem-estar e rotina, saúde e conforto, e eficiência energética.
- **Anomalias do MVP (oito):**

  | Classe | Anomalias no MVP | Dispositivos |
  |--------|------------------|--------------|
  | Segurança | A porta abriu a uma hora em que nunca abre; a porta ficou aberta mais de cinco minutos; veículo desconhecido na entrada de veículos | Porta, câmara |
  | Bem-estar e rotina | A porta não abriu até à hora habitual | Porta |
  | Saúde e conforto | Casa abaixo de 16 graus durante horas | Temperatura |
  | Eficiência energética | Lâmpada acesa há demasiado tempo; porta aberta com a temperatura a cair; aparelho esquecido ligado na tomada | Lâmpada, porta, temperatura, tomada |

  As restantes anomalias de cada classe ficam para os dias 3 e 4.
- **Estado da própria casa: fora do MVP.** Fica para mais tarde, por ser uma preocupação de longo prazo.
- **Visitas e cuidadores: fora do MVP.** Classe candidata sobre pessoas de fora que deviam aparecer e não apareceram (por exemplo, o apoio domiciliário das terças às 10h). Só precisa do sensor de porta.
- **Sono e noite: classe guardada para o futuro.** Cobre o que acontece enquanto a pessoa devia estar a dormir, por exemplo luz acesa às 3h em várias noites seguidas, ou deitar-se cada vez mais tarde. Usa a lâmpada e a câmara; depende de se conseguir ler o estado da lâmpada.
- **Fumo e fogo: postos de parte.** O detetor de fumo não entra no MVP; foi considerado pouco interessante, porque quem deteta é o detetor e não a casa.
- **Monóxido de carbono:** a incluir na classe Saúde e conforto como extensão futura. A equipa não vai ter esse detetor, por isso não é implementado.

### Quem usa e como é avisado

- **Cada casa é um agregado familiar.** Não existe no sistema a relação de dependente e cuidador.
- **Uma só conta por casa no MVP, usada por uma só pessoa:** o responsável da casa. Os restantes membros não têm acesso à aplicação.
- **Todas as casas têm um responsável**, que pode não viver lá. No caso da mãe idosa que vive sozinha, o responsável é o filho, e é ele que tem a aplicação.
- **Uma conta corresponde a uma só casa.** Uma pessoa responsável por duas casas fica fora do MVP.
- **Contacto externo opcional:** uma pessoa de fora pode receber os alertas de uma casa por mensagem. As casas e as aplicações não ficam ligadas entre si.
- **Tempo de espera antes de avisar o contacto externo:** cada casa tem um valor, cinco minutos por omissão, que pode ser zero para avisar ao mesmo tempo.
- **O contacto externo só recebe anomalias de segurança e de bem-estar e rotina.**
- **A casa pergunta antes de alarmar, por notificação no telemóvel**, por exemplo "esta luz está acesa há cinco horas, ainda estão a usar?". A pessoa responde na própria aplicação. No MVP, o aviso só chega com a aplicação aberta; as notificações com a aplicação fechada (push) vêm mais tarde.
- **A casa age com autorização:** quando a pessoa aceita na notificação, a casa executa a ação, por exemplo apagar a lâmpada.
- **A lâmpada não pisca para avisar.**
- **Conversa por texto na aplicação:** o responsável diz coisas à casa ("amanhã vamos de férias", "a empregada vem às terças") e a casa usa isso para não dar alarmes falsos.
- **De onde vem o "normal":** dos sensores e das conversas com a casa sobre o dia a dia.
- **Calendário Google (2026-11-18, mentores):** o responsável liga o Google Calendar em Definições com um botão (OAuth, só leitura), sem colar links. A IA tira férias, rotinas e compromissos, que entram logo, sem confirmação item a item; a lista "O que a casa sabe pelo calendário" mostra-os. Remover pede confirmação e apaga só o que veio do calendário. Só Google: a Apple não dá esta ligação a outras apps. Ver [o design](docs/superpowers/specs/2026-11-18-calendario-google-design.md).
- **Casa vazia sobe o alerta:** se a casa devia estar vazia (férias ditas à casa), a porta abrir a qualquer hora é um alerta de segurança imediato, e o contacto externo é avisado sem tempo de espera (US01, US07, US14). O alarme do kit é só de fumo; não há alarme de intrusão que diga que a casa está vazia.
- **Um aviso por porta aberta:** a porta esquecida aberta (US08) e a porta aberta com a casa a arrefecer (US12) partilham um só aviso por cada abertura da porta. Se a US08 avisou primeiro, a US12 não envia outra notificação; acrescenta a descida de temperatura ao mesmo aviso. Se a US12 avisou primeiro e a porta continua aberta ao fim de cinco minutos, o mesmo aviso passa a ser de segurança, e pode então chegar ao contacto externo.
- **Responder a um aviso (US02), revisto a 2026-11-18 depois da reunião com os mentores:** um botão só, "Está tudo bem", sem caixa de texto, que resolve aquela ocorrência e não ensina nada à casa. É a casa que repara quando um aviso se repete à mesma hora (três vezes no mesmo dia da semana em quatro semanas, ou em três dias seguidos) e propõe uma rotina; só a guarda se for aceite, e uma rotina recusada não volta a ser proposta. A US08 nunca dá rotina. Perdeu-se o "só por hoje" (silenciar até ao fim do dia). Desenho em `docs/superpowers/specs/2026-11-18-menos-intrusivo-design.md`.

### Como se constrói

- **Começar do zero.** Não construir em cima do código do semestre passado.
- **Aproveitar** o que for útil desse projeto: fluxos existentes e, possivelmente, o frontend. Origem: `/home/simas/Documents/2º Ano/2º Semestre/IES/ies2526-group-project-ies2526_g403`.
- **Aplicação: página web**, feita para telemóvel.
- **Frontend:** React, Vite e TypeScript.
- **Aviso ao contacto externo: por SMS, como a Uber faz com os contactos de confiança.** A SMS traz um link para uma página simples com o alerta, que se abre sem instalar nada. Na página, o contacto só vê o alerta e o estado atual; não responde nem age.
- **Envio das SMS: [textbee](https://github.com/vernu/textbee)**, gratuito e open-source. Uma app Android num telemóvel com cartão SIM envia as SMS que o backend pede por API. As SMS saem do número desse telemóvel, que é o de um colega da equipa, e gastam o tarifário dele.
- **Na demo:** no telemóvel que recebe a SMS, o número do colega fica gravado como "Homaly". O telemóvel que envia tem de estar ligado, com internet e com a app do textbee aberta. Em produção, as SMS sairiam com o remetente "Homaly", por um fornecedor de SMS ou pela própria Altice, que é operadora.
- **Backend:** um único serviço em Python, com o agente de IA ligado ao servidor MCP da Altice, e uma base de dados simples.
- **Quem decide que é anomalia:** regras simples detetam que algo fugiu ao padrão; a IA avalia o contexto (o histórico e o que foi dito na conversa), decide se vale a pena avisar e escreve a explicação.
- **Dataset:** serve de histórico simulado da casa e de conjunto de casos para testar a deteção. Não se treina nenhum modelo de IA de raiz.
- **Leitura dos sensores:** os sensores não enviam eventos. O backend pergunta o estado dos dispositivos ao servidor MCP em intervalos regulares e deteta as mudanças comparando com a leitura anterior. O intervalo está por definir. Confirmado nas leituras de 2026-11-16: o servidor não tem subscrições e não dá a hora a que cada valor mudou (ver `docs/mcp-dispositivos.md`).
- **Porta e lâmpada dadas como verificadas** (2026-11-17): o sensor de porta indica `alarm` com a porta aberta e `normal` com ela fechada, e a lâmpada está ligada e comunica. A equipa assume-o como confirmado.
- **A porta fecha depois do aviso (US08):** o aviso resolve-se sozinho e fica no histórico com a hora a que a porta fechou. Se o tempo de espera ainda estava a contar, é cancelado; se o contacto externo já tinha recebido SMS, recebe a de resolvido.
- **Página do alerta (US05):** é o backend que a serve, como uma página HTML simples, sem login e fora da aplicação React. O link leva um código aleatório e longo, criado quando a SMS é enviada e associado a esse alerta; nunca o id da anomalia, para não se poderem adivinhar os alertas de outras casas. O link funciona 24 horas depois do envio, mesmo que a anomalia já esteja resolvida (aí mostra que está resolvida e como); depois disso só diz que expirou.
- **Proposta de silêncio (US02):** a proposta da casa ("não volto a avisar sobre a porta até ao fim do dia, ok?") vem na própria anomalia, e o responsável aceita ou recusa com um pedido próprio. O silêncio só se aplica depois de aceite. Detalhe no contrato, em `docs/frontend-design.md`.
- **Fuga de água (US15, 2026-11-19, mentores):** a casa lê um contador de água simulado (o kit não tem sensor de água) e avisa quando a água corre sem parar: uma hora (torneira aberta, ou um fio de água como um autoclismo a pingar) é eficiência; muita água durante cinco minutos (cano rebentado) ou água a correr com a casa vazia é segurança e imediato. A ação é fechar a água, numa válvula também simulada. Escolheu-se o contador e não um sensor de inundação no chão, porque apanha o desperdício e não só os estragos.
- **Tomada inteligente:** serve para a anomalia do aparelho esquecido ligado (US14) e passa a ser o segundo dispositivo que a casa comanda (US03), além da lâmpada.
- **SMS de resolvido:** se o contacto externo já recebeu uma SMS sobre uma anomalia, recebe outra quando ela fica resolvida, quer pelo responsável quer sozinha (por exemplo, a porta fechou).
- **User-Agent próprio nos pedidos ao MCP:** o servidor está atrás do Cloudflare, que recusa os pedidos com o User-Agent por omissão das bibliotecas. O backend envia `homaly-backend/0.1`.
- **Acesso ao servidor MCP:** a equipa já tem a API key. Fica no `.env`, que nunca é commitado.

### Onde ficam os dispositivos

- **Sensor de porta:** na porta da rua.
- **Lâmpada e sensor de temperatura:** na mesma divisão, a sala.
- **Câmara:** apontada à entrada de veículos da casa (ver US13).

### Equipa e tempo

- 5 pessoas. O trabalho é dividido por todos mais tarde.
- A competição começou na segunda-feira, 16 de novembro de 2026, às 17:30 (online).
- Quarta, 18: checkpoint obrigatório com os mentores (14:00–18:30) e entrega do Sumário Executivo até às 19:00.
- Sexta, 20 (presencial, Fábrica Centro Ciência Viva de Aveiro): avaliação intermédia às 16:00, entrega da apresentação às 17:30 e apresentações finais às 18:00.

### Material disponível

Uma unidade de cada:

| Dispositivo | Papel | O que o MCP dá |
|-------------|-------|----------------|
| Câmara | Sensor (no MVP, só para o veículo desconhecido) | Deteção de movimento e de som; nenhuma imagem |
| Sensor de temperatura | Sensor | Temperatura e humidade |
| Sensor de abertura de porta | Sensor | Estado `alarm` com a porta aberta e `normal` com a porta fechada |
| Detetor de fumo | Sensor (posto de parte) | Estado `normal` ou `alarm` |
| Lâmpada | Dispositivo que a casa consegue comandar | Ligada ou desligada, brilho, cor e tom do branco; lê-se e altera-se |
| Tomada (Plug) | Dispositivo que a casa consegue comandar | Ligada ou desligada, potência, tensão, corrente e consumo de hoje e de ontem |
| Gateway (Security hub) | Liga os dispositivos à rede | Estado do alarme (só de fumo), Wi-Fi e rede móvel |

O que cada dispositivo devolve, com os ids, está em `docs/mcp-dispositivos.md`. O que se pensava ser só um adaptador aparece no servidor como uma tomada inteligente com medição de consumo.

## Proposto, ainda não aceite

- **Sem Authentik, RabbitMQ nem InfluxDB.**
- **Histórico na demo:** a casa arranca com o dataset simulado pré-carregado e um relógio acelerado, para mostrar anomalias de rotina ao vivo.
- **Leituras simuladas na demo:** poder injetar leituras falsas dos sensores (por exemplo, a sala abaixo de 16 graus), para mostrar ao vivo anomalias que não se conseguem provocar na sala.
- **Base de dados:** SQLite, por ser um ficheiro sem servidor.
- **Salvaguarda de sensor em silêncio:** se um sensor deixar de enviar dados, a casa não conclui que nada aconteceu.
- **Perfil de quem vive na casa:** o responsável descreve as pessoas por palavras (idade, surdez, demência) e a casa ajusta que anomalias contam mais e como avisa.
- **Formas de anomalia** (atravessam as classes): algo que não aconteceu, e algo que nunca acontece.

## Em aberto

- O papel das ideias 1 e 3: funcionalidades futuras ou abandonadas.
- A cena da demo (a equipa decide mais tarde).
- A divisão das histórias pelos cinco: há uma proposta em `DIVISAO.md`; a equipa decide.
- Se as regras do hackathon permitem reaproveitar código escrito antes do evento.
- O modelo de IA e quem o fornece: a equipa está a ver como fazer (créditos da organização ou plano gratuito de um fornecedor).
- De quanto em quanto tempo o backend pergunta o estado dos sensores ao servidor MCP.
- Como a casa reconhece um veículo (US13): a matrícula sozinha parece demasiado simples; a equipa vai discutir.
- A imagem da câmara: o MCP só dá deteção de movimento e de som, sem imagem; a imagem vem do stream RTSP (`CAMERA_RTSP_URL`), que ainda não foi testado.
