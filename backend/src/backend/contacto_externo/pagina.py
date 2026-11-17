"""US05: a página do alerta, `GET /a/{codigo}`, que o contacto externo abre a partir da SMS.

HTML simples servido pelo backend, fora da PWA e sem login. Só de leitura: mostra o alerta e o
estado atual (lido da base de dados a cada pedido), incluindo se já se resolveu e como. Vale 24
horas depois da última SMS sobre o alerta; depois diz só que expirou (410). Um código que não
existe dá 404. Não fica em cache nem aparece em motores de busca.
"""

from datetime import timedelta
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from backend import anomalias, contrato, definicoes
from backend.contrato import Anomalia

from . import envios

VALIDADE = timedelta(hours=24)
RECARREGAR_S = 30

CLASSES = {
    "seguranca": "Segurança",
    "bem_estar": "Bem-estar e rotina",
    "saude_conforto": "Saúde e conforto",
    "eficiencia": "Eficiência energética",
}

CABECALHOS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
    "Referrer-Policy": "no-referrer",
    # Sem scripts nem nada de fora: só o estilo que vem na própria página.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}


def _agora_real():
    """As 24 horas contam em tempo real, mesmo com o relógio da app acelerado: é o contacto a
    abrir o link."""
    return contrato.agora()


agora = _agora_real  # os testes trocam-no

router = APIRouter(tags=["página do alerta"])


@router.get("/a/{codigo}", response_class=HTMLResponse)
def pagina_do_alerta(codigo: str) -> HTMLResponse:
    envio = envios.por_codigo(codigo)
    anomalia = anomalias.obter(envio.anomalia_id) if envio else None
    if envio is None or envio.ultima_sms_em is None or anomalia is None:
        return _resposta(404, _aviso("Este link não existe", "Confirme que abriu o link completo da SMS."))
    if agora() > envio.ultima_sms_em + VALIDADE:
        return _resposta(
            410, _aviso("Este alerta expirou", "Os alertas ficam disponíveis 24 horas depois da SMS.")
        )
    return _resposta(200, _alerta(anomalia, definicoes.obter().nome_casa), recarregar=anomalia.estado == "ativa")


def _resposta(estado: int, corpo: str, recarregar: bool = False) -> HTMLResponse:
    return HTMLResponse(_documento(corpo, recarregar), status_code=estado, headers=CABECALHOS)


def _hora(momento) -> str:
    return f"{momento.astimezone():%H:%M}"


def _alerta(anomalia: Anomalia, nome_casa: str | None) -> str:
    quando = anomalia.detetada_em.astimezone()
    if anomalia.estado == "resolvida":
        texto = anomalia.resolucao.texto if anomalia.resolucao else "o responsável tratou do assunto"
        hora = _hora(anomalia.resolucao.em) if anomalia.resolucao else ""
        estado = (
            f'<div class="estado resolvido"><strong>Resolvido{f" às {hora}" if hora else ""}</strong>'
            f"<p>{escape(texto)}</p></div>"
        )
    else:
        estado = (
            '<div class="estado ativo"><strong>Ainda por resolver</strong>'
            "<p>Esta página atualiza-se sozinha.</p></div>"
        )
    casa = f'<p class="casa">{escape(nome_casa)}</p>' if nome_casa else ""
    return f"""
      <p class="marca">Homaly</p>
      {casa}
      <p class="classe">{escape(CLASSES.get(anomalia.classe, anomalia.classe))}</p>
      <h1>{escape(anomalia.titulo)}</h1>
      <p class="quando">Detetado às {quando:%H:%M} de {quando:%d/%m}</p>
      <p>{escape(anomalia.explicacao)}</p>
      {estado}
      <p class="rodape">Página só de leitura, enviada pelo Homaly ao contacto externo desta casa.</p>
    """


def _aviso(titulo: str, texto: str) -> str:
    return f'<p class="marca">Homaly</p><h1>{escape(titulo)}</h1><p>{escape(texto)}</p>'


def _documento(corpo: str, recarregar: bool) -> str:
    refresh = f'<meta http-equiv="refresh" content="{RECARREGAR_S}">' if recarregar else ""
    return f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  {refresh}
  <title>Homaly — alerta</title>
  <style>
    :root {{ --fundo: #f6f7f9; --cartao: #fff; --texto: #1b1f24; --apoio: #4b5563; --ativo: #b42318;
             --ativo-fundo: #fef3f2; --ok: #067647; --ok-fundo: #ecfdf3; --linha: #d0d5dd; }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --fundo: #0f1115; --cartao: #1a1d23; --texto: #f2f4f7; --apoio: #b8c0cc; --ativo: #fda29b;
               --ativo-fundo: #2a1513; --ok: #75e0a7; --ok-fundo: #10231a; --linha: #344054; }}
    }}
    body {{ margin: 0; background: var(--fundo); color: var(--texto);
           font: 17px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
    main {{ max-width: 34rem; margin: 0 auto; padding: 1.5rem 1rem 2rem; }}
    .cartao {{ background: var(--cartao); border: 1px solid var(--linha); border-radius: 1rem; padding: 1.25rem; }}
    .marca {{ margin: 0; font-weight: 700; letter-spacing: .02em; }}
    .casa, .quando, .rodape {{ color: var(--apoio); margin: .25rem 0; }}
    .classe {{ display: inline-block; margin: .75rem 0 0; padding: .1rem .6rem; border-radius: 999px;
              border: 1px solid var(--linha); font-size: .9rem; }}
    h1 {{ font-size: 1.4rem; line-height: 1.3; margin: .5rem 0 .25rem; }}
    .estado {{ border-radius: .75rem; padding: .75rem 1rem; margin: 1rem 0; }}
    .estado p {{ margin: .25rem 0 0; }}
    .ativo {{ background: var(--ativo-fundo); color: var(--ativo); }}
    .resolvido {{ background: var(--ok-fundo); color: var(--ok); }}
    .rodape {{ font-size: .85rem; margin-top: 1.25rem; }}
  </style>
</head>
<body><main><div class="cartao">{corpo}</div></main></body>
</html>"""
