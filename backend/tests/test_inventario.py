"""O inventário: o nome e a divisão de cada dispositivo, e o papel que daí se deduz."""

from pathlib import Path

import pytest

from backend.ia.modelo import ModeloFalso

from backend import inventario
from backend.formatos import Leitura

from .conftest import AGORA


def test_uma_leitura_sem_id_fica_com_os_valores_do_tipo():
    porta = inventario.de(Leitura("porta", "sensorState", "normal", AGORA))
    camara = inventario.de(Leitura("camara", "motionDetected", "", AGORA))

    assert porta == inventario.Dispositivo("porta", "Porta da rua", "a sala", "porta_da_rua")
    assert camara.papel == "interior"


def test_um_dispositivo_do_inventario(casa):
    janela = inventario.de(Leitura("porta", "sensorState", "normal", AGORA, "janela-quarto"))

    assert janela == inventario.Dispositivo("janela-quarto", "Janela do quarto", "o quarto", "janela")


def test_um_id_que_nao_esta_no_inventario_fica_com_os_valores_do_tipo(casa):
    assert inventario.de(Leitura("porta", "sensorState", "normal", AGORA, "outra")).papel == "porta_da_rua"


def test_o_que_conta_como_dentro_de_casa(casa):
    assert inventario.conta_como_casa(Leitura("camara", "motionDetected", "", AGORA, "cam-sala"))
    assert not inventario.conta_como_casa(Leitura("camara", "motionDetected", "", AGORA, "cam-rua"))
    assert inventario.conta_como_casa(Leitura("porta", "sensorState", "", AGORA, "porta-rua"))
    assert not inventario.conta_como_casa(Leitura("porta", "sensorState", "", AGORA, "janela-quarto"))
    assert inventario.conta_como_casa(Leitura("lampada", "power", "on", AGORA, "luz-sala"))


def test_contracoes():
    assert inventario.com_preposicao("em", "a sala") == "na sala"
    assert inventario.com_preposicao("em", "o quarto") == "no quarto"
    assert inventario.com_preposicao("de", "a cozinha") == "da cozinha"
    assert inventario.com_preposicao("em", "casa") == "em casa"


def test_o_ficheiro_do_kit_so_tem_id_nome_e_divisao():
    import csv

    with open(Path(inventario.INVENTARIO), newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        linhas = list(leitor)
    assert leitor.fieldnames == ["id", "nome", "divisao"]
    assert linhas
    assert all(l["divisao"].split(" ")[0] in ("a", "o", "as", "os") for l in linhas)


def test_o_papel_de_cada_dispositivo_do_kit():
    # O ficheiro real (sem configurar): a porta da rua fica na sala, mas o nome di-lo.
    inventario.configurar(None)
    papeis = {
        "937ac145-dc42-4dcf-9180-ad481ef33c82": ("porta", "porta_da_rua"),
        "janela-quarto": ("porta", "janela"),
        "0915a1d0-544e-4427-b35c-46110d21a013": ("camara", "interior"),
        "camara-quarto": ("camara", "interior"),
        "camara-entrada": ("camara", "exterior"),
    }
    for id, (tipo, esperado) in papeis.items():
        assert inventario.de(Leitura(tipo, "", "", AGORA, id)).papel == esperado, id


@pytest.mark.parametrize(
    "nome, divisao, esperado",
    [
        ("Porta da rua", "a sala", "porta_da_rua"),  # o nome manda, mesmo fora da entrada
        ("Porta de entrada", "a cozinha", "porta_da_rua"),
        ("Porta principal", "o corredor", "porta_da_rua"),
        ("Janela do quarto", "o quarto", "janela"),
        ("Janela da entrada", "a entrada", "janela"),
        ("Porta da varanda", "a sala", "janela"),  # abri-la não é sair de casa
        ("Porta da garagem", "a garagem", "janela"),
        ("Sensor de contacto", "o hall", "porta_da_rua"),  # o nome não diz: vai pela divisão
        ("Contact sensor", "a entrada", "porta_da_rua"),
        ("Porta", "o vestíbulo", "porta_da_rua"),
        ("Sensor de contacto", "o quarto", "janela"),
        ("Porta", "a sala", "janela"),
    ],
)
def test_o_papel_de_um_sensor_de_contacto(nome, divisao, esperado):
    assert inventario.papel("porta", nome, divisao) == esperado


@pytest.mark.parametrize(
    "nome, divisao, esperado",
    [
        ("Câmara da sala", "a sala", "interior"),
        ("Câmara do hall", "a entrada", "interior"),  # "entrada" sozinha é o hall, dentro de casa
        ("Câmara da entrada de veículos", "a entrada", "exterior"),
        ("Câmara do jardim", "o jardim", "exterior"),
        ("Camera", "a garagem", "exterior"),
        ("Câmara da porta da rua", "a entrada", "exterior"),
        ("Câmara exterior", "a sala", "exterior"),
        ("Camera", "o quarto", "interior"),
    ],
)
def test_o_papel_de_uma_camara(nome, divisao, esperado):
    assert inventario.papel("camara", nome, divisao) == esperado


def test_os_outros_tipos_nao_tem_papel():
    assert inventario.papel("lampada", "Luz da entrada", "a entrada") == ""
    assert inventario.papel("tomada", "Tomada do jardim", "o jardim") == ""


def test_o_ficheiro_vem_de_dispositivos_csv(monkeypatch, tmp_path):
    ficheiro = tmp_path / "casa.csv"
    ficheiro.write_text("id,nome,divisao\nc9,Câmara da garagem,a garagem\n", encoding="utf-8")
    monkeypatch.setenv("DISPOSITIVOS_CSV", str(ficheiro))
    inventario.configurar(None)
    try:
        camara = inventario.de(Leitura("camara", "motionDetected", "", AGORA, "c9"))
        assert (camara.divisao, camara.papel) == ("a garagem", "exterior")
    finally:
        monkeypatch.delenv("DISPOSITIVOS_CSV")
        inventario.configurar(None)


# O que o MCP diz (name e roomName de cada dispositivo), para os ids que não estão no CSV


def _mcp(*dispositivos: tuple[str, str, str, str]) -> None:
    inventario.registar([{"id": i, "tipo": t, "nome": n, "divisao": d} for i, t, n, d in dispositivos])


def _de(tipo: str, id: str) -> inventario.Dispositivo:
    return inventario.de(Leitura(tipo, "", "", AGORA, id))


def test_uma_casa_nova_como_a_do_kit(casa):
    # Outra casa, com os nomes de fábrica do kit: não dizem nada, e fica tudo como no MVP.
    _mcp(
        ("x-porta", "porta", "Contact sensor", "Hack 9"),
        ("x-camara", "camara", "Camera", "Hack 9"),
        ("x-luz", "lampada", "Light", "Hack 9"),
    )
    assert _de("porta", "x-porta") == inventario.Dispositivo("x-porta", "Porta da rua", "a sala", "porta_da_rua")
    assert _de("camara", "x-camara") == inventario.Dispositivo("x-camara", "Câmara da sala", "a sala", "interior")
    assert _de("lampada", "x-luz") == inventario.Dispositivo("x-luz", "Luz da sala", "a sala", "")
    assert inventario.origem("x-porta") == "mcp"


def test_nomes_e_divisoes_a_serio_usam_se(casa):
    _mcp(("x-luz", "lampada", "Luz da cozinha", "Cozinha"))
    assert _de("lampada", "x-luz") == inventario.Dispositivo("x-luz", "Luz da cozinha", "a cozinha", "")


def test_cada_campo_conta_por_si(casa):
    # Um nome de fábrica numa divisão a sério, e um nome a sério numa divisão que não diz nada.
    _mcp(("x-luz", "lampada", "Light", "Quarto"), ("x-janela", "porta", "Janela da sala", "Hack 4"))
    assert _de("lampada", "x-luz") == inventario.Dispositivo("x-luz", "Luz do quarto", "o quarto", "")
    assert _de("porta", "x-janela") == inventario.Dispositivo("x-janela", "Janela da sala", "a sala", "janela")


@pytest.mark.parametrize(
    "nome, generico",
    [
        ("Contact sensor", True),
        ("Light 2", True),
        ("Camera", True),
        ("Security hub", True),
        ("", True),
        ("Porta da rua", False),
        ("Câmara do jardim", False),
        ("Tomada da máquina", False),
        ("Window sensor", False),  # diz que é uma janela
    ],
)
def test_os_nomes_de_fabrica_nao_contam(nome, generico):
    assert (inventario._nome_do_mcp(nome) == "") is generico


def test_um_generico_ao_lado_da_porta_de_entrada_e_outra_abertura(casa):
    _mcp(
        ("x-entrada", "porta", "Porta de entrada", "Sala"),
        ("x-outro", "porta", "Contact sensor", "Quarto"),
    )
    assert _de("porta", "x-entrada").papel == "porta_da_rua"
    # Sem nome que diga alguma coisa, o nome vem do papel e da divisão (não "Porta da rua").
    assert _de("porta", "x-outro") == inventario.Dispositivo("x-outro", "Janela do quarto", "o quarto", "janela")


def test_um_sensor_no_hall_e_claramente_a_porta_da_rua(casa):
    _mcp(("x-hall", "porta", "Contact sensor", "Hall"), ("x-outro", "porta", "Contact sensor", "Sala"))
    assert _de("porta", "x-hall").papel == "porta_da_rua"
    assert _de("porta", "x-outro").papel == "janela"


def test_o_csv_ganha_ao_mcp():
    # O kit: o MCP diz "Contact sensor" em "Hack 4", o CSV diz "Porta da rua" na sala.
    inventario.configurar(None)
    kit = "937ac145-dc42-4dcf-9180-ad481ef33c82"
    _mcp((kit, "porta", "Contact sensor", "Hack 4"))
    assert _de("porta", kit) == inventario.Dispositivo(kit, "Porta da rua", "a sala", "porta_da_rua")
    assert inventario.origem(kit) == "csv"


def test_as_linhas_do_kit_no_csv_nao_contam_noutra_casa(casa):
    # O CSV de teste tem "Porta da rua" (porta-rua), mas o MCP não a devolve: noutra casa, não existe.
    _mcp(("x-a", "porta", "Contact sensor", "Sala"))
    assert _de("porta", "x-a").papel == "porta_da_rua"


def test_os_simulados_do_csv_continuam_a_contar(casa):
    _mcp(("x-a", "porta", "Contact sensor", "Sala"))
    assert _de("porta", "janela-quarto").papel == "janela"
    assert _de("camara", "cam-rua").papel == "exterior"


def test_um_id_fora_do_csv_e_do_mcp_fica_com_os_valores_do_tipo(casa):
    _mcp(("x-a", "porta", "Contact sensor", "Sala"))
    assert _de("porta", "outro") == inventario.Dispositivo("outro", "Porta da rua", "a sala", "porta_da_rua")
    assert inventario.origem("outro") == "omissao"


def test_sem_nome_no_mcp_fica_o_nome_do_tipo_e_da_divisao(casa):
    _mcp(("x-cam", "camara", "Camera", "Quarto"), ("x-hub", "hub", "Security hub", "Hack 4"))
    assert _de("camara", "x-cam").nome == "Câmara do quarto"
    assert _de("hub", "x-hub").nome == "Hub de segurança"


def test_sem_nome_no_mcp_nem_divisao(casa):
    _mcp(("x-luz", "lampada", "", ""))
    assert _de("lampada", "x-luz") == inventario.Dispositivo("x-luz", "Luz da sala", "a sala", "")


@pytest.mark.parametrize(
    "divisao, esperado",
    [
        ("Sala", "a sala"),
        ("Quarto principal", "o quarto principal"),
        ("Casa de banho", "a casa de banho"),
        ("Escritório", "o escritório"),
        ("o sótão", "o sótão"),  # já traz o artigo
        ("Hack 4", "a sala"),  # desconhecida: não diz nada
        ("", "a sala"),
    ],
)
def test_a_divisao_do_mcp_ganha_o_artigo(divisao, esperado):
    assert inventario._com_artigo(divisao) == esperado


def test_um_dispositivo_novo_vai_para_o_log_uma_vez(casa, caplog):
    caplog.set_level("INFO", logger="backend.inventario")
    _mcp(("x-porta", "porta", "Contact sensor", "Hack 9"))
    inventario.classificar(ModeloFalso())  # sem IA: ficam as regras, e o log diz isso
    _mcp(("x-porta", "porta", "Contact sensor", "Hack 9"))
    avisos = [r.getMessage() for r in caplog.records if "dispositivo novo" in r.getMessage()]
    assert avisos == [
        "dispositivo novo do MCP (pelas regras): porta x-porta 'Porta da rua' (no MCP 'Contact sensor')"
        " em 'a sala' (no MCP 'Hack 9') -> porta_da_rua"
    ]


def test_os_do_csv_nao_vao_para_o_log(casa, caplog):
    caplog.set_level("INFO", logger="backend.inventario")
    _mcp(("janela-quarto", "porta", "Contact sensor", "Hack 9"))
    assert not [r for r in caplog.records if "dispositivo novo" in r.getMessage()]


# A IA: lê os dispositivos do MCP que não estão no CSV e diz o nome, a divisão e o papel


class IA:
    """Um modelo que responde com `dispositivos` e conta as chamadas."""

    def __init__(self, dispositivos: list[dict] | None):
        self.dispositivos = dispositivos
        self.chamadas: list[str] = []

    def completar_json(self, sistema: str, mensagem: str) -> dict | None:
        self.chamadas.append(mensagem)
        return None if self.dispositivos is None else {"dispositivos": self.dispositivos}


CASA_NOVA = [
    ("x-porta", "porta", "Front door sensor", "Entrance"),
    ("x-varanda", "porta", "Balcony door", "Living room"),
    ("x-cam", "camara", "Garden cam", "Outside"),
    ("x-luz", "lampada", "Light", "Hack 9"),
]


def _ia(ia: IA) -> None:
    _mcp(*CASA_NOVA)
    inventario.classificar(ia)


def test_a_ia_diz_o_que_sao_os_dispositivos_novos(casa):
    ia = IA([
        {"id": "x-porta", "nome": "Porta da rua", "divisao": "a entrada", "papel": "porta_da_rua"},
        {"id": "x-varanda", "nome": "Porta da varanda", "divisao": "a sala", "papel": "janela"},
        {"id": "x-cam", "nome": "Câmara do jardim", "divisao": "o jardim", "papel": "exterior"},
        {"id": "x-luz", "nome": None, "divisao": None, "papel": None},
    ])
    _ia(ia)

    assert _de("porta", "x-porta") == inventario.Dispositivo("x-porta", "Porta da rua", "a entrada", "porta_da_rua")
    assert _de("porta", "x-varanda") == inventario.Dispositivo("x-varanda", "Porta da varanda", "a sala", "janela")
    assert _de("camara", "x-cam") == inventario.Dispositivo("x-cam", "Câmara do jardim", "o jardim", "exterior")
    # O que a IA não identificou fica com as regras: um nome de fábrica em "Hack 9", como no MVP.
    assert _de("lampada", "x-luz") == inventario.Dispositivo("x-luz", "Luz da sala", "a sala", "")
    assert inventario.origem("x-porta") == "ia"
    assert inventario.origem("x-luz") == "mcp"
    assert inventario.por_classificar() == []


def test_a_ia_ve_a_casa_toda_e_so_classifica_os_que_nao_estao_no_csv(casa):
    ia = IA([])
    _mcp(*CASA_NOVA, ("janela-quarto", "porta", "Window", "Bedroom"))
    inventario.classificar(ia)
    [mensagem] = ia.chamadas
    assert '"janela-quarto"' in mensagem.split("Classifica estes ids")[0]  # no contexto
    assert "janela-quarto" not in mensagem.split("Classifica estes ids")[1]  # mas o CSV ganha


def test_o_que_a_ia_diz_de_invalido_nao_conta(casa):
    _ia(IA([
        {"id": "x-porta", "nome": "Porta", "divisao": "Entrada", "papel": "garagem"},  # sem artigo; papel que não existe
        {"id": "x-cam", "papel": "porta_da_rua"},  # um papel de outro tipo
        {"id": "outro", "nome": "Inventado", "divisao": "a sala", "papel": "janela"},  # um id que não foi pedido
        "lixo",
    ]))
    # Fica tudo com as regras, que não percebem inglês: "Entrance" não é uma divisão conhecida,
    # e "Garden cam" em "Outside" não diz nada que as regras conheçam.
    assert _de("porta", "x-porta").divisao == "a sala"
    assert _de("porta", "x-porta").papel == "porta_da_rua"
    assert _de("camara", "x-cam").papel == "interior"
    assert inventario.origem("outro") == "omissao"


def test_a_ia_nao_inventa_nome_para_um_nome_de_fabrica(casa):
    _ia(IA([{"id": "x-luz", "nome": "Luz da sala de estar", "divisao": None, "papel": None}]))
    assert _de("lampada", "x-luz").nome == "Luz da sala"


def test_sem_ia_ficam_as_regras_e_nao_volta_a_perguntar(casa):
    ia = IA(None)  # o modelo falhou
    _ia(ia)
    # As regras não percebem "Balcony door": sem uma porta da rua clara, conta como a porta da rua.
    assert _de("porta", "x-varanda").papel == "porta_da_rua"
    _mcp(*CASA_NOVA)
    inventario.classificar(ia)
    assert len(ia.chamadas) == 1  # neste processo, não pergunta outra vez


def test_o_que_a_ia_disse_fica_guardado_e_so_se_pergunta_outra_vez_se_o_mcp_mudar(casa):
    ia = IA([{"id": "x-cam", "nome": "Câmara do jardim", "divisao": "o jardim", "papel": "exterior"}])
    _ia(ia)
    inventario.esquecer_mcp()  # um reinício: a memória vai-se, a tabela fica
    _mcp(*CASA_NOVA)
    assert _de("camara", "x-cam").nome == "Câmara do jardim"
    assert "x-cam" not in inventario.por_classificar()

    _mcp(*[c if c[0] != "x-cam" else ("x-cam", "camara", "Hall cam", "Hall") for c in CASA_NOVA])
    assert "x-cam" in inventario.por_classificar()  # o MCP mudou o nome: volta a perguntar


def test_o_csv_ganha_a_ia(casa):
    _mcp(("janela-quarto", "porta", "Front door", "Entrance"))
    assert "janela-quarto" not in inventario.por_classificar()
    assert _de("porta", "janela-quarto").papel == "janela"


def test_a_porta_da_rua_da_ia_conta_para_os_genericos(casa):
    # A IA diz qual é a porta da rua: um sensor genérico passa a ser outra abertura.
    _mcp(("x-a", "porta", "Contact sensor", "Hack 9"), ("x-b", "porta", "Contact sensor 2", "Hack 9"))
    inventario.classificar(IA([{"id": "x-a", "nome": None, "divisao": None, "papel": "porta_da_rua"}]))
    assert _de("porta", "x-a").papel == "porta_da_rua"
    assert _de("porta", "x-b").papel == "janela"
