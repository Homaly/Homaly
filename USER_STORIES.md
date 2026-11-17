# User stories do MVP

Hackathon by Aveiro Tech City, Desafio #3 (Altice Labs). Versão de 2026-11-16.

Foco: a casa que repara, centrada na deteção de anomalias. As decisões em que estas histórias assentam estão em `DECISIONS.md`.

## Personagens

- **Responsável da casa:** a única pessoa com acesso à aplicação de uma casa. Normalmente vive lá, mas pode não viver: na casa de uma mãe idosa que vive sozinha, o responsável é o filho.
- **Contacto externo:** pessoa de fora que o responsável escolheu para receber alertas quando ele não responde (por exemplo, um vizinho ou outro familiar). Não tem a aplicação; recebe os alertas por SMS, com um link para uma página com o alerta, sem instalar nada.

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
| US09 | A porta não abriu à hora habitual | Bem-estar e rotina | Porta |
| US10 | Casa fria durante horas | Saúde e conforto | Temperatura |
| US11 | Luz acesa há demasiado tempo | Eficiência energética | Lâmpada, porta |
| US12 | Porta aberta com a casa a arrefecer | Eficiência energética | Porta, temperatura |
| US13 | Veículo desconhecido na entrada | Segurança | Câmara |
| US14 | Aparelho esquecido ligado | Eficiência energética | Tomada |

## Histórias transversais

### US01 — Contar à casa o dia a dia

**Como** responsável da casa, **quero** dizer à casa por palavras o que vai mudar na rotina, **para** ela não me avisar de coisas que eu já sei.

**Critérios de aceitação**
- **Dado** que escrevo "amanhã vamos de férias uma semana", **então** a casa confirma o que percebeu e durante esse período não avisa que a porta não abriu.
- **Dado** que disse à casa que vamos de férias, **quando** a porta abre durante esse período, **então** a casa trata-o como alerta de segurança (US07), em vez de o ignorar.
- **Dado** que escrevo "a empregada vem às terças à tarde", **então** a casa deixa de tratar a porta a abrir nesse período como anomalia.
- **Dado** que a casa não percebeu a mensagem, **então** pede para eu a dizer de outra forma, sem assumir nada.

### US02 — Receber uma anomalia e responder

**Como** responsável da casa, **quero** receber no telemóvel uma notificação que explique o que a casa estranhou e me deixe responder, **para** resolver o assunto sem abrir várias páginas.

**Critérios de aceitação**
- **Dado** que a casa detetou uma anomalia, **então** recebo uma notificação com o que aconteceu, o que é habitual e a que classe pertence.
- **Dado** que respondo "está tudo bem" sem dar motivo, **então** a anomalia fica resolvida e registada, mas só esta ocorrência: se voltar a acontecer, a casa avisa outra vez.
- **Dado** que explico o motivo, **então** a casa diz o que vai deixar de avisar e até quando (por exemplo, "não volto a avisar sobre a porta até amanhã, ok?"), e só aplica depois de eu confirmar.
- **Dado** que o motivo é temporário ("fiquei em casa doente"), **então** a casa deixa de avisar sobre esse tipo de anomalia até ao fim do dia.
- **Dado** que o motivo é recorrente ("a empregada vem às terças"), **então** passa a fazer parte da rotina da casa (US01) até eu o remover.
- **Dado** que a anomalia é de segurança, **então** a casa nunca a silencia para além da ocorrência atual, a não ser com uma regra recorrente explícita.

### US03 — Autorizar a casa a agir

**Como** responsável da casa, **quero** que a casa me proponha uma ação e só a execute se eu aceitar, **para** ela nunca fazer nada sem a minha autorização.

**Critérios de aceitação**
- **Dado** que a anomalia tem uma ação possível, **então** a notificação inclui um botão para a aceitar.
- **Dado** que aceito, **então** a casa executa a ação e confirma o resultado.
- **Dado** que recuso ou não respondo, **então** a casa não age.

**Dispositivos:** lâmpada e tomada inteligente, os dois dispositivos que a casa comanda. Depois de agir, a casa lê de novo o estado do dispositivo para confirmar o resultado.

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
- **Dado** que recebo a SMS, **então** ela traz um link para uma página com o alerta e o estado atual, que abro sem instalar nada. A página é só de leitura.
- **Dado** que abro o link depois de a anomalia se resolver, **então** a página mostra que está resolvida e como ("a porta fechou às 14:12").
- **Dado** que passaram mais de 24 horas desde a SMS, **então** o link já não mostra o alerta, só que expirou.
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
- **Dado** que a casa devia estar vazia (disse à casa que vamos de férias, ou o alarme está armado em modo ausente), **quando** a porta abre a qualquer hora, **então** recebo uma notificação de imediato e o contacto externo é avisado ao mesmo tempo, sem esperar o tempo de espera da casa.

**Dispositivos:** sensor de porta. O estado do alarme lê-se pelo servidor MCP (`get_home_security_status`).

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

### US09 — A porta não abriu à hora habitual (Bem-estar e rotina)

**Como** responsável da casa, **quero** que a casa repare quando a manhã de quem lá vive foge ao habitual, **para** saber cedo se alguém não estiver bem.

**Critérios de aceitação**
- **Dado** que a porta abre habitualmente antes das 10h, **quando** não abre até às 10h30, **então** recebo uma notificação com a hora habitual e o que aconteceu hoje.
- **Dado** que disse à casa que ia ficar em casa, **então** a casa não avisa.

**Dispositivos:** sensor de porta. Na demo, precisa de histórico simulado e de relógio acelerado.

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

**Como** responsável da casa, **quero** que a casa me pergunte quando o aparelho ligado à tomada está a gastar há muito mais tempo do que é costume, **para** o desligar à distância e não gastar energia nem correr riscos.

**Critérios de aceitação**
- **Dado** que o aparelho na tomada costuma estar ligado no máximo uma hora seguida, **quando** está a gastar há três horas, **então** recebo "o aquecedor está ligado há três horas, desligo?" com o consumo atual e a ação de desligar a tomada.
- **Dado** que aceito desligar, **então** a casa desliga a tomada e confirma (US03).
- **Dado** que respondo que ainda está a ser usado, **então** a casa não volta a perguntar nesse dia.
- **Dado** que a casa devia estar vazia (férias ditas à casa, ou alarme armado em modo ausente), **quando** a tomada está a gastar, **então** o aviso é de segurança, é imediato e segue as regras do contacto externo (US05).
- **Dado** que o aparelho deixa de gastar, **então** a anomalia resolve-se sozinha.

**Dispositivos:** tomada inteligente, que mede a potência e se liga e desliga pelo servidor MCP. "A gastar" quer dizer potência acima de um limite baixo (por exemplo, 10 W), a afinar. A casa sabe que aparelho está na tomada porque o responsável lho diz na conversa ("na tomada está o aquecedor", US01); se não souber, diz "o aparelho na tomada". O tempo habitual vem do histórico; na demo, do dataset simulado.

## Limites conhecidos

- **Um sensor de porta não distingue entrar de sair.** A casa não sabe ao certo se há alguém lá dentro; só sabe que a porta abriu e fechou. Por isso a US11 pergunta em vez de afirmar que a pessoa saiu.
- **As anomalias de rotina precisam de histórico.** Na demo, esse histórico vem do dataset simulado.
- **Fora do MVP:** as restantes anomalias que dependem da câmara, a classe Estado da própria casa, a classe Sono e noite, o fumo e as automatizações.
