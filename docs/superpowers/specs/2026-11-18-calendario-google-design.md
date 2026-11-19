# Calendário: ligar o Google Calendar à casa

Data: 2026-11-18. Origem: reunião com os mentores (ponto 3).

## Porquê

Os mentores sugeriram que a casa aprenda com o calendário da pessoa, logo no início, em vez de
ela ter de dizer tudo no chat. A equipa quer a experiência de "ligar a conta Google" que se vê
noutras apps: um botão, escolher a conta, autorizar. Sem copiar links.

## O que muda para o responsável

Em Definições aparece uma secção "Calendário":

```
Calendário
A casa fica a saber das suas férias e rotinas sem ter de as dizer.
[ Ligar ao Google Calendar ]
```

Depois de autorizar, volta à app com "Calendário ligado" (ou "Não foi possível ligar"):

```
Calendário
Ligado a ana@gmail.com · lido às 15:02
O que a casa sabe pelo calendário
  • Férias no Algarve: de 1 a 8 de dezembro
  • Empregada: terça-feira, às 10:00
  • Dentista: hoje, das 15:00 às 16:00
[ Remover calendário ]
```

"Remover calendário" abre uma página de confirmação: "Vai perder tudo o que a casa sabe pelo
calendário. O que disse na conversa fica." com "Apagar" e "Cancelar". Depois de apagar,
volta às Definições com "Calendário removido".

Os itens entram logo, sem confirmação um a um (decisão do responsável, para não ser intrusivo).

## Abordagens consideradas

1. **Google OAuth, só leitura (escolhida).** Um botão, como noutras apps. Só Google.
2. Colar o link iCal secreto. Funcionava com Google e Apple, mas o responsável não quer colar
   links. Posta de parte.
3. Apple Calendar. Não tem uma ligação deste tipo para outras apps, e uma PWA não lê o
   calendário do iPhone. Quem usa iPhone junta a conta Google ao Calendário do iPhone.

## Como funciona

- **Ligação:** OAuth 2.0 "authorization code" da Google, com `access_type=offline` para ter um
  refresh token. Permissões: `calendar.readonly`, `openid`, `email`. O `state` evita pedidos
  forjados. O email vem do `id_token`.
- **Leitura:** quando liga, de hora a hora, e com "Atualizar" (`POST /calendario/sincronizar`).
  Lê o calendário principal, de ontem a daqui a 90 dias, com os eventos que se repetem como
  um só (com a regra de repetição).
- **O que a IA tira:** recebe a lista de eventos e devolve:
  - **férias e ausências** (dias fora de casa) → períodos, como as férias ditas no chat;
  - **eventos que se repetem** → rotinas (dias da semana e hora);
  - **compromissos** de um dia → ficam no contexto do dia, para a IA explicar avisos.
  Tudo é validado como no chat (`ler_rotina`, `ler_data`). Sem IA, ou com uma resposta que não
  presta, a casa usa o que dá para tirar sem IA: os eventos semanais ou diários como rotinas e
  os eventos com hora como compromissos.
- **Onde fica:** em tabelas próprias (`calendario_ligacao`, `calendario_itens`). Cada leitura
  substitui os itens anteriores (o calendário manda). `carregar_contexto` junta as férias e as
  rotinas do calendário às do chat, e os compromissos de hoje. Remover apaga só o que veio do
  calendário e revoga o acesso na Google.
- **Configuração** (no `.env`, nunca no git): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
  `GOOGLE_REDIRECT_URI` (por omissão `http://localhost:8000/calendario/google/retorno`) e
  `APP_URL`, para onde voltar depois de ligar (por omissão `http://localhost:5173`).

## Não-objetivos

- Outros calendários além do principal; Apple; Outlook.
- Escrever no calendário.
- Rever item a item o que veio do calendário.

## Limitações conhecidas

- Com a app em modo de teste na Google, só as contas de teste ligam, e o acesso acaba ao fim
  de 7 dias. Quando acaba, a secção mostra o erro e pede para ligar outra vez.
- O refresh token fica na base de dados SQLite do servidor, sem cifrar (a app não tem login).
