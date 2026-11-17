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
| Início | `/` | Anomalias ativas, ou "Está tudo normal" | US02 |
| Conversa | `/conversa` | Conversa por texto com a casa | US01 |
| Histórico | `/historico` | Eventos e anomalias, do mais recente para o mais antigo | US06 |
| Definições | `/definicoes` | Contacto externo e tempo de espera | US04 |

O detalhe da anomalia (`/anomalias/:id`) abre a partir do Início ou do Histórico, com a seta de voltar e sem a barra de baixo. Mostra a explicação, deixa responder, aceitar ou recusar a ação proposta e a proposta de silêncio, e mostra a imagem quando a há (US02, US03, US13).

## Estrutura

```
frontend/src/
  types/contract.ts   tipos do contrato com o backend
  api/                cliente HTTP, mocks e WebSocket
  pages/              os 5 ecrãs
  components/         BottomNav, Layout, AnomaliaCard; as peças base Botao, Campo e Icone
  context/            Toast e tema
```

**Dependências:** react, react-router-dom, @tanstack/react-query, tailwindcss v4, clsx, tailwind-merge, date-fns, vite-plugin-pwa. Ícones: Material Symbols (fonte do Google), como no frontend antigo. A fonte só traz os ícones listados em `icon_names` no `index.html`; um ícone novo tem de entrar nessa lista, senão aparece o nome em texto.

**Vem do frontend antigo** (`projSmartHome/frontend`): `ToastContext` (sem `motion`), `useTheme`, estilos de `index.css`, o padrão do `useApi`; `Topbar` simplificado (sem pesquisa, alertas nem engrenagem).

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

## Mocks

Com `VITE_USE_MOCKS=true`, a camada `api/` devolve uns poucos dados fixos (algumas anomalias, eventos, mensagens e definições) para os ecrãs terem conteúdo. Sem WebSocket falso: o tempo real só se testa com o backend.

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
| `border-outline-variant` | Contornos de cartões e divisórias |
| `border-field` | Contorno dos campos e do botão de contorno |
| `bg-primary` + `text-on-primary` | Botão principal, mensagem da pessoa na conversa |

- **Cor de estado:** `text-accent-green` (correu bem), `text-accent-orange` (pede atenção), `text-danger` (erro ou perigo), `text-primary-ink` (ligação ou ação). Passam também sobre o fundo claro da mesma cor (`bg-danger/10`, `bg-accent-green/15`).
- **As classes de anomalia não têm cor.** Distinguem-se pelo ícone e pelo nome; a cor fica para o estado.
- **Não usar `text-primary`:** o ciano da marca tem 2:1 sobre fundo claro. O contorno de foco é global; não usar `outline-none`.

## Peças base

- **`Botao`** (`components/Botao.tsx`): 48 px de altura mínima, cantos de 12 px. Variantes `primario`, `secundario`, `contorno`, `texto`, `perigo`. Um só `primario` por ecrã ou por bloco.
- **`Campo`** (`components/Campo.tsx`): 48 px, cantos de 12 px, letra de 16 px (o iOS não faz zoom). A caixa da conversa é redonda de propósito.
- **`Icone`** (`components/Icone.tsx`): escondido do leitor de ecrã. Quando o ícone é a única informação, juntar texto em `sr-only`.
- **Alvos de toque:** 48 px no mínimo. Os botões só de ícone têm a área de toque maior do que o desenho.
- **Títulos de lista** (Início, Histórico): `text-sm font-semibold text-muted`.
- **Movimento:** as animações param com "reduzir movimento".

## PWA

`vite-plugin-pwa` com manifesto (nome Homaly, ícone, cores) e service worker básico. Instalável; sem push. O service worker guarda as fontes do Google, para a app abrir sem rede com letra e ícones. A cor da barra do telemóvel (`theme-color`) acompanha o tema.

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
| Ícones Material Symbols | lucide-react | É o que as peças copiadas do antigo usam |
| Classes de anomalia sem cor | Uma cor por classe | As cores das classes repetiam as de estado: eficiência parecia "correu bem", segurança parecia erro |
| Cores como papéis trocados pelo `.dark` | `dark:` em cada componente | Um só sítio por cor; o tema escuro não se esquece em nenhum componente |

## Em aberto

- **Login:** decide-se depois do pitch.
- **Contrato:** confirmar com o colega do backend, que diz já ter os endpoints feitos mas ainda não fez push.
