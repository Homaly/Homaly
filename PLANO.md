# Plano

Hackathon by Aveiro Tech City, Desafio #3 (Altice Labs): "Connected Home, Reimagined".
Versão de 2026-11-16. Detalhe em `DECISIONS.md` e `USER_STORIES.md`.

## O que vamos construir

Uma casa que repara: aprende o que é habitual e avisa quando algo foge a isso.

## Como funciona

1. A casa lê os sensores e compara o que acontece com o que é habitual.
2. Quando algo foge ao padrão, a IA avalia o contexto, decide se vale a pena avisar e escreve a explicação.
3. O responsável da casa recebe uma notificação no telemóvel e responde. Se aceitar uma ação, a casa executa-a.
4. Se ele não responder em cinco minutos, um contacto externo é avisado por mensagem.

## O que entra no MVP

| Classe | Anomalias | Dispositivos |
|--------|-----------|--------------|
| Segurança | A porta abriu a uma hora em que nunca abre; a porta ficou aberta mais de cinco minutos; veículo desconhecido na entrada de veículos | Porta, câmara |
| Bem-estar e rotina | A casa não vê sinais de vida: nenhuma atividade até à hora habitual, ou a atividade parou com a pessoa em casa | Câmara, lâmpada, tomada, porta |
| Saúde e conforto | Casa abaixo de 16 graus durante horas | Temperatura |
| Eficiência energética | Luz acesa há demasiado tempo; porta aberta com a temperatura a cair; aparelho esquecido ligado na tomada | Lâmpada, porta, temperatura, tomada |

Além das anomalias: conversa por texto com a casa, notificações com resposta, contacto externo e histórico. São catorze user stories no total.

**Fora do MVP:** as restantes anomalias da câmara, detetor de fumo, automatizações, e as classes Estado da própria casa, Sono e noite, e Visitas e cuidadores.

## Quem usa

- **Responsável da casa:** a única pessoa com a aplicação. Pode não viver lá (por exemplo, o filho de uma mãe idosa que vive sozinha).
- **Contacto externo:** opcional. Só recebe anomalias de segurança e de bem-estar e rotina.

## Tecnologia

- **Frontend:** página web para telemóvel, em React, Vite e TypeScript.
- **Backend:** um único serviço em Python, com o agente de IA ligado ao servidor MCP da Altice, e uma base de dados simples.
- **Contacto externo:** SMS com link para uma página com o alerta, enviada pelo textbee a partir de um telemóvel Android da equipa.
- **Dados:** um dataset simulado dá à casa o histórico que não vai existir, e serve para testar a deteção.
- **Dispositivos:** sensor de porta na porta da rua; lâmpada e sensor de temperatura na sala; câmara apontada à entrada de veículos.

## Calendário

| Quando | O que se faz |
|--------|--------------|
| **Antes de segunda** | Ler as user stories; dividir o trabalho pelos cinco; escolher a cena da demo; adiantar o dataset simulado. Não se escreve código até confirmarmos as regras. |
| **Segunda de manhã** | Fazer as perguntas à Altice; ligar ao servidor MCP e ler a porta, a temperatura e a lâmpada; abrir o stream da câmara; montar o esqueleto da aplicação; testar as notificações no telemóvel da demo. |
| **Segunda à tarde** | Primeira anomalia de ponta a ponta: porta aberta mais de cinco minutos, do sensor até à notificação. |
| **Terça** | Restantes seis anomalias, incluindo o veículo desconhecido (câmara); conversa com a casa; contacto externo; histórico. Ensaio e apresentação do MVP ao fim do dia. |
| **Quarta** | Restantes anomalias da câmara e as outras que ficaram de fora; afinar a deteção com o dataset. |
| **Quinta** | Polir, ensaiar o pitch e apresentar. |

A duração de quatro dias e o MVP ao segundo dia estão por confirmar.

## Frentes de trabalho

Uma por pessoa; falta decidir quem fica com qual.

Há uma proposta diferente em `DIVISAO.md`: cada pessoa fica com algumas user stories e faz cada uma de ponta a ponta. Os formatos que passam entre as partes fixam-se na primeira manhã, para ninguém ficar à espera de ninguém.

1. **Dispositivos:** ligação ao servidor MCP da Altice.
2. **Motor de anomalias:** regras de deteção e dataset simulado.
3. **IA:** avaliação do contexto, explicações e conversa com a casa.
4. **Aplicação:** página web e notificações.
5. **Avisos externos e demo:** SMS pelo textbee, página do alerta para o contacto externo, histórico, cena da demo e pitch.

## Perguntas para a Altice na segunda

- O estado da lâmpada consegue ler-se? Muda de cor e de intensidade?
- Os sensores avisam quando algo muda, ou é preciso ir perguntar-lhes?
- O que fornece a câmara: fotografia a pedido, vídeo ou só eventos?
- O servidor MCP expõe mais alguma coisa além destes dispositivos?
- Há créditos para modelos de IA?
- Pode usar-se código escrito antes do evento?

## Riscos

- **Estado da lâmpada:** se não se conseguir ler, a anomalia da luz acesa sai do MVP.
- **Câmara:** o veículo desconhecido depende do stream RTSP e de um modelo de visão que reconheça veículos. Se não funcionar a tempo, sai do MVP.
- **Notificações web:** podem falhar em alguns telemóveis. Testar no primeiro dia.
- **Anomalias de rotina:** dependem do histórico simulado e de um relógio acelerado para se mostrarem ao vivo.
- **Um só sensor de porta:** não distingue entrar de sair, por isso a casa pergunta em vez de afirmar.

## Por decidir pela equipa

- A cena da demo.
- Quem fica com cada frente de trabalho, ou com que user stories (proposta em `DIVISAO.md`).
