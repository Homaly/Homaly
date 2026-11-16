# Desenho do frontend

Versão de 2026-11-16. Base: `USER_STORIES.md` (US01–US13) e `DECISIONS.md`.

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

O detalhe da anomalia (`/anomalias/:id`) abre a partir do Início ou do Histórico. Mostra a explicação, deixa responder, aceitar ou recusar a ação proposta, e mostra a imagem quando a há (US02, US03, US13).

## Estrutura

```
frontend/src/
  types/contract.ts   tipos do contrato com o backend
  api/                cliente HTTP, mocks e WebSocket
  pages/              os 5 ecrãs
  components/         BottomNav, Layout, AnomaliaCard e outros pequenos
  context/            Toast e tema
```

**Dependências:** react, react-router-dom, @tanstack/react-query, tailwindcss v4, clsx, tailwind-merge, date-fns, vite-plugin-pwa. Ícones: Material Symbols (fonte do Google), como no frontend antigo.

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
}

interface Evento {
  id: string
  em: string
  dispositivo: string
  descricao: string
  anomaliaId?: string
}

interface MensagemConversa { id: string; autor: 'pessoa' | 'casa'; texto: string; em: string }

interface Definicoes { contacto: { nome: string; telemovel: string } | null; esperaMinutos: number }
```

| Pedido | Para quê |
|--------|----------|
| `GET /anomalias?estado=ativa` | Início |
| `GET /anomalias/{id}` | Detalhe |
| `POST /anomalias/{id}/resposta` `{texto}` | Responder (US02) |
| `POST /anomalias/{id}/acao` `{aceitar}` | Aceitar ou recusar a ação (US03) |
| `GET /eventos` | Histórico |
| `GET /conversa`, `POST /conversa` `{texto}` | Conversa; o POST devolve a resposta da casa |
| `GET /definicoes`, `PUT /definicoes` | Definições |

**WebSocket `/ws`:** o servidor envia `{tipo: 'anomalia', anomalia}` quando uma anomalia aparece ou muda, e `{tipo: 'evento', evento}` quando há um evento novo. O cliente não envia nada por aqui.

## Estados e erros

- **A carregar:** esqueleto simples.
- **Erro de rede:** mensagem e botão "tentar de novo".
- **Vazio:** "Está tudo normal" no Início; "Ainda não há eventos" no Histórico.
- **WebSocket em baixo:** reconecta sozinho e mostra "sem ligação em tempo real" até voltar.
- **Ação aceite:** o botão fica a carregar até o backend confirmar; se falhar, toast de erro e nada muda. Nunca se mostra a ação como feita sem confirmação.

## Mocks

Com `VITE_USE_MOCKS=true`, a camada `api/` devolve uns poucos dados fixos (algumas anomalias, eventos, mensagens e definições) para os ecrãs terem conteúdo. Sem WebSocket falso: o tempo real só se testa com o backend.

## PWA

`vite-plugin-pwa` com manifesto (nome Homaly, ícone, cores) e service worker básico. Instalável; sem push.

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

## Em aberto

- **Login:** decide-se depois do pitch.
- **Contrato:** confirmar com o colega do backend, que diz já ter os endpoints feitos mas ainda não fez push.
