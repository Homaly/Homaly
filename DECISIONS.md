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
| Eficiência energética | Lâmpada acesa há demasiado tempo; porta aberta com a temperatura a cair | Lâmpada, porta, temperatura |
| Estado da própria casa | Um sensor deixou de comunicar; o gateway ficou sem ligação | Gateway, todos |

- **Entram no MVP quatro classes:** segurança, bem-estar e rotina, saúde e conforto, e eficiência energética.
- **Anomalias do MVP (sete):**

  | Classe | Anomalias no MVP | Dispositivos |
  |--------|------------------|--------------|
  | Segurança | A porta abriu a uma hora em que nunca abre; a porta ficou aberta mais de cinco minutos; veículo desconhecido na entrada de veículos | Porta, câmara |
  | Bem-estar e rotina | A porta não abriu até à hora habitual | Porta |
  | Saúde e conforto | Casa abaixo de 16 graus durante horas | Temperatura |
  | Eficiência energética | Lâmpada acesa há demasiado tempo; porta aberta com a temperatura a cair | Lâmpada, porta, temperatura |

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
- **A casa pergunta antes de alarmar, por notificação no telemóvel**, por exemplo "esta luz está acesa há cinco horas, ainda estão a usar?". A pessoa responde na própria aplicação.
- **A casa age com autorização:** quando a pessoa aceita na notificação, a casa executa a ação, por exemplo apagar a lâmpada.
- **A lâmpada não pisca para avisar.**
- **Conversa por texto na aplicação:** o responsável diz coisas à casa ("amanhã vamos de férias", "a empregada vem às terças") e a casa usa isso para não dar alarmes falsos.
- **De onde vem o "normal":** dos sensores e das conversas com a casa sobre o dia a dia.
- **Um aviso por porta aberta:** se a porta esquecida aberta (US08) já avisou, a porta aberta com a casa a arrefecer (US12) não envia outra notificação; acrescenta a descida de temperatura ao mesmo aviso.
- **Silenciar avisos depois de uma resposta (US02):** "está tudo bem" sem motivo fecha só aquela ocorrência; um motivo temporário silencia esse tipo de anomalia até ao fim do dia; um motivo recorrente passa a fazer parte da rotina até ser removido. A casa diz sempre o que vai ignorar e até quando, e espera confirmação. As anomalias de segurança nunca ficam silenciadas para além da ocorrência atual sem uma regra recorrente explícita.

### Como se constrói

- **Começar do zero.** Não construir em cima do código do semestre passado.
- **Aproveitar** o que for útil desse projeto: fluxos existentes e, possivelmente, o frontend. Origem: `/home/simas/Documents/2º Ano/2º Semestre/IES/ies2526-group-project-ies2526_g403`.
- **Aplicação: página web**, feita para telemóvel.
- **Frontend:** React, Vite e TypeScript.
- **Aviso ao contacto externo:** não tem de ser SMS; basta um meio de aviso. Um bot de Telegram simula o serviço de SMS.
- **Backend:** um único serviço em Python, com o agente de IA ligado ao servidor MCP da Altice, e uma base de dados simples.
- **Quem decide que é anomalia:** regras simples detetam que algo fugiu ao padrão; a IA avalia o contexto (o histórico e o que foi dito na conversa), decide se vale a pena avisar e escreve a explicação.
- **Dataset:** serve de histórico simulado da casa e de conjunto de casos para testar a deteção. Não se treina nenhum modelo de IA de raiz.
- **Modelo de IA:** na segunda-feira pergunta-se à organização se há créditos; se não houver, usa-se o plano gratuito de um fornecedor.
- **Código antes de segunda:** não se escreve código até as regras do hackathon serem confirmadas. Até lá, dividem-se as histórias pelos cinco.

### Onde ficam os dispositivos

- **Sensor de porta:** na porta da rua.
- **Lâmpada e sensor de temperatura:** na mesma divisão, a sala.
- **Câmara:** apontada à entrada de veículos da casa (ver US13).

### Equipa e tempo

- 5 pessoas.
- O desenvolvimento começa na segunda-feira, 16 de novembro de 2026.
- Cerca de 4 dias, com apresentação de MVP no fim do segundo dia (por confirmar).

### Material disponível

Uma unidade de cada:

| Dispositivo | Papel |
|-------------|-------|
| Câmara | Sensor (no MVP, só para o veículo desconhecido) |
| Sensor de temperatura | Sensor |
| Sensor de abertura de porta | Sensor |
| Detetor de fumo | Sensor (posto de parte) |
| Lâmpada | Único dispositivo que a casa consegue comandar |
| Gateway | Liga os dispositivos à rede |

O adaptador entregue com o kit é só um conversor de ficha, não um dispositivo da casa.

## Proposto, ainda não aceite

- **Sem Authentik, RabbitMQ nem InfluxDB.**
- **Histórico na demo:** a casa arranca com o dataset simulado pré-carregado e um relógio acelerado, para mostrar anomalias de rotina ao vivo.
- **Salvaguarda de sensor em silêncio:** se um sensor deixar de enviar dados, a casa não conclui que nada aconteceu.
- **Perfil de quem vive na casa:** o responsável descreve as pessoas por palavras (idade, surdez, demência) e a casa ajusta que anomalias contam mais e como avisa.
- **Formas de anomalia** (atravessam as classes): algo que não aconteceu, e algo que nunca acontece.

## Em aberto

- O papel das ideias 1 e 3: funcionalidades futuras ou abandonadas.
- A cena da demo (a equipa decide mais tarde).
- A divisão das histórias pelos cinco (a equipa decide mais tarde).
- Se as regras do hackathon permitem reaproveitar código escrito antes do evento.
- A duração exata e a data da apresentação do MVP.
- Se o estado da lâmpada se consegue ler, e se muda de cor e de intensidade. O guia do MCP mostra que sim (estado, brilho e cor, lidos e alterados), num exemplo da Altice; falta confirmar com a nossa lâmpada.
- O que a câmara fornece. Nenhuma das 16 ferramentas do guia do MCP devolve imagem; o `.env.example` prevê um stream RTSP fora do MCP. Falta confirmar com a nossa câmara.
- Como a casa reconhece um veículo (US13): pela matrícula ou pelo aspeto (tipo e cor).
