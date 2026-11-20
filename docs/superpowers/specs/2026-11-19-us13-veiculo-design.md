# US13 — Veículo desconhecido na entrada: design

Data: 2026-11-19. Aprovado em conversa; o plano de implementação vem a seguir.

## Porquê

A US13 é a única história de deteção sem nada no backend (só existe no mock do frontend). O stream RTSP da câmara já foi visto a funcionar (`ffplay`, no PC de um membro da equipa). Não se sabe como vai aparecer o veículo na demo (carro real, fotografia num telemóvel ou carrinho), por isso o reconhecimento tem de funcionar nos três casos.

## Objetivos

- Avisar quando um veículo que a casa não conhece fica na entrada mais de dois minutos, com a imagem, a hora e a descrição (USER_STORIES.md, US13).
- Não avisar por veículos conhecidos.
- Aprender veículos novos: pela resposta ("é o carro do meu irmão") e por uma fotografia do carro.
- Ter um caminho garantido para a demo, sem depender da câmara (fotografia guardada).

## Fora do âmbito

- Treinar um modelo de visão; bibliotecas de OCR; vídeo contínuo.
- Comparar imagem com imagem em cada verificação (ver Abordagens).

## Restrições

- O MCP não dá imagens; a imagem vem do RTSP (`CAMERA_RTSP_URL`).
- `motionDetected` (e `soundDetected`) é sempre `""` no MCP: confirmado a 2026-11-19 com a câmara a comunicar, o alarme armado em `AWAY` e a app da Altice a notificar o movimento no telemóvel. Nenhuma ferramenta do MCP dá eventos ou clips. Os mentores disseram para não nos limitarmos ao MCP.
- O RTSP é um relay `go2rtc` da Altice (porta 8554, H.265 1920×1080). A VM de produção chega-lhe; a rede do local bloqueia a porta (só funcionou no hotspot de um telemóvel).
- O `Modelo` só envia texto. Groq (`gpt-oss`) não aceita imagens; OpenRouter (Haiku 5.5) e Gemini aceitam. Com `IA_FORNECEDOR=falso` a US13 fica desligada.
- Timeout do modelo: 10 s.
- Fotografias com matrículas reais não entram no git.

## Abordagens

**Gatilho:**

- **A. Movimento do MCP** (fica no código): `motionDetected` muda → tira-se uma imagem. Usa o MCP e só chama o modelo quando há movimento. Hoje nunca dispara (o valor é sempre `""`).
- **A2. Detetor de movimento no vídeo** (escolhida como gatilho real): `ffmpeg` com `select='gt(scene,0.1)'` sobre o RTSP, só keyframes. Testado: em 90 s deu 10 imagens, todas com movimento. Leva ao mesmo caminho que A; o modelo só é chamado quando a imagem muda.
- **B. Imagens a intervalos fixos:** rejeitada pela equipa por ineficiente (muitas chamadas ao modelo) e por deixar o MCP de fora.
- **C. Fotografia guardada via `/dev`** (escolhida como plano B da demo e para os testes).

**Reconhecimento:**

- Só aspeto (tipo, cor): funciona com imagem fraca, mas confunde carros parecidos.
- Só matrícula: exata, mas sem matrícula legível não há aviso.
- **As duas** (escolhida): matrícula quando se lê, aspeto quando não. Custa um campo a mais no JSON.

**Registo de conhecidos:**

- **Foto → texto** (escolhida): a fotografia é descrita uma vez pelo modelo e guarda-se o texto. Cada verificação continua a ser uma imagem só.
- Foto ao lado da foto: mais imagens por chamada, mais lento, arrisca o timeout.

## Desenho

1. **Gatilho:** o ciclo dispara quando `motionDetected` muda **ou** quando o detetor de vídeo vê movimento (pausa de 30 s entre disparos). A rota `/dev/us13` aceita uma fotografia e entra no mesmo caminho.
2. **Imagem:** `ffmpeg` tira uma imagem do `CAMERA_RTSP_URL`. Guarda-se em JPEG, é servida por uma rota própria e preenche `imagem_url` da anomalia.
3. **Visão:** uma chamada ao modelo com a imagem e a lista de veículos conhecidos. Devolve `{veiculo, tipo, cor, matricula|null, conhecido_id|null}`.
4. **Dois minutos:** segunda imagem depois de dois minutos (valor a afinar). Se o mesmo veículo desconhecido continua, a regra devolve um `Desvio` US13 com a imagem.
5. **Aprender:** a resposta "é conhecido" e o registo por fotografia guardam o veículo numa tabela `veiculos_conhecidos` (descrição, matrícula). Esse veículo deixa de gerar aviso.
6. **Contexto:** um aviso prévio de visita de carro (US01) suprime o aviso. O contacto externo (US05) segue o caminho normal das outras anomalias.

## Deixado a quem constrói

- Onde corre a captura e a chamada ao modelo sem atrasar o polling do ciclo.
- Como o `Modelo` passa a aceitar uma imagem, sem partir os fornecedores que não a aceitam.
- O esquema da tabela, a rota da imagem e a normalização da matrícula.
- Como a resposta "é conhecido" chega a `veiculos_conhecidos` (ver o módulo `resposta`).
- O limiar do detetor (0.1) e a CPU do `ffmpeg` na VM: afinar e medir com a câmara no sítio final.
