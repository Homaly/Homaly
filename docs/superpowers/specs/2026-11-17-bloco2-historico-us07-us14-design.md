# Histórico simulado, US07 e US14

Versão de 2026-11-17. Parte de Vila (`DIVISAO.md`), segundo bloco: até à junção de quarta 18, às 12:00.

## Para que serve

As regras precisam de saber o que é habitual numa casa para repararem no que foge a isso. Este trabalho faz o histórico simulado da casa, calcula o habitual a partir dele e escreve as duas primeiras regras reais: a US07 (porta a uma hora anormal) e a US14 (aparelho esquecido ligado). A US09 usa o mesmo habitual no bloco seguinte.

## Decidido com Vila

- **A casa:** uma família que trabalha. Quatro semanas, de 2026-10-19 a 2026-11-15, uma delas de férias (2026-11-02 a 2026-11-08).
  - Nos dias úteis sai entre as 7h30 e as 8h30 e chega entre as 18h00 e as 19h30.
  - Ao fim de semana a primeira abertura é entre as 9h30 e as 11h00, e a última até às 23h00.
  - Nunca abre de madrugada.
- **Férias:** nessa semana, a porta não abre e a tomada não gasta. Não entram no cálculo do habitual.
- **Na tomada:** um desumidificador, ligado no máximo cerca de 1 h de cada vez, algumas vezes por dia.
- **US07:** a hora normal depende do tipo de dia (útil ou fim de semana). Vai da primeira à última abertura do histórico, com 1 h de margem para cada lado.
- **US14:** avisa a partir de 3× o período seguido mais longo do histórico. "A gastar" é `instantPower` acima de 10 W.
- **Casa vazia = férias ditas à casa.** O alarme do kit é só de fumo; não há alarme de intrusão.
- **Com a casa vazia, avisa sempre**, mesmo à hora de uma rotina. O desvio é imediato e de segurança.
- **O nome do aparelho:** fica num campo novo, `Contexto.aparelho_tomada`. Sem ele, a casa diz "o aparelho na tomada".

## Abordagens consideradas

- **Escolhida: o habitual calculado de um histórico gerado com semente fixa.** É reproduzível e mostra o que a casa aprendeu.
- **Posta de parte: um histórico escrito à mão.** São poucas linhas, mas não chega para várias semanas.
- **Posta de parte: o habitual escrito diretamente no código.** Deixava de ser "a casa aprende".

## Como ficou

- `backend/scripts/gerar_historico.py` escreve `backend/dados/historico.csv`. Só leva as mudanças (a porta a abrir e a fechar, a tomada a ligar e a desligar).
- `backend/src/backend/habitual.py` dá as janelas da porta, o período mais longo da tomada e os textos do `habitual`.
- `backend/src/backend/regras/us07.py` e `us14.py` guardam no módulo o que precisam de lembrar de um polling para o outro.
- A US07 só se resolve com a resposta do responsável. A US14 resolve-se sozinha quando o aparelho deixa de gastar.
- Os casos de teste estão em `backend/dados/us07.csv` e `us14.csv`, e os testes em `backend/tests/`.

## Escolhas do construtor

- Cada abertura anormal da porta é uma anomalia nova.
- Uma rotina explica uma abertura no seu dia da semana, até 1 h antes ou depois da sua hora, ou o dia todo se não tiver hora.
- O resumo da US14 diz desde quando o aparelho gasta, para não mudar a cada polling.

## Por fechar com a equipa

- O campo `Contexto.aparelho_tomada` (Simão).
- A unidade de `instantPower`, que ainda não foi confirmada com um aparelho ligado.
- A ação "desligar a tomada" e o texto "deixou de gastar às HH:MM". Por agora, a resolução usa o texto genérico do ciclo.
