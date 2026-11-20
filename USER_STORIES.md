# User stories do MVP

Hackathon by Aveiro Tech City, Desafio #3 (Altice Labs). Versão de 2026-11-16.

Foco: a casa que repara, centrada na deteção de anomalias. As decisões em que estas histórias assentam estão em `DECISIONS.md`.

## Personagens

- **Responsável da casa:** a única pessoa com acesso à aplicação de uma casa. Normalmente vive lá, mas pode não viver: na casa de uma mãe idosa que vive sozinha, o responsável é o filho.
- **Contacto externo:** pessoa de fora que o responsável escolheu para receber alertas quando ele não responde (por exemplo, um vizinho ou outro familiar). Não tem a aplicação; recebe os alertas por SMS, sem instalar nada.

## Resumo

| # | História | Tipo | Dispositivos |
|---|----------|------|--------------|
| US01 | Contar à casa o dia a dia | Transversal | — |
| US02 | Receber uma anomalia e responder | Transversal | — |
| US03 | Autorizar a casa a agir | Transversal | Lâmpada, tomada |
| US04 | Escolher um contacto externo | Transversal | — |
| US05 | Ser avisado como contacto externo | Transversal | — |
| US06 | Ver o que aconteceu em casa | Transversal | Todos |
| US07 | Porta aberta a uma hora anormal | Segurança | Porta |
| US08 | Porta esquecida aberta | Segurança | Porta |
| US09 | A casa não vê sinais de vida | Bem-estar e rotina | Câmara, lâmpada, tomada, porta |
| US10 | Casa fria durante horas | Saúde e conforto | Temperatura |
| US11 | Luz acesa há demasiado tempo | Eficiência energética | Lâmpada, porta |
| US12 | Porta aberta com a casa a arrefecer | Eficiência energética | Porta, temperatura |
| US13 | Veículo desconhecido na entrada | Segurança | Câmara |
| US14 | Aparelho esquecido ligado | Eficiência energética | Tomada, porta, câmaras de dentro |
| US15 | Água a correr sem parar | Eficiência energética / Segurança | Contador de água (simulado) |

## Histórias transversais

### US01 — Contar à casa o dia a dia

**Como** responsável da casa, **quero** dizer à casa por palavras o que vai mudar na rotina, **para** ela não me avisar de coisas que eu já sei.

**Critérios de aceitação**
- **Dado** que escrevo "amanhã vamos de férias uma semana", **então** a casa confirma o que percebeu e durante esse período não avisa que não vê sinais de vida (US09).
- **Dado** que disse à casa que vamos de férias, **quando** a porta abre durante esse período, **então** a casa trata-o como alerta de segurança (US07), em vez de o ignorar.
- **Dado** que escrevo "a empregada vem às terças à tarde", **então** a casa deixa de tratar a porta a abrir nesse período como anomalia.
- **Dado** que a casa não percebeu a mensagem, **então** pede para eu a dizer de outra forma, sem assumir nada.

### US02 — Receber uma anomalia e responder

**Como** responsável da casa, **quero** receber no telemóvel uma notificação que explique o que a casa estranhou e me deixe responder, **para** resolver o assunto sem abrir várias páginas.

**Critérios de aceitação**
- **Dado** que a casa detetou uma anomalia, **então** recebo uma notificação com o que aconteceu, o que é habitual e a que classe pertence.
- **Dado** que toco em "Está tudo bem" (um botão só, sem justificar nada), **então** a anomalia fica resolvida e registada, mas só esta ocorrência: se voltar a acontecer, a casa avisa outra vez. Serve tanto para um falso alarme como para um problema que eu já tratei.
- **Dado** que o mesmo aviso se repete à mesma hora (três vezes no mesmo dia da semana em quatro semanas, ou em três dias seguidos), **então** a casa propõe passar a contar com isso como rotina (por exemplo, "a porta abre a esta hora, terça-feira, às 10:00") e só a guarda depois de eu confirmar.
- **Dado** que recuso a proposta, **então** a casa continua a avisar e não volta a propor a mesma rotina.
- **Dado** que a anomalia é a porta esquecida aberta (US08), **então** a casa nunca propõe uma rotina para ela.

### US03 — Autorizar a casa a agir

**Como** responsável da casa, **quero** que a casa me proponha uma ação e só a execute se eu aceitar, **para** ela nunca fazer nada sem a minha autorização.

**Critérios de aceitação**
- **Dado** que a anomalia tem uma ação possível, **então** o aviso tem dois botões: a ação, com o nome dela ("Apagar a luz", "Desligar a tomada"), e "Está tudo bem".
- **Dado** que carrego na ação, **então** a casa executa-a e confirma o resultado.
- **Dado** que carrego em "Está tudo bem" ou não respondo, **então** a casa não age. "Está tudo bem" fecha só este aviso: se voltar a acontecer, mesmo no mesmo dia, a casa pergunta outra vez (e, se se repetir à mesma hora, propõe uma rotina, US02).

**Dispositivos:** lâmpada e tomada inteligente, os dois dispositivos que a casa comanda, e a válvula da água (simulada, US15). Depois de agir, a casa lê de novo o estado do dispositivo para confirmar o resultado.

### US04 — Escolher um contacto externo

**Como** responsável da casa, **quero** indicar uma pessoa de fora que receba os alertas da minha casa, **para** alguém saber quando eu não respondo.

**Critérios de aceitação**
- **Dado** que indico um contacto (nome e número de telemóvel), **então** ele passa a receber os alertas desta casa por SMS.
- **Dado** que removo o contacto, **então** ele deixa de receber alertas.
- **Dado** que não indico ninguém, **então** a aplicação funciona normalmente, só com os moradores.

### US05 — Ser avisado como contacto externo

**Como** contacto externo, **quero** receber uma mensagem clara quando a casa de alguém de quem cuido estranha alguma coisa, **para** poder ligar ou ir lá.

**Critérios de aceitação**
- **Dado** que há uma anomalia que me deve chegar, **então** recebo uma SMS com o que aconteceu, a que horas e o que é habitual.
- **Dado** que recebo a SMS, **então** ela basta: não traz link nem pede para abrir nada.
- **Dado** que a anomalia é de segurança ou de bem-estar e rotina, **quando** o responsável não responde dentro do tempo de espera da casa (cinco minutos por omissão), **então** recebo a mensagem.
- **Dado** que o tempo de espera da casa é zero, **então** recebo a mensagem ao mesmo tempo que o responsável.
- **Dado** que a anomalia é de eficiência energética ou de saúde e conforto, **então** não recebo nada.
- **Dado** que já recebi uma SMS sobre uma anomalia, **quando** ela fica resolvida, pelo responsável ou sozinha (por exemplo, a porta fechou), **então** recebo uma segunda SMS a dizer que está resolvida e como.

### US06 — Ver o que aconteceu em casa

**Como** responsável da casa, **quero** ver a lista do que os sensores registaram e das anomalias detetadas, **para** perceber porque é que a casa me avisou.

**Critérios de aceitação**
- **Dado** que abro o histórico, **então** vejo os eventos por ordem, do mais recente para o mais antigo.
- **Dado** que abro uma anomalia, **então** vejo a explicação da casa e a resposta que foi dada.

## Histórias de anomalias

### US07 — Porta aberta a uma hora anormal (Segurança)

**Como** responsável da casa, **quero** ser avisado quando a porta da rua abre a uma hora em que nunca abre, ou enquanto a casa devia estar vazia, **para** saber se entrou ou saiu alguém que não devia.

**Critérios de aceitação**
- **Dado** que no histórico a porta nunca abre entre a meia-noite e as 6h, **quando** abre às 3h10, **então** recebo uma notificação de imediato.
- **Dado** que avisei antes que ia chegar tarde, **então** a casa não avisa.
- **Dado** que a casa devia estar vazia (disse à casa que vamos de férias), **quando** a porta abre a qualquer hora, **então** recebo uma notificação de imediato e o contacto externo é avisado ao mesmo tempo, sem esperar o tempo de espera da casa.

**Dispositivos:** sensor de porta. A casa vazia vem só das férias ditas à casa: o alarme do kit é só de fumo, não há alarme de intrusão para armar.

### US08 — Porta esquecida aberta (Segurança)

**Como** responsável da casa, **quero** ser avisado quando a porta da rua fica aberta mais de cinco minutos, **para** a ir fechar.

**Critérios de aceitação**
- **Dado** que a porta abriu, **quando** passam cinco minutos sem fechar, **então** recebo uma notificação.
- **Dado** que a porta fecha antes dos cinco minutos, **então** não recebo nada.
- **Dado** que este aviso já foi enviado, **quando** a temperatura começa a descer com a porta ainda aberta, **então** a casa acrescenta isso ao mesmo aviso em vez de enviar outro (ver US12).
- **Dado** que a casa já avisou que a sala está a arrefecer com a porta aberta (US12), **quando** passam cinco minutos sem a porta fechar, **então** não recebo um segundo aviso: o existente passa a ser de segurança e diz que a porta está aberta há cinco minutos.
- **Dado** que já recebi o aviso, **quando** a porta fecha, **então** o aviso resolve-se sozinho, fica no histórico com a hora a que a porta fechou ("resolvido: a porta fechou às 14:12") e o tempo de espera do contacto externo é cancelado.
- **Dado** que o contacto externo já tinha recebido uma SMS, **quando** a porta fecha, **então** ele recebe a SMS de resolvido (US05).

**Dispositivos:** sensor de porta.

### US09 — A casa não vê sinais de vida (Bem-estar e rotina)

**Como** responsável da casa, **quero** que a casa repare quando deixa de haver sinais de vida de quem lá vive, **para** saber cedo se alguém desmaiou, caiu ou não está bem.

Um **sinal de vida** é qualquer coisa que mostre que alguém está a mexer na casa: movimento ou som na câmara, a lâmpada ligada, desligada ou com o brilho mudado, a tomada a começar a gastar (a chaleira, a máquina do café, a televisão) ou a porta a abrir. A porta passa a ser um sinal entre vários, em vez do único.

**Critérios de aceitação**

*Manhã sem atividade*
- **Dado** que no histórico o primeiro sinal de vida do dia chega habitualmente antes das 9h, **quando** não há nenhum até à hora limite (a habitual mais a margem, por exemplo 10h30), **então** recebo uma notificação com a hora habitual e o último sinal visto ("o último sinal foi a luz desligada às 23:40 de ontem").

*A atividade parou*
- **Dado** que hoje já houve sinais de vida e o último não foi a porta (a pessoa deve estar em casa), **quando** passam três horas sem nenhum sinal, a uma hora em que o histórico mostra atividade, **então** recebo uma notificação com a hora e o tipo do último sinal ("o último movimento na sala foi às 14:20").
- **Dado** que o último sinal foi a porta a abrir e fechar, **então** a casa não conta esse silêncio: a pessoa pode ter saído. Se ela voltar, a câmara vê-a entrar e a vigilância recomeça.
- **Dado** que é uma hora em que o histórico não mostra atividade (a pessoa costuma estar a dormir), **então** o silêncio não conta.

*Comum aos dois casos*
- **Dado** que a casa já avisou, **quando** aparece um sinal de vida, **então** a anomalia resolve-se sozinha e fica no histórico com o sinal e a hora ("resolvido: movimento na câmara às 11:05"). Se o contacto externo já tinha recebido uma SMS, recebe a SMS de resolvido (US05).
- **Dado** que disse à casa que ia ficar em casa, **então** a casa continua a vigiar: é com a pessoa em casa que uma queda pode acontecer. Ficar em casa só quer dizer que a porta pode não abrir.
- **Dado** que a casa devia estar vazia (férias ditas à casa), **então** a casa não avisa. Se a anomalia já estava ativa, resolve-se com esse motivo, e não "sozinha".
- **Dado** que um dispositivo deixou de comunicar, **então** o silêncio dele não conta como falta de atividade. Se nenhum dispositivo que dá sinais de vida comunica, a casa não sabe o que se passa e não avisa por bem-estar.

**Dispositivos:** câmara (só `motionDetected` e `soundDetected`, pelo servidor MCP, sem imagem), lâmpada, tomada e sensor de porta. A câmara tem de estar dentro de casa, na divisão onde a pessoa passa mais tempo. O formato de `motionDetected` quando há movimento ainda não foi confirmado (a 2026-11-19 vinha vazio), nem se `motionHumanoidFilter` o limita a pessoas. A margem da manhã e as três horas são valores a afinar com o histórico. Na demo, precisa de histórico simulado com a câmara e a lâmpada, além da porta e da tomada, e de relógio acelerado.

### US10 — Casa fria durante horas (Saúde e conforto)

**Como** responsável da casa, **quero** ser avisado quando a casa está fria há muito tempo, **para** resolver antes que faça mal à saúde.

**Critérios de aceitação**
- **Dado** que a temperatura está abaixo de 16 graus, **quando** assim se mantém durante duas horas, **então** recebo uma notificação com a temperatura atual e a habitual a essa hora.
- **Dado** que a temperatura volta a subir acima de 16 graus, **então** a anomalia fica resolvida sozinha.

**Dispositivos:** sensor de temperatura. O limite de duas horas é um valor a afinar.

### US11 — Luz acesa há demasiado tempo (Eficiência energética)

**Como** responsável da casa, **quero** que a casa me pergunte quando a luz está acesa há muito mais tempo do que é costume, **para** não gastar energia sem dar por isso.

**Critérios de aceitação**
- **Dado** que a lâmpada está acesa há cinco horas e a porta abriu e fechou depois de ela ser acesa, **então** recebo "esta luz está acesa há cinco horas, ainda estão a usar?".
- **Dado** que aceito apagar, **então** a casa apaga a lâmpada (US03).
- **Dado** que respondo que ainda estou a usar, **então** a casa não volta a perguntar nesse dia.

**Dispositivos:** lâmpada, sensor de porta. Depende de o servidor MCP permitir ler o estado da lâmpada.

### US12 — Porta aberta com a casa a arrefecer (Eficiência energética)

**Como** responsável da casa, **quero** ser avisado quando a porta está aberta e a temperatura está a cair, **para** não deixar fugir o calor.

**Critérios de aceitação**
- **Dado** que a porta está aberta, **quando** a temperatura desce dois graus desde que abriu, **então** recebo uma notificação com a descida.
- **Dado** que a porta fecha, **então** a anomalia fica resolvida.
- **Dado** que já recebi o aviso de porta esquecida aberta (US08) por esta mesma abertura, **então** não recebo uma segunda notificação: o aviso existente é atualizado com "e a sala já desceu 2 °C".
- **Dado** que este aviso chegou primeiro, **quando** a porta continua aberta ao fim de cinco minutos, **então** o mesmo aviso passa a ser de segurança (ver US08).

**Dispositivos:** sensor de porta, sensor de temperatura. A casa não sabe se o aquecimento está ligado; só vê a temperatura a descer.

### US13 — Veículo desconhecido na entrada (Segurança)

**Como** responsável da casa, **quero** ser avisado quando a câmara vê na entrada de veículos um veículo que a casa não conhece, **para** saber se está lá alguém que não devia.

**Critérios de aceitação**
- **Dado** que a câmara vê na entrada de veículos um veículo que não corresponde a nenhum dos conhecidos, **quando** ele lá permanece mais de dois minutos, **então** recebo uma notificação com a imagem, a hora e a descrição do veículo.
- **Dado** que o veículo é um dos conhecidos da casa, **então** não recebo nada.
- **Dado** que respondo que o veículo é conhecido ("é o carro do meu irmão"), **então** a casa guarda-o e não volta a avisar quando ele aparecer.
- **Dado** que avisei antes que vinha alguém de carro (US01), **então** a casa não avisa.
- **Dado** que não respondo dentro do tempo de espera da casa, **então** o contacto externo é avisado (US05).

**Dispositivos:** câmara, apontada à entrada de veículos. A imagem vem do stream RTSP da câmara, fora do servidor MCP. Os dois minutos são um valor a afinar, para não avisar por quem só faz inversão de marcha. Falta decidir como a casa reconhece um veículo: pela matrícula ou pelo aspeto (tipo e cor), conforme a qualidade da imagem.

### US14 — Aparelho esquecido ligado (Eficiência energética)

**Como** responsável da casa, **quero** que a casa me pergunte quando o aparelho ligado à tomada fica a gastar sem ninguém a usá-lo, **para** o desligar à distância e não gastar energia nem correr riscos.

A casa junta a tomada, a porta e o movimento das câmaras de dentro de casa para saber se alguém saiu, se está ao pé do aparelho ou noutra divisão.

**Critérios de aceitação**
- **Dado** que há movimento na divisão da tomada, **então** a casa não avisa: alguém está a usar o aparelho. Se já tinha avisado, a anomalia resolve-se ("voltou a haver alguém na sala às 14:32").
- **Dado** que o aquecedor está a gastar, **quando** a porta abre e fecha depois de ele ligar e não há movimento em casa durante 20 minutos, **então** recebo "o aquecedor está a gastar desde as 14:05, e a porta fechou às 14:11 sem movimento em casa desde então: parece que saíram", com a ação de desligar a tomada.
- **Dado** que há alguém em casa mas não na divisão da tomada há uma hora, **quando** o aparelho precisa de alguém por perto (um aquecedor, um ferro, a televisão), **então** recebo "o aquecedor está a gastar e não há ninguém na sala desde as 14:05 (há movimento na cozinha)", com a ação de desligar a tomada.
- **Dado** que o aparelho pode ficar a trabalhar sozinho (a máquina de lavar, o frigorífico), ou que a casa não tem câmaras dentro de casa, **quando** está a gastar há muito mais tempo do que é costume (três vezes o período mais longo do histórico), **então** recebo o aviso, com o consumo atual e a ação de desligar a tomada.
- **Dado** que aceito desligar, **então** a casa desliga a tomada e confirma (US03).
- **Dado** que carrego em "Está tudo bem", **então** a casa não age e fecha só este aviso (US03).
- **Dado** que a casa devia estar vazia (férias ditas à casa), **quando** a tomada está a gastar, **então** o aviso é de segurança, é imediato e segue as regras do contacto externo (US05).
- **Dado** que o aparelho deixa de gastar, **então** a anomalia resolve-se sozinha.

**Dispositivos:** tomada inteligente, que mede a potência e se liga e desliga pelo servidor MCP; sensor de porta; câmaras de dentro de casa (só `motionDetected`). "A gastar" quer dizer potência acima de um limite baixo (por exemplo, 10 W), a afinar. A casa sabe que aparelho está na tomada porque o responsável lho diz na conversa ("na tomada está o aquecedor", US01); se não souber, diz "o aparelho na tomada" e trata-o como um que precisa de alguém por perto. A câmara do kit está na sala; as outras divisões têm a sua (`camara_<divisão>`; na demo, injetadas por `/dev/leituras`). Os tempos (10 minutos de movimento recente, 20 para "saíram", uma hora sem ninguém na divisão) vêm do histórico, onde há até 47 minutos sem movimento com o aparelho em uso; na demo, baixam-se no `.env`. O tempo habitual vem do histórico; na demo, do dataset simulado.

### US15 — Água a correr sem parar (Eficiência energética e Segurança)

**Como** responsável da casa, **quero** que a casa me avise quando a água corre sem parar, **para** fechar a torneira ou a água antes de a desperdiçar ou de haver estragos.

**Critérios de aceitação**
- **Dado** que a água corre sem parar há uma hora com um caudal normal, **então** recebo "a água está a correr sem parar desde as 18:00; uma torneira pode ter ficado aberta", com a ação de fechar a água.
- **Dado** que corre só um fio de água sem parar há uma hora (por exemplo, de madrugada), **então** recebo "corre um fio de água sem parar; pode ser um autoclismo ou uma torneira a pingar", com a ação de fechar a água.
- **Dado** que corre muita água (12 litros por minuto ou mais) durante cinco minutos, **então** o aviso é de segurança, é imediato ("pode ser um cano rebentado") e segue as regras do contacto externo (US05).
- **Dado** que a casa devia estar vazia (férias ditas à casa), **quando** a água corre, **então** o aviso é de segurança e imediato.
- **Dado** que aceito fechar a água, **então** a casa fecha a válvula e confirma (US03).
- **Dado** que a água pára, **então** a anomalia resolve-se sozinha e diz quantos litros correram.

**Dispositivos:** contador de água com válvula. O kit não o tem: na demo, o caudal (litros por minuto) entra pelas leituras injetadas (`/dev/leituras`, dispositivo `agua`, tipo `caudal`) e a válvula é simulada. "A correr" é um caudal acima de 0,1 L/min. Os limites (uma hora, 2 L/min para o fio de água, 12 L/min durante cinco minutos para o cano) afinam-se no `.env`. Um uso normal, como um banho ou a máquina da loiça, não chega a uma hora seguida.

## Limites conhecidos

- **Um sensor de porta não distingue entrar de sair.** A casa não sabe ao certo se há alguém lá dentro; só sabe que a porta abriu e fechou. Por isso a US11 pergunta em vez de afirmar que a pessoa saiu.
- **As anomalias de rotina precisam de histórico.** Na demo, esse histórico vem do dataset simulado.
- **Fora do MVP:** as restantes anomalias que dependem da câmara, a classe Estado da própria casa, a classe Sono e noite, o fumo e as automatizações.
