# Fuga de água (US15)

Data: 2026-11-19. Origem: reunião com os mentores (ponto 2).

## Porquê

Os mentores sugeriram mais sensores, mesmo que o kit não os tenha. A equipa escolheu a fuga de
água, para a casa evitar desperdício e estragos: é uma situação em que "a casa que repara" faz
falta, porque uma torneira a pingar ou um autoclismo a correr passam despercebidos durante dias.

## Abordagens consideradas

1. **Contador de água (escolhida).** Mede o caudal à entrada da casa. Apanha a torneira
   esquecida, o fio de água escondido (autoclismo, torneira a pingar, sobretudo de madrugada) e o
   cano rebentado. Encaixa no "evitar desperdício".
2. Sensor de inundação no chão. Só diz "há água" ou "não há": apanha estragos, não o desperdício.

## Como funciona

- **Sensor:** dispositivo `agua`, tipo `caudal`, em litros por minuto. Na demo entra por
  `POST /dev/leituras`; o resto da casa continua real.
- **Regra (`regras/us15.py`):**
  - água a correr (mais de 0,1 L/min) sem parar há uma hora → eficiência. Decide-se uma vez, pelo
    caudal médio: abaixo de 2 L/min é "um fio de água" (autoclismo, torneira a pingar), senão "uma
    torneira pode ter ficado aberta";
  - 12 L/min ou mais durante cinco minutos → segurança e imediato ("pode ser um cano rebentado");
  - com a casa vazia (férias), qualquer água a correr → segurança e imediato;
  - quando a água pára, resolve-se sozinha e diz os litros que correram.
- **Ação (US03):** "Fechar a água". A válvula também é simulada (`dispositivos/simulacao.py`):
  fechá-la põe o caudal a zero, a anomalia resolve-se e o histórico regista "Válvula da água:
  Fechou". Se a pessoa não aceitar, a casa não fecha nada.
- **Limites no `.env`:** `AGUA_MINUTOS`, `AGUA_LIMITE_LMIN`, `FUGA_LMIN`, `CANO_LMIN`,
  `CANO_MINUTOS`. Na demo, `AGUA_MINUTOS=2` mostra o aviso em dois minutos.

## Não-objetivos

- Histórico de consumo de água (o "habitual" é um limite fixo, não aprendido).
- Uma válvula ou contador verdadeiros pelo MCP.
- Ecrãs novos na app: o aviso, a ação e o histórico usam os que já existem.

## Demo

```
POST /dev/leituras {"dispositivo": "agua", "tipo": "caudal", "valor": 0.3}   # fio de água
POST /dev/leituras {"dispositivo": "agua", "tipo": "caudal", "valor": 20}    # cano rebentado
DELETE /dev/leituras                                                         # volta tudo ao normal
```
