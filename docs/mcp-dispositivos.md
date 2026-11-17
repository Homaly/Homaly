# O que o servidor MCP devolve

Leituras feitas a 2026-11-16, por volta das 23:55, com a conta da equipa. Só se usaram ferramentas de leitura; nada foi alterado na casa.

## Ligação

- **Endpoint:** a raiz de `MCP_URL`, por HTTP (streamable HTTP, protocolo `2025-06-18`). O servidor chama-se "Smarthome MCP Server", versão 0.6.0.
- **Autenticação:** o token do Keycloak obtido por `scripts/mcp_headers.sh`, mais os cabeçalhos `X-API-Key` e `X-Client-Type`.
- **User-Agent obrigatório:** o servidor está atrás do Cloudflare, que recusa com erro 403 (código 1010) os pedidos com o User-Agent por omissão das bibliotecas, como `Python-urllib`. O backend tem de enviar um User-Agent próprio, por exemplo `homaly-backend/0.1`.
- **Sem eventos:** o servidor não expõe `resources` (a lista vem vazia), por isso não há subscrições. Os estados lêem-se por polling.

## Ferramentas

São 18, não 16 como no guia. As duas a mais são `get_device_timers` e `post_timer_device`.

| Grupo | Leitura | Escrita |
|-------|---------|---------|
| Casa | `get_home`, `get_home_devices`, `get_home_rooms`, `get_home_status_brief`, `get_home_detail_report` | — |
| Dispositivos | `get_device_details`, `get_device_recommendations`, `get_device_timers` | `update_device_capabilities`, `post_timer_device` |
| Segurança | `get_home_security_status`, `get_home_security_alarm_history` | `patch_home_security_status` |
| Cenários | `get_home_scenarios`, `get_scenario` | `post_new_scenario`, `patch_scenario_activation`, `post_execute_scenario` |

**Atenção:** o servidor marca `patch_home_security_status` como só de leitura, mas a ferramenta muda o estado do alarme.

## Casa

- Nome **"Hack 4"**, id `66dc7efb-154d-4f80-936f-32fd5941e651`.
- Todos os dispositivos estão na divisão "Hack 4", mas `get_home_rooms` devolve uma lista vazia.
- Não há cenários configurados.

## Dispositivos

| Dispositivo | Tipo | id | O que se lê |
|-------------|------|----|-------------|
| Contact sensor | `contactSensor` | `937ac145-dc42-4dcf-9180-ad481ef33c82` | `sensorState` (`normal` / `alarm`), bateria, tamper, sinal |
| Temperature sensor | `temperatureSensor` | `2d1d79da-49cc-4e1a-93ad-5714e514f351` | `temperatureValue` (°C, uma casa decimal), `humidityValue` (%), bateria |
| Light | `bulb` | `59dfc0f6-8813-4768-9877-f993b3e2dec3` | `power` (`on` / `off`), `brightness` (1–100), `color_rgb`, `temperature` (tom do branco, 0–100), `workMode` (`colour`, `music`, `white`, `scene`) |
| Plug | `plug` | `30c07125-1175-47ae-a8be-96b1b20d4539` | `power` (`on` / `off`), potência instantânea, tensão, corrente, consumo de hoje e de ontem |
| Camera | `camera` | `0915a1d0-544e-4427-b35c-46110d21a013` | `motionDetected`, `soundDetected`, sensibilidades, filtro de pessoas (`motionHumanoidFilter`), visão noturna, `streamingSwitch`. Nenhuma imagem |
| Smoke sensor | `smokeSensor` | `a3cc7911-f2cb-4245-8c30-53e30b5a220b` | `sensorState` (`normal` / `alarm`), bateria, tamper |
| Security hub | `gateway` | `2865e9a5-46ef-4c13-a760-2cdf27912680` | `alarmState`, Wi-Fi, rede móvel, bateria |

Cada valor vem dentro de `capabilities`, como `{"type": "temperatureValue", "value": 23.1}`. O código deve procurar pelo `type`, porque o campo `name` vem vazio.

`get_home_devices` devolve todos os dispositivos com as `capabilities` numa só chamada (confirmado a 2026-11-17). Um ciclo de polling é, por isso, um único pedido.

## Hora das leituras

- Cada dispositivo traz `lastCommunicationTime`, em milissegundos desde 1970. É a hora a que o dispositivo comunicou pela última vez, não a hora a que um valor mudou.
- Não há hora por valor. Para saber quando a porta abriu, o backend tem de comparar cada leitura com a anterior.
- **O servidor repete o último valor de um dispositivo que deixou de comunicar.** A 17 de novembro às 03:46, a porta, a temperatura e a tomada não comunicavam desde as 19:16 do dia anterior, e a lâmpada desde 4 de novembro; a porta continuava a aparecer `alarm` (aberta). Por isso o `dispositivos.ler()` deixa de fora os dispositivos que não comunicam há mais de `SENSOR_SILENCIO_MINUTOS` (60 por omissão).
- Nesta leitura, a porta, a temperatura e o detetor de fumo comunicaram pela última vez às 19:16 de 16 de novembro, a câmara às 23:56 e a **lâmpada a 4 de novembro**.

## Segurança

- `get_home_security_status` devolve `{"status": "DISARMED", "isAlarmed": true}`.
- `get_home` mostra mais: o tipo de alarme (`FIRE_SMOKE`), os atrasos de armar e de disparar (30 s em `AWAY`, 0 s em `STAY`) e a hora de entrada.
- O estado `AWAY` existe, por isso a regra da casa vazia (US07) pode ler o alarme. Ainda não se viu o alarme armado.
- O histórico de alarmes só tem dois eventos de 21 de outubro, de uma sirene que não faz parte do nosso kit. Não serve de histórico.

## O que falta confirmar

A equipa deu como verificados a porta (`alarm` = aberta, `normal` = fechada) e a lâmpada (ligada e a comunicar) a 2026-11-17.

- **Temperatura:** de quanto em quanto tempo o sensor comunica. Define o intervalo útil do polling.
- **Câmara:** o que aparece em `motionDetected` quando há movimento, e se o filtro de pessoas o limita a pessoas.
