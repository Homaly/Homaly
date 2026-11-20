# Desenho do frontend

Versão de 2026-11-16. Base: `USER_STORIES.md` (US01–US14) e `DECISIONS.md`.

## Resumo

- **O quê:** o frontend do Homaly, uma PWA para telemóvel em React, Vite, TypeScript e Tailwind. Projeto Vite novo, que traz do frontend do semestre passado só as peças escolhidas.
- **Para quem:** o responsável da casa, a única pessoa com a aplicação.
- **Âmbito:** só o que as user stories descrevem, mais um ecrã inicial com as anomalias ativas.
- **Fora:** gerir dispositivos e divisões, agendamentos, energia, perfis, permissões, automações, login, e notificações push com a app fechada.

## Ecrãs e navegação

Barra em baixo com quatro separadores:

| Separador | Rota | Ecrã | História |
|-----------|------|------|----------|
| Início | `/` | Anomalias ativas, das mais urgentes para as menos (segurança, bem-estar, saúde e conforto, eficiência; dentro da classe, a mais recente primeiro), ou "Está tudo normal" | US02 |
| Conversa | `/conversa` | Conversa por texto com a casa; o texto pode ser ditado | US01 |
| Histórico | `/historico` | Eventos e anomalias, do mais recente para o mais antigo | US06 |
| Definições | `/definicoes` | Contacto externo e tempo de espera, nome da casa, calendário e aparência (tema) | US04 |

O detalhe da anomalia (`/anomalias/:id`) abre a partir do Início ou do Histórico, com a seta de voltar e sem a barra de baixo. A barra de topo fica só com a seta: o título do ecrã é o da anomalia. Mostra a explicação, deixa responder, aceitar ou recusar a ação proposta e a proposta de silêncio, e mostra a imagem quando a há (US02, US03, US13). Os botões ficam presos ao fundo do ecrã, ao alcance do polegar; depois de responder ou de aceitar a ação, passam a "Voltar ao início".

O separador do Início mostra na barra de baixo quantos avisos estão por responder, para se ver a partir de qualquer separador.

## Estrutura

```
frontend/src/
  types/contract.ts   tipos do contrato com o backend
  api/                cliente HTTP, mocks e WebSocket
  pages/              os 5 ecrãs
  components/         BottomNav, Layout, AnomaliaCard; as peças base Botao, Campo, Icone, Segmentado e Grupo
  context/            Toast e tema (ThemeContext)
```

**Dependências:** react, react-router-dom, @tanstack/react-query, tailwindcss v4, clsx, tailwind-merge, date-fns, vite-plugin-pwa. Mais lucide-react para os ícones; um ícone novo entra no mapa de `components/Icone.tsx`. Letra: Montserrat (fonte do Google).

**Vem do frontend antigo** (`projSmartHome/frontend`): `ToastContext` (sem `motion`), `useTheme` (agora um contexto, `context/ThemeContext.tsx`), estilos de `index.css`, o padrão do `useApi`; `Topbar` simplificado (sem pesquisa, alertas, engrenagem nem botão de tema).

## Contrato com o backend

O frontend define os tipos; o backend segue-os ou propõe correções.

```ts
type Classe = 'seguranca' | 'bem_estar' | 'saude_conforto' | 'eficiencia'

interface Anomalia {
  id: string
  classe: Classe
  titulo: string
  explicacao: string        // texto da IA: o que aconteceu e o que é habitual
  detetadaEm: string        // ISO 8601
  estado: 'ativa' | 'resolvida'
  acaoProposta?: { descricao: string }
  imagemUrl?: string
  resposta?: { texto: string; em: string }
  propostaSilencio?: PropostaSilencio  // US02: só se aplica depois de aceite
  resolucao?: { texto: string; em: string } // ex.: "a porta fechou às 14:12"
}

interface PropostaSilencio {
  texto: string             // "Não volto a avisar sobre a porta até ao fim do dia."
  ate: string               // ISO 8601
  estado: 'pendente' | 'aceite' | 'recusada'
}

interface Evento {
  id: string
  em: string
  dispositivo: string
  descricao: string
  anomaliaId?: string
}

interface MensagemConversa { id: string; autor: 'pessoa' | 'casa'; texto: string; em: string }

interface Definicoes { contacto: { nome: string; telemovel: string } | null; esperaMinutos: number; nomeCasa?: string }
```

| Pedido | Para quê |
|--------|----------|
| `GET /anomalias?estado=ativa` | Início |
| `GET /anomalias/{id}` | Detalhe |
| `POST /anomalias/{id}/resposta` `{texto}` | Responder (US02) |
| `POST /anomalias/{id}/acao` `{aceitar}` | Aceitar ou recusar a ação (US03) |
| `POST /anomalias/{id}/silencio` `{aceitar}` | Aceitar ou recusar a proposta de silêncio (US02); devolve a `Anomalia` atualizada |
| `GET /eventos` | Histórico |
| `GET /conversa`, `POST /conversa` `{texto}` | Conversa; o POST devolve a resposta da casa |
| `GET /definicoes`, `PUT /definicoes` | Definições |

**Proposta de silêncio (US02):** quando o responsável explica um alerta (`POST /anomalias/{id}/resposta`), a resposta pode trazer `propostaSilencio` com `estado: 'pendente'`. O ecrã de detalhe mostra o texto com os botões Sim e Não, que chamam `POST /anomalias/{id}/silencio`. O backend só deixa de avisar depois de `aceitar: true`.

**Página do alerta (US05):** não faz parte da PWA. É o backend que a serve, em `GET /a/{codigo}`, como uma página HTML simples, sem login, para o contacto externo abrir a partir da SMS. O `codigo` é aleatório e longo (por exemplo, `secrets.token_urlsafe(16)` em Python), criado quando a SMS é enviada e associado ao alerta; nunca é o id da anomalia. A página mostra o alerta e o estado atual, incluindo se já está resolvido e como. Funciona 24 horas depois do envio; depois mostra só que o alerta expirou.

**WebSocket `/ws`:** o servidor envia `{tipo: 'anomalia', anomalia}` quando uma anomalia aparece ou muda, e `{tipo: 'evento', evento}` quando há um evento novo. O cliente não envia nada por aqui.

## Estados e erros

- **A carregar:** esqueleto simples.
- **Erro de rede:** mensagem e botão "tentar de novo".
- **Vazio:** "Está tudo normal" no Início; "Ainda não há eventos" no Histórico.
- **WebSocket em baixo:** reconecta sozinho e mostra "sem ligação em tempo real" até voltar.
- **Ação aceite:** o botão fica a carregar até o backend confirmar; se falhar, toast de erro e nada muda. Nunca se mostra a ação como feita sem confirmação.

## Ditado na Conversa

O botão do microfone, dentro da caixa da Conversa, passa a voz a texto com a Web Speech API do browser, em português de Portugal (`hooks/useDitado.ts`). Ditar substitui o que estava na caixa: o que é ouvido vai aparecendo enquanto a pessoa fala; se o ditado falhar sem ouvir nada, o texto anterior volta. Para sozinho quando a pessoa se cala, e não envia: a pessoa revê e carrega em enviar. Tocar outra vez no microfone para; enviar a meio deita fora o que ainda não chegou.

- **Onde funciona:** Chrome (Android e computador) e Edge; no Safari do iPhone está por testar. No Firefox, e fora de HTTPS ou de `localhost`, o botão não aparece. No telemóvel, testar pela ligação USB (`localhost`), como na instalação.
- **Privacidade:** no Chrome, o áudio vai para os servidores da Google para ser transcrito; no Safari, para os da Apple. Não passa pelo backend.
- **Erros:** sem autorização do microfone, sem som, sem rede ou sem microfone: toast com o que fazer.

## Sugestões na Conversa

Por cima da caixa, enquanto ela está vazia, há começos de frase para o que a casa percebe: "Vamos de férias", "Vem cá alguém", "Na tomada está…" e "O que aconteceu hoje?". Tocar põe o começo na caixa, com o cursor no fim, e a pessoa acaba a frase; nada é enviado sozinho, como no ditado. O espaço das sugestões fica reservado mesmo escondido, para a caixa não saltar ao escrever. As mensagens encostam-se ao fundo, junto à caixa.

## Mocks

Com `VITE_USE_MOCKS=true`, a camada `api/` devolve uns poucos dados fixos (algumas anomalias, eventos, mensagens e definições) para os ecrãs terem conteúdo. Sem WebSocket falso: o tempo real só se testa com o backend.

## Identidade visual

Segue a app Connected Home da Altice, para a Homaly parecer da mesma família: fundo azul-noite (`#131321`), cartões num tom um pouco mais claro e sem contorno, cantos de 16 px, botões em pílula turquesa (`#00e0c6`) com texto escuro, rosa para o que é destrutivo, letra Montserrat e ícones de traço fino (Lucide). Os títulos são grandes e a negrito; os separadores do ecrã têm título grande na barra de topo; no detalhe da anomalia, a barra fica só com a seta e o título é o da anomalia. As cores do tema escuro foram medidas nas capturas da app; o tema claro deriva delas. Não se usa o logótipo nem o nome da Altice.

## Cores e contraste

As cores estão em `src/index.css`, como papéis. Os componentes usam os papéis, nunca `slate-*`, `bg-white` nem `dark:`: o `.dark` troca os valores dos papéis. Texto e ícones passam WCAG 2.2 AA nos dois temas: 4,5:1 no texto, 3:1 nos ícones, nos contornos dos campos e no foco.

| Papel | Para quê |
|-------|----------|
| `bg-surface` | Fundo do ecrã |
| `bg-surface-container` | Cartões, campos, barra de baixo, toasts |
| `bg-surface-tonal` | Botões secundários, chips das classes, esqueletos |
| `text-on-surface` | Texto principal (é o do `body`) |
| `text-on-surface-variant` | Texto de apoio: descrições, explicações curtas |
| `text-muted` | Metadados: horas, ajudas, separadores inativos |
| `border-outline-variant` | Divisórias dentro dos cartões (os cartões não têm contorno) |
| `border-field` | Contorno dos campos e do botão de contorno |
| `bg-primary` + `text-on-primary` | Botão principal, mensagem da pessoa na conversa |
| `bg-primary/25` | O que está escolhido: pílula do separador ativo, opção do `Segmentado` (com letra a negrito, para não depender só da cor) |
| `bg-accent-orange` + `text-on-accent-orange` | Número de avisos por responder, na barra de baixo |

- **Cor de estado:** `text-accent-green` (correu bem), `text-accent-orange` (pede atenção), `text-danger` (erro, perigo ou destrutivo; rosa no escuro), `text-primary-ink` (ligação ou ação). Passam também sobre o fundo claro da mesma cor (`bg-danger/10`, `bg-accent-green/15`).
- **As classes de anomalia não têm cor.** Distinguem-se pelo ícone e pelo nome; a cor fica para o estado.
- **Não usar `text-primary`:** o turquesa tem 1,6:1 sobre fundo claro. O contorno de foco é global; não usar `outline-none`.

## Peças base

- **`Botao`** (`components/Botao.tsx`): pílula com 48 px de altura mínima. Variantes `primario`, `secundario`, `contorno`, `texto`, `perigo`. Um só `primario` por ecrã ou por bloco.
- **`Campo`** (`components/Campo.tsx`): 48 px, cantos de 12 px, letra de 16 px (o iOS não faz zoom). A caixa da conversa é em pílula, como os botões.
- **`Icone`** (`components/Icone.tsx`): Lucide com traço de 1,75 (2,25 no separador ativo), escondido do leitor de ecrã. Quando o ícone é a única informação, juntar texto em `sr-only`.
- **Cartões:** `rounded-2xl bg-surface-container`, sem contorno. Listas (Histórico) num só cartão, com divisórias que não chegam às bordas.
- **`Segmentado`** (`components/Segmentado.tsx`): escolha de uma opção entre poucas, lado a lado, com 48 px de altura (tema, tempo de espera). Por dentro são botões de rádio.
- **`Grupo`** (`components/Grupo.tsx`): grupo das Definições, como nas definições do telemóvel: título pequeno, conteúdo num cartão e uma nota por baixo.
- **Alvos de toque:** 48 px no mínimo. A seta de voltar é um círculo de contorno de 40 px dentro de 48 px de toque.
- **Títulos de secção** (Início, Histórico): `text-xl font-semibold`. Nas Definições, os grupos têm título pequeno (`Grupo`).
- **Barra de baixo:** o separador ativo tem uma pílula `bg-primary/25` atrás do ícone, letra a negrito e traço mais grosso; o Início mostra o número de avisos por responder.
- **Ações presas ao fundo** (detalhe da anomalia) e caixa da Conversa: avisam os toasts por `useReservarFundo`, que os põe por cima delas em vez de as taparem.
- **Estados vazios:** ícone num círculo, título e uma frase, como na app.
- **Movimento:** as animações param com "reduzir movimento".

## Definições e tema

Os dois primeiros grupos (contacto externo, com o tempo de espera, e casa) guardam-se com o botão Guardar; o calendário e a aparência mudam logo. Há um só botão turquesa, o Guardar; o "Ligar ao Google Calendar" é de contorno.

- **Tempo de espera:** opções fixas (Logo, 5 min, 15 min, 30 min). Um valor guardado fora da lista (o backend aceita até 1440) aparece como mais uma opção.
- **Aparência:** Automático, Claro ou Escuro. Automático segue o tema do telemóvel, mesmo com a app aberta, e é o valor por omissão. A escolha fica no telemóvel (`localStorage`, chave `homaly-theme`), não vai para o backend. Não há botão de tema na barra de topo.

## PWA

`vite-plugin-pwa` com manifesto (nome Homaly, ícone, cores) e service worker básico. Instalável; sem push. O service worker guarda a letra do Google, para a app abrir sem rede com a mesma letra; os ícones vêm no código. A cor da barra do telemóvel (`theme-color`) acompanha o tema.

### Instalar e testar

O servidor de desenvolvimento (`npm run dev`, porta 5173) não tem manifesto nem service worker: mostra os ecrãs, mas não deixa instalar. Para testar a PWA, gerar a build e servi-la, a partir da raiz do repo:

```bash
docker compose run --rm -p 4173:4173 frontend sh -c "npx vite build --mode development && npx vite preview --host 0.0.0.0"
```

O `--mode development` faz a build ler `frontend/.env.development` e `frontend/.env.development.local`. Sem ele não há ficheiro de ambiente para produção: os mocks ficam desligados, a API fica sem endereço e os pedidos vão para o próprio servidor da build, que não responde.

- **Dados:** por omissão, a build usa os mocks. Para usar o backend real, pôr `VITE_USE_MOCKS=false` em `frontend/.env.development.local` e ter o backend a correr na porta 8000.
- **Instalar no computador:** abrir http://localhost:4173 no Chrome, no Edge ou no Chromium e carregar no ícone de instalar, à direita na barra de endereço (ou menu ⋮ → *Transmitir, guardar e partilhar* → *Instalar página como app…*). O Firefox não instala PWAs no Linux.
- **Instalar no telemóvel (Android):** o Chrome só instala a partir de HTTPS ou de `localhost`; pelo IP da rede, a página abre mas não deixa instalar. Ligar o telemóvel por USB, com a depuração USB ativa; no Chrome do computador, em `chrome://inspect` → *Port forwarding*, reencaminhar `4173` e `8000` (a app chama a API em `localhost:8000`); no telemóvel, abrir `http://localhost:4173` e escolher ⋮ → *Instalar app*.
- **Verificar:** F12 → *Application*. Em *Manifest* aparece "Homaly" com os ícones; em *Service workers*, o `sw.js` está ativo. Com *Offline* ligado no separador *Network*, a app deve voltar a abrir ao recarregar, sem dados novos.
- **Aparece a versão antiga:** o service worker serve a cópia que guardou; a nova entra depois de recarregar uma ou duas vezes. Se não entrar, F12 → *Application* → *Storage* → *Clear site data*. Uma app já instalada atualiza-se da mesma forma ao abrir.
- **Depois de um pull com dependências novas:** `docker compose up -d --build -V`. Sem o `-V`, os contentores ficam com o `node_modules` e o `.venv` antigos, e a build falha com "failed to resolve import" (ou o backend com `ModuleNotFoundError`).

## Verificação

`tsc` e `vite build` sem erros. Cada ecrã aberto no browser em modo telemóvel, com mocks e, quando houver, com o backend. Sem testes automáticos.

## Registo de decisões

| Decisão | Alternativas | Porquê |
|---------|--------------|--------|
| Projeto Vite novo, com peças copiadas do antigo | Copiar tudo e apagar | Sem código morto nem dependências inúteis |
| Ecrã inicial com as anomalias ativas | Resumo da casa; abrir na conversa | Pedido da equipa; fica dentro das user stories |
| Barra de navegação em baixo | Menu lateral | É uma app de telemóvel |
| Sem login | Login com Keycloak/OIDC | Pouco tempo; decide-se depois do pitch (18/11) |
| Tempo real por WebSocket | Polling; STOMP | Escolha da equipa |
| Push com a app fechada fora deste trabalho | Fazer já | Precisa de HTTPS, VAPID no backend e testes em telemóvel; é uma frente à parte |
| Frontend define o contrato | Esperar pelo backend | Não ficar à espera um do outro |
| Mocks só com dados fixos | Mocks completos com WebSocket falso; sem mocks | Chega para popular os ecrãs |
| Sem testes automáticos | Testes com Vitest | Tempo do hackathon |
| Ícones Lucide (lucide-react) | Material Symbols, como no frontend antigo | São os da app Connected Home; vêm no código, sem fonte para carregar |
| Identidade da app Connected Home | Identidade própria | A Homaly vive ao lado da app da Altice; parecer da mesma família ajuda no pitch |
| Ditado pela Web Speech API do browser | Gravar o áudio e transcrevê-lo no backend (ex.: Whisper) | Sem backend nem chave nova; chega para a demonstração. O áudio vai para a Google ou a Apple, não para o servidor da equipa |
| O ditado não envia sozinho | Enviar quando a pessoa se cala | A transcrição pode vir errada; a pessoa revê antes, como a casa pergunta antes de agir |
| Classes de anomalia sem cor | Uma cor por classe | As cores das classes repetiam as de estado: eficiência parecia "correu bem", segurança parecia erro |
| Cores como papéis trocados pelo `.dark` | `dark:` em cada componente | Um só sítio por cor; o tema escuro não se esquece em nenhum componente |
| Tema em Definições → Aparência, com Automático | Botão na barra de topo de todos os ecrãs | Muda-se uma vez; o botão ocupava o lugar de mais destaque e, depois de um toque, a app deixava de seguir o telemóvel sem forma de voltar |
| Início ordenado por urgência | Só por hora | Um alerta de segurança não fica abaixo de uma luz acesa; as classes continuam sem cor |
| Ações do detalhe presas ao fundo | A seguir ao texto | Ficam ao alcance do polegar, mesmo com explicações longas ou com imagem |
| Tempo de espera em opções fixas | Campo numérico | Sem teclado e sem valores inválidos |
| Definições em grupos com título pequeno | Formulário com títulos grandes | Mais curto e mais parecido com as definições do telemóvel |
| Sugestões na Conversa põem o começo da frase na caixa | Enviar logo | A pessoa acaba e revê a frase, como no ditado |

## Em aberto

- **Login:** decide-se depois do pitch.
- **Contrato:** confirmar com o colega do backend, que diz já ter os endpoints feitos mas ainda não fez push.
