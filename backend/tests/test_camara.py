import io
import subprocess
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import camara

JPEG_A = b"\xff\xd8aaa\xff\xd9"
JPEG_B = b"\xff\xd8bbbb\xff\xd9"


@pytest.fixture(autouse=True)
def limpo(monkeypatch):
    monkeypatch.delenv("CAMERA_RTSP_URL", raising=False)
    camara.definir_foto_fixa(None)
    yield
    camara.definir_foto_fixa(None)


# --- capturar ---


def test_sem_url_nao_ha_imagem():
    assert camara.capturar() is None


def test_foto_fixa_ganha_a_camara(monkeypatch):
    monkeypatch.setenv("CAMERA_RTSP_URL", "rtsp://camara/x")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("não devia chamar o ffmpeg"))
    camara.definir_foto_fixa(JPEG_A)
    assert camara.capturar() == JPEG_A


def test_captura_pelo_ffmpeg(monkeypatch):
    monkeypatch.setenv("CAMERA_RTSP_URL", "rtsp://camara/x")
    comandos = []

    def correr(cmd, **kwargs):
        comandos.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=JPEG_A, stderr=b"")

    monkeypatch.setattr(subprocess, "run", correr)
    assert camara.capturar() == JPEG_A
    (cmd,) = comandos
    assert cmd[0] == "ffmpeg" and "rtsp://camara/x" in cmd
    assert "-frames:v" in cmd
    assert any("scale" in parte for parte in cmd)  # reduzida, para gastar menos tokens


@pytest.mark.parametrize(
    "falha",
    [
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, stdout=b"", stderr=b"erro"),
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, stdout=b"nao e jpeg", stderr=b""),
        lambda cmd, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd, 15)),
        lambda cmd, **k: (_ for _ in ()).throw(FileNotFoundError("ffmpeg")),
    ],
    ids=["codigo-de-erro", "nao-jpeg", "timeout", "sem-ffmpeg"],
)
def test_falhas_da_captura_dao_none(monkeypatch, falha):
    monkeypatch.setenv("CAMERA_RTSP_URL", "rtsp://camara/x")
    monkeypatch.setattr(subprocess, "run", falha)
    assert camara.capturar() is None


def test_reduzir_sem_ffmpeg_devolve_a_original(monkeypatch):
    def sem_ffmpeg(*a, **k):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "run", sem_ffmpeg)
    assert camara.reduzir(JPEG_A) == JPEG_A


def test_reduzir_so_le_imagens_do_pipe(monkeypatch):
    # A fotografia vem de fora (POST /veiculos): o ffmpeg não pode adivinhar o formato, porque uma
    # playlist (HLS, concat...) o faria abrir ficheiros locais ou outros endereços.
    comandos = []

    def correr(cmd, **kwargs):
        comandos.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=JPEG_B, stderr=b"")

    monkeypatch.setattr(subprocess, "run", correr)
    assert camara.reduzir(JPEG_A) == JPEG_B
    (cmd,) = comandos
    entrada = cmd.index("-i")
    assert cmd[entrada + 1] == "pipe:0"
    antes = cmd[:entrada]
    assert antes[antes.index("-f") + 1] == "image2pipe"
    assert antes[antes.index("-protocol_whitelist") + 1] == "pipe"


# --- guardar e servir ---


def _cliente() -> TestClient:
    app = FastAPI()
    app.include_router(camara.router)
    return TestClient(app)


def test_guardar_e_servir():
    url = camara.guardar(JPEG_A)
    assert url.startswith("/imagens/") and url.endswith(".jpg")
    r = _cliente().get(url)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content == JPEG_A


@pytest.mark.parametrize("nome", ["nao-existe.jpg", "..%2Fhomaly.db", "0" * 32 + ".png"])
def test_nomes_invalidos_ou_inexistentes_dao_404(nome):
    assert _cliente().get(f"/imagens/{nome}").status_code == 404


# --- separar JPEG de um stream ---


def test_separar_imagens_coladas_e_guarda_o_resto():
    imagens, resto = camara.separar(JPEG_A + JPEG_B + b"\xff\xd8meia")
    assert imagens == [JPEG_A, JPEG_B]
    assert resto == b"\xff\xd8meia"


def test_separar_ignora_lixo_antes_da_imagem():
    imagens, resto = camara.separar(b"lixo" + JPEG_A)
    assert imagens == [JPEG_A] and resto == b""


# --- detetor ---


class Processo:
    """Um ffmpeg falso: o stdout dá os bytes dados e acaba."""

    def __init__(self, dados: bytes):
        self.stdout = io.BytesIO(dados)
        self.morto = False

    def kill(self):
        self.morto = True

    def wait(self, timeout=None):
        return 0


def test_detetor_conta_movimentos_com_pausa():
    tempos = iter([0.0, 10.0, 40.0])  # a 2.ª imagem cai na pausa de 30 s
    parar = threading.Event()
    abertos = []

    def abrir(url, limiar):
        abertos.append((url, limiar))
        if len(abertos) > 1:
            parar.set()
            return Processo(b"")
        return Processo(JPEG_A + JPEG_B + JPEG_A)

    d = camara.Detetor("rtsp://x", limiar=0.1, pausa_s=30, abrir=abrir,
                       relogio=lambda: next(tempos), esperar=lambda s: parar.is_set())
    d.correr(parar)
    assert d.movimentos == 2
    assert abertos[0] == ("rtsp://x", 0.1)


def test_detetor_volta_a_abrir_com_espera_crescente():
    esperas = []
    parar = threading.Event()

    def esperar(s):
        esperas.append(s)
        if len(esperas) == 4:
            parar.set()
        return parar.is_set()

    d = camara.Detetor("rtsp://x", limiar=0.1, pausa_s=30, abrir=lambda u, l: Processo(b""),
                       relogio=lambda: 0.0, esperar=esperar)
    d.correr(parar)
    assert esperas == [5, 10, 20, 40]
    assert d.movimentos == 0


def test_detetor_sem_ffmpeg_espera_e_tenta_outra_vez():
    parar = threading.Event()
    tentativas = []

    def abrir(url, limiar):
        tentativas.append(1)
        raise FileNotFoundError("ffmpeg")

    d = camara.Detetor("rtsp://x", limiar=0.1, pausa_s=30, abrir=abrir,
                       relogio=lambda: 0.0, esperar=lambda s: len(tentativas) >= 2)
    d.correr(parar)
    assert len(tentativas) == 2


def test_arrancar_sem_url_nao_faz_nada():
    assert camara.arrancar() is None
    assert camara.movimentos() == 0


def test_arrancar_desligado_por_variavel(monkeypatch):
    monkeypatch.setenv("CAMERA_RTSP_URL", "rtsp://camara/x")
    monkeypatch.setenv("DETETOR_VIDEO", "0")
    assert camara.arrancar() is None
