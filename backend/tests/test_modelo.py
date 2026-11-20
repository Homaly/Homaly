import json

import httpx
import pytest

from backend.ia.modelo import ModeloOpenAI, obter_modelo


def test_obter_modelo_por_omissao_e_falso(monkeypatch):
    monkeypatch.delenv("IA_FORNECEDOR", raising=False)
    assert obter_modelo().completar_json("s", "m") is None


def test_obter_modelo_desconhecido_falha(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "xpto")
    with pytest.raises(ValueError):
        obter_modelo()


def test_modelo_fixo_importa_de_conftest_e_regista_chamadas():
    from tests.conftest import AGORA, LX, ModeloFixo

    m = ModeloFixo({"a": 1})
    assert m.completar_json("s", "m") == {"a": 1}
    assert m.chamadas == [("s", "m")]
    assert AGORA.tzinfo is LX and AGORA.weekday() == 1


def _cliente(resposta) -> tuple[httpx.Client, list[httpx.Request]]:
    """Um cliente httpx que não sai para a rede: `resposta(pedido)` dá a resposta."""
    pedidos: list[httpx.Request] = []

    def tratar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return resposta(pedido)

    return httpx.Client(transport=httpx.MockTransport(tratar)), pedidos


def _com_conteudo(conteudo: str):
    return lambda _: httpx.Response(200, json={"choices": [{"message": {"content": conteudo}}]})


def test_groq_por_omissao(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "chave-groq")
    monkeypatch.delenv("IA_MODELO", raising=False)
    m = obter_modelo()
    assert isinstance(m, ModeloOpenAI)
    assert m.url == "https://api.groq.com/openai/v1/chat/completions"
    assert m.modelo == "openai/gpt-oss-120b"


def test_gemini_com_modelo_do_ambiente(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini")
    monkeypatch.setenv("IA_MODELO", "gemini-outro")
    m = obter_modelo()
    assert m.url.startswith("https://generativelanguage.googleapis.com/")
    assert m.modelo == "gemini-outro"


def test_openrouter_por_omissao(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-or")
    monkeypatch.delenv("IA_MODELO", raising=False)
    m = obter_modelo()
    assert m.url == "https://openrouter.ai/api/v1/chat/completions"
    assert m.modelo == "anthropic/claude-haiku-5.5"


def test_fornecedor_sem_chave_falha(monkeypatch):
    monkeypatch.setenv("IA_FORNECEDOR", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        obter_modelo()


def test_pedido_e_resposta():
    cliente, pedidos = _cliente(_com_conteudo('{"avisar": true}'))
    m = ModeloOpenAI("https://exemplo/v1/chat/completions", "segredo", "m1", cliente=cliente)

    assert m.completar_json("o sistema", "a mensagem") == {"avisar": True}

    (pedido,) = pedidos
    assert pedido.headers["Authorization"] == "Bearer segredo"
    assert pedido.headers["User-Agent"] == "homaly-backend/0.1"
    corpo = json.loads(pedido.content)
    assert corpo["model"] == "m1"
    assert corpo["response_format"] == {"type": "json_object"}
    assert corpo["messages"] == [
        {"role": "system", "content": "o sistema"},
        {"role": "user", "content": "a mensagem"},
    ]


def test_historico_vai_entre_o_sistema_e_a_mensagem():
    cliente, pedidos = _cliente(_com_conteudo('{"tipo": "resposta"}'))
    m = ModeloOpenAI("https://exemplo/v1/chat/completions", "segredo", "m1", cliente=cliente)
    historico = [
        {"role": "user", "content": "chama-te Jarvis"},
        {"role": "assistant", "content": "Combinado."},
    ]

    m.completar_json("o sistema", "como te chamas?", historico)

    assert json.loads(pedidos[0].content)["messages"] == [
        {"role": "system", "content": "o sistema"},
        *historico,
        {"role": "user", "content": "como te chamas?"},
    ]


@pytest.mark.parametrize(
    "resposta",
    [
        lambda _: httpx.Response(429, json={"error": "limite"}),
        lambda _: httpx.Response(503, json={"error": "ocupado"}),
        _com_conteudo("isto não é JSON"),
        _com_conteudo("[1, 2]"),
        lambda _: httpx.Response(200, json={"choices": []}),
    ],
    ids=["429", "503", "nao-json", "nao-objeto", "sem-escolhas"],
)
def test_falhas_dao_none(resposta):
    cliente, _ = _cliente(resposta)
    m = ModeloOpenAI("https://exemplo", "k", "m", cliente=cliente)
    assert m.completar_json("s", "m") is None


def test_timeout_da_none():
    def rebenta(pedido):
        raise httpx.ReadTimeout("demorou", request=pedido)

    cliente, _ = _cliente(rebenta)
    m = ModeloOpenAI("https://exemplo", "k", "m", cliente=cliente)
    assert m.completar_json("s", "m") is None


def test_com_imagem_envia_a_imagem_em_base64():
    cliente, pedidos = _cliente(_com_conteudo('{"veiculo": true}'))
    m = ModeloOpenAI("https://exemplo/v1/chat/completions", "segredo", "m1", cliente=cliente)

    assert m.completar_json_com_imagem("o sistema", "o que vês?", b"\xff\xd8jpeg") == {"veiculo": True}

    corpo = json.loads(pedidos[0].content)
    assert corpo["response_format"] == {"type": "json_object"}
    assert corpo["messages"] == [
        {"role": "system", "content": "o sistema"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "o que vês?"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9hqcGVn"}},
            ],
        },
    ]


def test_com_imagem_aceita_json_dentro_de_um_bloco_de_codigo():
    cliente, _ = _cliente(_com_conteudo('```json\n{"veiculo": false}\n```'))
    m = ModeloOpenAI("https://exemplo", "k", "m", cliente=cliente)
    assert m.completar_json_com_imagem("s", "m", b"x") == {"veiculo": False}


@pytest.mark.parametrize("conteudo", ["sem json nenhum", "[1, 2]"])
def test_com_imagem_resposta_sem_objeto_da_none(conteudo):
    cliente, _ = _cliente(_com_conteudo(conteudo))
    m = ModeloOpenAI("https://exemplo", "k", "m", cliente=cliente)
    assert m.completar_json_com_imagem("s", "m", b"x") is None


def test_com_imagem_erro_http_da_none():
    cliente, _ = _cliente(lambda _: httpx.Response(400, json={"error": "sem visão"}))
    m = ModeloOpenAI("https://exemplo", "k", "m", cliente=cliente)
    assert m.completar_json_com_imagem("s", "m", b"x") is None


def test_falso_com_imagem_da_none(monkeypatch):
    monkeypatch.delenv("IA_FORNECEDOR", raising=False)
    assert obter_modelo().completar_json_com_imagem("s", "m", b"x") is None
