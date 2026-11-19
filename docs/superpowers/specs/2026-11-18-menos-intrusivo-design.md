# Menos intrusivo: um botão só, e a casa repara no que se repete

Data: 2026-11-18. Origem: reunião com os mentores (ponto 1).

## Porquê

Os mentores acharam a app intrusiva: ao carregar em "Está tudo bem" abre-se sempre uma caixa
"Quer dizer porquê?". Mesmo opcional, parece que a casa pede justificações. A equipa quer
que responder seja um toque e que seja a casa a perceber quando uma coisa passa a ser habitual.

## O que muda para o responsável

- O aviso tem um botão só, "Está tudo bem". Um toque resolve o aviso. Não há caixa de texto.
- Serve para os dois casos: era um falso alarme, ou era a sério e o responsável já tratou.
  A casa não distingue, e o botão não ensina nada à casa.
- Quando a mesma coisa se repete, a casa propõe uma rotina no ecrã do aviso
  (o "Aceitar / Recusar" que já existe):

  ```
  A porta abriu às 10:05 (costuma abrir depois das 11:00)
  [ Está tudo bem ]
  ──────────────
  Obrigado, fica registado.
  A porta tem aberto às terças por volta das 10:00.
  Passo a contar com isso? Quando bater certo, não aviso.
  [ Aceitar ]  [ Recusar ]
  ```

- Aceitar guarda uma rotina igual às que se dizem no chat ("a empregada vem às terças às 10h").

## Abordagens consideradas

1. **A casa olha para os avisos que se repetem e propõe uma rotina (escolhida).** Aproveita as
   rotinas e o ecrã de proposta que já existem. O responsável vê e decide, e na demo vê-se a
   casa a aprender.
2. O habitual (`habitual.py`, hoje fixo, calculado do `historico.csv`) passa a atualizar-se
   com as leituras novas. Foi posta de parte: a casa calava-se sem perguntar, podia aprender
   coisas más (duas aberturas às 3h alargavam o horário), e na demo nada se via.

Também se pôs de parte separar "era falso alarme" de "já tratei" em dois botões: como o botão
não ensina nada e a rotina só entra se for aceite, o risco de aprender um caso real é pequeno.

## Como funciona

- **Quando se verifica:** ao carregar em "Está tudo bem". É o momento em que o responsável está
  a olhar para o aviso, e é onde o ecrã de proposta já aparece.
- **O que conta como "a mesma coisa":** avisos da mesma história (a mesma US, via
  `anomalia_us`), com a hora de deteção a menos de `MARGEM_ROTINA` (1 h) uns dos outros.
  Contam todos os avisos dessa história, resolvidos de qualquer forma; o aviso atual é um deles.
- **"Começa a ser habitual":** três desses avisos
  - no mesmo dia da semana, nas últimas quatro semanas → rotina nesse dia; ou
  - em três dias seguidos → rotina nos dias úteis se forem todos úteis, senão todos os dias.
- **A rotina proposta:** os dias acima, a hora é a mediana das horas dos avisos (arredondada
  a 5 minutos), e a descrição é feita a partir do título do aviso, sem IA (ex.: "a porta abre
  a uma hora pouco habitual"). Fica guardada com `repositorio.guardar_rotina`, pelo `aplicar`
  que já existe.
- **Não propõe:**
  - para a US08 (`AVISA_SEMPRE`: a porta aberta muito tempo avisa sempre);
  - se já houver uma rotina que cubra esses dias e essa hora;
  - outra vez o mesmo padrão (US + dias + hora) depois de o responsável o ter recusado.

## O que sai

- A caixa de texto, "Confirmar sem motivo" e o placeholder "Fiquei em casa doente" em
  `Anomalia.tsx`.
- A chamada à IA em `resposta/responder.py` (classificar `nenhum` / `temporario` /
  `recorrente`). Com um texto fixo não há nada para a IA ler. Os testes de `test_responder.py`
  que testam essa classificação são substituídos pelos do padrão.
- Perde-se o "só por hoje" (`temporario`: silenciar até ao fim do dia). O chat também não o
  faz hoje (só férias, rotinas e aparelho). Fica anotado: se fizer falta, o caminho é o chat
  aprender "hoje tenho visitas".

A API mantém-se: `POST /anomalias/{id}/resposta` continua a receber `texto` (a PWA envia
"Está tudo bem") e `/silencio` continua a aceitar ou recusar a proposta.

## Não-objetivos

- Não muda o habitual nem as regras.
- Não aprende a partir de leituras sem aviso.
- Não muda o chat.

## Fica para quem constrói

- Onde guardar as recusas (uma tabela pequena no repositório do contexto parece suficiente).
- O texto exato da proposta, mantendo o tom das outras frases da casa.
