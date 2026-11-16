# User stories do MVP

Hackathon by Aveiro Tech City, Desafio #3 (Altice Labs). Versão de 2026-11-15.

Foco: a casa que repara, centrada na deteção de anomalias. As decisões em que estas histórias assentam estão em `DECISIONS.md`.

## Personagens

- **Responsável da casa:** a única pessoa com acesso à aplicação de uma casa. Normalmente vive lá, mas pode não viver: na casa de uma mãe idosa que vive sozinha, o responsável é o filho.
- **Contacto externo:** pessoa de fora que o responsável escolheu para receber alertas quando ele não responde (por exemplo, um vizinho ou outro familiar). Não tem a aplicação; recebe mensagens por um bot de Telegram.

## Resumo

| # | História | Tipo | Dispositivos |
|---|----------|------|--------------|
| US01 | Contar à casa o dia a dia | Transversal | — |
| US02 | Receber uma anomalia e responder | Transversal | — |
| US03 | Autorizar a casa a agir | Transversal | Lâmpada |
| US04 | Escolher um contacto externo | Transversal | — |
| US05 | Ser avisado como contacto externo | Transversal | — |
| US06 | Ver o que aconteceu em casa | Transversal | Todos |
| US07 | Porta aberta a uma hora anormal | Segurança | Porta |
| US08 | Porta esquecida aberta | Segurança | Porta |
| US09 | A porta não abriu à hora habitual | Bem-estar e rotina | Porta |
| US10 | Casa fria durante horas | Saúde e conforto | Temperatura |
| US11 | Luz acesa há demasiado tempo | Eficiência energética | Lâmpada, porta |
| US12 | Porta aberta com a casa a arrefecer | Eficiência energética | Porta, temperatura |

## Histórias transversais

### US01 — Contar à casa o dia a dia

**Como** responsável da casa, **quero** dizer à casa por palavras o que vai mudar na rotina, **para** ela não me avisar de coisas que eu já sei.

**Critérios de aceitação**
- **Dado** que escrevo "amanhã vamos de férias uma semana", **então** a casa confirma o que percebeu e durante esse período não avisa que a porta não abriu.
- **Dado** que escrevo "a empregada vem às terças à tarde", **então** a casa deixa de tratar a porta a abrir nesse período como anomalia.
- **Dado** que a casa não percebeu a mensagem, **então** pede para eu a dizer de outra forma, sem assumir nada.

### US02 — Receber uma anomalia e responder

**Como** responsável da casa, **quero** receber no telemóvel uma notificação que explique o que a casa estranhou e me deixe responder, **para** resolver o assunto sem abrir várias páginas.

**Critérios de aceitação**
- **Dado** que a casa detetou uma anomalia, **então** recebo uma notificação com o que aconteceu, o que é habitual e a que classe pertence.
- **Dado** que respondo "está tudo bem", **então** a anomalia fica resolvida e registada.
- **Dado** que explico o motivo ("fiquei em casa doente"), **então** a casa guarda a explicação e não repete o aviso pelo mesmo motivo.

### US03 — Autorizar a casa a agir

**Como** responsável da casa, **quero** que a casa me proponha uma ação e só a execute se eu aceitar, **para** ela nunca fazer nada sem a minha autorização.

**Critérios de aceitação**
- **Dado** que a anomalia tem uma ação possível, **então** a notificação inclui um botão para a aceitar.
- **Dado** que aceito, **então** a casa executa a ação e confirma o resultado.
- **Dado** que recuso ou não respondo, **então** a casa não age.

**Dispositivos:** lâmpada, o único dispositivo que a casa comanda.

### US04 — Escolher um contacto externo

**Como** responsável da casa, **quero** indicar uma pessoa de fora que receba os alertas da minha casa, **para** alguém saber quando eu não respondo.

**Critérios de aceitação**
- **Dado** que indico um contacto, **então** ele passa a receber os alertas desta casa pelo bot de Telegram.
- **Dado** que removo o contacto, **então** ele deixa de receber alertas.
- **Dado** que não indico ninguém, **então** a aplicação funciona normalmente, só com os moradores.

### US05 — Ser avisado como contacto externo

**Como** contacto externo, **quero** receber uma mensagem clara quando a casa de alguém de quem cuido estranha alguma coisa, **para** poder ligar ou ir lá.

**Critérios de aceitação**
- **Dado** que há uma anomalia que me deve chegar, **então** recebo uma mensagem com o que aconteceu, a que horas e o que é habitual.
- **Dado** que a anomalia é de segurança ou de bem-estar e rotina, **quando** o responsável não responde dentro do tempo de espera da casa (cinco minutos por omissão), **então** recebo a mensagem.
- **Dado** que o tempo de espera da casa é zero, **então** recebo a mensagem ao mesmo tempo que o responsável.
- **Dado** que a anomalia é de eficiência energética ou de saúde e conforto, **então** não recebo nada.
- **Dado** que a anomalia fica resolvida pelo responsável, **então** recebo uma segunda mensagem a dizer que está resolvida.

### US06 — Ver o que aconteceu em casa

**Como** responsável da casa, **quero** ver a lista do que os sensores registaram e das anomalias detetadas, **para** perceber porque é que a casa me avisou.

**Critérios de aceitação**
- **Dado** que abro o histórico, **então** vejo os eventos por ordem, do mais recente para o mais antigo.
- **Dado** que abro uma anomalia, **então** vejo a explicação da casa e a resposta que foi dada.

## Histórias de anomalias

### US07 — Porta aberta a uma hora anormal (Segurança)

**Como** responsável da casa, **quero** ser avisado quando a porta da rua abre a uma hora em que nunca abre, **para** saber se entrou ou saiu alguém que não devia.

**Critérios de aceitação**
- **Dado** que no histórico a porta nunca abre entre a meia-noite e as 6h, **quando** abre às 3h10, **então** recebo uma notificação de imediato.
- **Dado** que avisei antes que ia chegar tarde, **então** a casa não avisa.

**Dispositivos:** sensor de porta.

### US08 — Porta esquecida aberta (Segurança)

**Como** responsável da casa, **quero** ser avisado quando a porta da rua fica aberta mais de cinco minutos, **para** a ir fechar.

**Critérios de aceitação**
- **Dado** que a porta abriu, **quando** passam cinco minutos sem fechar, **então** recebo uma notificação.
- **Dado** que a porta fecha antes dos cinco minutos, **então** não recebo nada.

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

**Dispositivos:** sensor de porta, sensor de temperatura.

## Limites conhecidos

- **Um sensor de porta não distingue entrar de sair.** A casa não sabe ao certo se há alguém lá dentro; só sabe que a porta abriu e fechou. Por isso a US11 pergunta em vez de afirmar que a pessoa saiu.
- **As anomalias de rotina precisam de histórico.** Na demo, esse histórico vem do dataset simulado.
- **Fora do MVP:** as anomalias que dependem da câmara, a classe Estado da própria casa, a classe Sono e noite, o fumo e as automatizações.
