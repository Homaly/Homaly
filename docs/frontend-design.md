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
| Início | `/` | Anomalias ativas em dois grupos: "Urgente" (segurança e bem-estar, as que chegam ao contacto externo), cada uma no seu cartão com o começo da explicação; "Outros avisos" (saúde e conforto, eficiência), em linhas num só cartão. Dentro do grupo, por classe e depois a mais recente primeiro. O título de cada grupo leva o número de avisos ("Urgente (2)"). Sem avisos, "Está tudo normal" | US02 |
| Conversa | `/conversa` | Conversa por texto com a casa; o texto pode ser ditado | US01 |
| Histórico | `/historico` | Eventos e anomalias, do mais recente para o mais antigo, agrupados por dia. Cada dia abre e fecha no cabeçalho ("Hoje (6)"); ao abrir o ecrã, só o "Hoje" está aberto | US06 |
| Definições | `/definicoes` | Contacto externo e tempo de espera, nome da casa, calendário e aparência (tema) | US04 |

O detalhe da anomalia (`/anomalias/:id`) abre a partir do Início ou do Histórico, com a seta de voltar e sem a barra de baixo. A barra de topo fica só com a seta: o título do ecrã é o da anomalia. Mostra a explicação, deixa responder, aceitar ou recusar a ação proposta e a proposta de silêncio, e mostra a imagem quando a há (US02, US03, US13). Os botões ficam presos ao fundo do ecrã, ao alcance do polegar; depois de responder ou de aceitar a ação, passam a "Voltar ao início".

O calendário tem dois ecrãs abaixo das Definições, com a seta de voltar e a barra de baixo: o detalhe (`/definicoes/calendario`), com a conta (e-mail, hora da última leitura, "Atualizar" e, se a leitura falhou, o erro e "Conectar outra vez") e "Remover calendário" num grupo à parte, e a confirmação de remover (`/definicoes/calendario/remover`). Depois de remover, a app volta às Definições sem passar pelo detalhe, que sem calendário já não tem nada.

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

**Página do alerta (US05):** saiu a 2026-11-20. A SMS ao contacto externo basta e não traz link.

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

Por cima da caixa, enquanto ela está vazia, há sugestões para o que a casa percebe: "Vamos de férias", "Vem cá alguém", "Na tomada está…" e "O que aconteceu hoje?". As que acabam em "…" põem o começo da frase na caixa, com o cursor no fim, e a pessoa acaba-a; as outras enviam logo o texto. A casa lê cada mensagem sozinha, sem as anteriores, por isso "Vamos de férias" ou "Vem cá alguém" sem datas nem dias podem receber "Não percebi bem". O espaço das sugestões fica reservado mesmo escondido, para a caixa não saltar ao escrever. As mensagens encostam-se ao fundo, junto à caixa.

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
| `bg-primary/25` | A opção escolhida do `Segmentado` (com letra a negrito, para não depender só da cor) |
| `bg-accent-orange` + `text-on-accent-orange` | Número de avisos por responder, na barra de baixo |

- **Cor de estado:** `text-accent-green` (correu bem), `text-accent-orange` (pede atenção), `text-danger` (erro, perigo ou destrutivo; rosa no escuro), `text-primary-ink` (ligação ou ação). Passam também sobre o fundo claro da mesma cor (`bg-danger/10`, `bg-accent-green/15`).
- **As classes de anomalia não têm cor.** Distinguem-se pelo ícone e pelo nome; a cor fica para o estado. No Início, os ícones dos avisos urgentes ficam a laranja (`bg-accent-orange/15` e `text-accent-orange`, "pede atenção"): a cor diz a urgência, não a classe, por isso segurança e bem-estar têm a mesma.
- **Não usar `text-primary`:** o turquesa tem 1,6:1 sobre fundo claro. O contorno de foco é global; não usar `outline-none`.

## Peças base

- **`Botao`** (`components/Botao.tsx`): pílula com 48 px de altura mínima. Variantes `primario`, `secundario`, `contorno`, `texto`, `perigo`. Um só `primario` por ecrã ou por bloco.
- **`Campo`** (`components/Campo.tsx`): 48 px, cantos de 12 px, letra de 16 px (o iOS não faz zoom). A caixa da conversa é em pílula, como os botões.
- **`Icone`** (`components/Icone.tsx`): Lucide com traço de 1,75, escondido do leitor de ecrã. Quando o ícone é a única informação, juntar texto em `sr-only`. Com `ativo`, mostra a versão cheia: desenhada no mesmo ficheiro sobre os contornos do Lucide (que só tem ícones de traço), para os quatro ícones da barra de baixo; os pormenores (porta, ponteiros, furo) ficam recortados. No Histórico, o anel com a seta fica de traço e só o mostrador do relógio enche, porque encher o anel apagava a seta. Sem versão cheia, o traço passa a 2,25.
- **Cartões:** `rounded-2xl bg-surface-container`, sem contorno. Listas (Histórico, avisos que não são urgentes) num só cartão, com divisórias que não chegam às bordas.
- **Avisos no Início** (`components/AnomaliaCard.tsx`): ícone da classe num círculo à esquerda (laranja nos urgentes, neutro nos outros) e três níveis de texto. Em cima, um cabeçalho pequeno com a classe a negrito e a hora ("**Segurança** · avisou há 9 h"), como o de uma notificação no telemóvel. Depois, o título, forte. Por fim, a explicação, em texto de apoio (só nos urgentes, duas linhas). O cabeçalho vai em cima para não ficar colado à explicação, que também é cinzenta. O "avisou" diz que é a hora do aviso, porque o título pode trazer outro tempo ("Porta da rua aberta há 7 minutos").
- **`Segmentado`** (`components/Segmentado.tsx`): escolha de uma opção entre poucas, lado a lado, com 48 px de altura (tema, tempo de espera). Por dentro são botões de rádio.
- **`Grupo`** (`components/Grupo.tsx`): grupo das Definições, como nas definições do telemóvel: título pequeno, conteúdo num cartão e uma nota por baixo.
- **Alvos de toque:** 48 px no mínimo. A seta de voltar é um círculo de contorno de 40 px dentro de 48 px de toque.
- **Títulos de secção:** `text-xl font-semibold` no Histórico (os dias). Aí, o título é um botão que abre e fecha o dia, com o número de eventos e uma seta que roda. A lista abre a deslizar e, fechada, fica `inert`. No Início e nas Definições, os grupos têm título pequeno (`text-sm font-semibold text-on-surface-variant`), para não competir com o título do ecrã.
- **`Linha`** (`components/Linha.tsx`): linha de lista das definições, com ícone num círculo, título, uma linha de apoio e, à direita, uma seta (`Seta`, abre outro ecrã) ou uma ação curta em `text-primary-ink`. Vai dentro de um `Grupo` com `lista`, que separa as linhas com divisórias. A ação destrutiva fica num grupo só dela, no fim, em `text-danger` e sem seta.
- **Barra de baixo:** o separador ativo tem o ícone cheio e a letra a negrito, na cor do texto principal; os outros ficam de traço, em `text-muted`. O Início mostra o número de avisos por responder.
- **Ações presas ao fundo** (detalhe da anomalia) e caixa da Conversa: avisam os toasts por `useReservarFundo`, que os põe por cima delas em vez de as taparem.
- **Estados vazios:** ícone num círculo, título e uma frase, como na app.
- **Movimento:** ver a secção "Movimento". As animações param com "reduzir movimento".

## Movimento

Segue os padrões do Material 3 e do iOS. As curvas estão em `src/index.css` (`--ease-emphasized`, `--ease-emphasized-decelerate`, `--ease-emphasized-accelerate`). O que entra desacelera (chega depressa e assenta devagar) e o que sai acelera. Os ecrãs demoram 300 ms; os elementos pequenos, entre 150 e 250 ms.

- **Entre separadores da barra de baixo:** "fade through". O ecrã novo aparece e cresce de 96% para 100% (`ecra-separador`).
- **Mais fundo na hierarquia** (cartão → aviso, Definições → Calendário → Remover): o ecrã entra pela direita, 32 px, a aparecer (`ecra-frente`). **Ao subir**, entra pela esquerda (`ecra-tras`). É o "shared axis X" do Material e o push do iOS. Decide-se pela profundidade do caminho e não pelo histórico, por isso "Voltar ao início" também entra pela esquerda (`hooks/useTransicaoDeEcra.ts`).
- Só se anima o ecrã que entra; o que sai desaparece logo. A barra de baixo fica parada.
- **Cada ecrã abre no topo** (`Layout`, com `history.scrollRestoration = 'manual'`). O deslocamento é da janela e passava de um ecrã para o outro: descer na Conversa abria o Histórico no fundo. Ao voltar atrás também se começa no topo.
- **Listas que chegam** (Início, Histórico): os elementos entram em cascata, a subir 8 px, com 40 ms entre cada um (`.cascata`).
- **Barras presas ao fundo** (ações do aviso, caixa da Conversa): vão por portal para o `body` e só aparecem (`animate-aparecer`). Dentro do ecrã animado, o `transform` da animação prendia-as ao ecrã em vez do fundo da janela. Regra: nada com `fixed` dentro do `Layout`.
- **Com "reduzir movimento":** os ecrãs só aparecem, sem deslizar nem crescer, e as listas não fazem cascata.

**Animação de arranque** (`index.html` e `src/lib/arranque.ts`). Mostra a casa do logótipo e a linha do eletrocardiograma, que se desenha da esquerda para a direita. A casa aparece em 300 ms e a linha desenha-se em 650 ms, ao todo cerca de 1 s, como pedem as regras do ecrã de arranque do Android. Está no `index.html` para aparecer antes de o JavaScript carregar. Fica até a app desenhar o primeiro ecrã, mas nunca antes de a linha acabar, e sai a desvanecer em 250 ms. Usa as cores do tema: a casa na cor do texto e a linha no turquesa da marca (`#00e0c6`) nos dois temas. No claro, este turquesa tem pouco contraste (1,6:1), mas aqui é decorativo e é a cor da marca. Com "reduzir movimento", aparece já desenhada e sai logo. Só aparece ao abrir ou recarregar a app, não ao mudar de ecrã. O vídeo do logótipo (`assets/marca/*.mp4`) não se usa: as cores não condizem com a app e dura 7 s.

## Definições e tema

Os dois primeiros grupos (contacto externo, com o tempo de espera, e casa) guardam-se com o botão Guardar; o calendário e a aparência mudam logo. Há um só botão turquesa, o Guardar.

- **Calendário:** uma só linha, como as contas nas definições do telemóvel. Por conectar: "Google Calendar · Não conectado", com "Conectar" à direita, e a linha toda leva à Google. Conectado: o e-mail da conta e uma seta para o detalhe; se a última leitura falhou, a linha di-lo a vermelho. Nos textos do calendário usa-se o verbo conectar (conectar, conectado), não ligar.
- **E-mail anonimizado** (`anonimizarEmail` em `lib/calendario.ts`), na linha, no detalhe e na confirmação de remover: antes do @, os 2 primeiros e os 2 últimos caracteres com asteriscos no meio, sempre com 8 caracteres (`an****va@gmail.com`), para não se saber quão longo é; o que vem depois do @ fica. Nomes de 3 ou 4 caracteres mostram só o primeiro e o último (`a******a@gmail.com`), e de 1 ou 2 só o primeiro, para não ficarem inteiros à vista. O backend continua a devolver o e-mail completo. O detalhe não lista o que a casa sabe pelo calendário; o número de coisas aparece só na confirmação de remover.

- **Tempo de espera:** opções fixas (30 s, 5 min, 15 min, 30 min). Os 30 segundos vão como `esperaMinutos: 0.5`. Um valor guardado fora da lista (o backend aceita de 0, que avisa logo, a 1440) aparece como mais uma opção.
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
| Dias do Histórico recolhíveis, só o "Hoje" aberto | Todos abertos | Com vários dias, a lista ficava longa; o que interessa quase sempre é o dia de hoje |
| Transições: "fade through" entre separadores e eixo X na hierarquia, só no ecrã que entra | View Transitions (React Router `viewTransition`); sem transições | Padrões do Material 3 e do iOS; funciona em qualquer browser e com o `BrowserRouter` atual; a View Transitions API ainda não existe em todos os browsers |
| Animação de arranque em SVG (casa e linha), no `index.html` | O vídeo do logótipo; um ecrã de arranque em React | O vídeo dura 7 s e tem outras cores; no `index.html` aparece antes de o JavaScript carregar, que é quando a app está mesmo a carregar |
| Ícones dos urgentes a laranja e número em cada grupo | Uma cor por classe; número por classe | A cor de "pede atenção" reforça o grupo Urgente sem repetir as cores de estado; com dois ou três avisos, um número por classe era ruído, e o total já está na barra de baixo |
| Início em dois grupos, Urgente e Outros avisos | Lista única só por hora; uma cor por classe | Um alerta de segurança não fica abaixo de uma luz acesa e pesa mais do que ela; a diferença vem do tamanho e do agrupamento, e as classes continuam sem cor |
| Separador ativo com o ícone cheio | Pílula turquesa atrás do ícone; só traço mais grosso | É o padrão do iOS e do Android; a pílula fazia um brilho a competir com o número de avisos |
| Calendário como uma linha de conta, com detalhe à parte | Tudo no ecrã das Definições (conta, lista, Atualizar, Remover) | É o padrão das definições do telemóvel e deixa as Definições curtas; o detalhe só interessa a quem o abre |
| Hora curta nos avisos, com "avisou" ("avisou há 9 h") | `formatDistanceToNow` ("há aproximadamente 9 horas") | É um dado de apoio; a frase longa disputava o lugar ao título. Sem "avisou", confundia-se com o tempo do título |
| Ações do detalhe presas ao fundo | A seguir ao texto | Ficam ao alcance do polegar, mesmo com explicações longas ou com imagem |
| Tempo de espera em opções fixas | Campo numérico | Sem teclado e sem valores inválidos |
| Definições em grupos com título pequeno | Formulário com títulos grandes | Mais curto e mais parecido com as definições do telemóvel |
| Sugestões na Conversa enviam logo, menos as que acabam em "…" | Pôr sempre o começo na caixa; enviar só as frases completas | Pedido da equipa: um toque chega. As que acabam em "…" precisam de ser acabadas pela pessoa |

## Em aberto

- **Login:** decide-se depois do pitch.
- **Contrato:** confirmar com o colega do backend, que diz já ter os endpoints feitos mas ainda não fez push.
