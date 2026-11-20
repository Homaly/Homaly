"""A câmara da entrada de veículos (US13): imagens do stream RTSP e movimento visto no vídeo.

O MCP não dá imagens, e o `motionDetected` da câmara vem sempre "" (visto a 2026-11-19, mesmo com
a app da Altice a notificar o movimento). Por isso tudo o que é imagem passa pelo `ffmpeg`, sobre o
stream RTSP em `CAMERA_RTSP_URL` (um relay go2rtc da Altice; a VM chega-lhe, a rede do local não):

- `capturar()`: uma imagem, quando a regra precisa de olhar (até 15 s). Com `definir_foto_fixa`
  (rota /dev/us13), devolve essa fotografia em vez da câmara, para a demo sem câmara.
- `Detetor`: um `ffmpeg` sempre ligado ao stream, só com as keyframes (`-skip_frame nokey`, para o
  H.265 1080p não comer a CPU da VM), que deixa passar uma imagem quando a cena muda
  (`select=gt(scene,LIMIAR)`). Cada mudança fora da pausa (`DETETOR_PAUSA_S`, 30 s: um movimento
  dá 2 a 4 imagens seguidas) soma um a `movimentos()`. A regra us13 vê o contador subir.
- As imagens saem reduzidas a 1024 px de largura: chega para ler uma matrícula e gasta menos de
  metade dos tokens do modelo de visão.

A URL nunca vai para o registo: pode ter credenciais.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend import db

registo = logging.getLogger(__name__)

ESCALA = "scale='min(1024,iw)':-2"  # no máximo 1024 px de largura, sem aumentar as pequenas
CAPTURA_TIMEOUT_S = 15
ESPERA_MIN_S, ESPERA_MAX_S = 5, 60  # entre tentativas, quando o ffmpeg do detetor morre
_NOME_IMAGEM = re.compile(r"^[0-9a-f]{32}\.jpg$")
_INICIO, _FIM = b"\xff\xd8", b"\xff\xd9"

_foto_fixa: bytes | None = None


def _url() -> str:
    return os.environ.get("CAMERA_RTSP_URL", "").strip()


def definir_foto_fixa(jpeg: bytes | None) -> None:
    """Para a demo sem câmara: `capturar()` passa a devolver esta fotografia (None volta à câmara)."""
    global _foto_fixa
    _foto_fixa = jpeg


def capturar() -> bytes | None:
    """Uma imagem JPEG da câmara agora, ou None (sem URL, sem ffmpeg, stream em baixo)."""
    if _foto_fixa is not None:
        return _foto_fixa
    url = _url()
    if not url:
        return None
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp", "-i", url,
           "-frames:v", "1", "-vf", ESCALA, "-f", "image2", "-c:v", "mjpeg", "-q:v", "5", "pipe:1"]
    return _correr_ffmpeg(cmd, None, "tirar uma imagem da câmara")


def reduzir(jpeg: bytes) -> bytes:
    """A imagem com no máximo 1024 px de largura; sem ffmpeg, a original."""
    # A imagem vem de fora (POST /veiculos): só se aceitam imagens e só o pipe, para uma playlist
    # (HLS, concat...) não pôr o ffmpeg a abrir ficheiros locais ou outros endereços.
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-protocol_whitelist", "pipe", "-f", "image2pipe",
           "-i", "pipe:0", "-vf", ESCALA,
           "-f", "image2", "-c:v", "mjpeg", "-q:v", "5", "pipe:1"]
    return _correr_ffmpeg(cmd, jpeg, "reduzir a imagem") or jpeg


def _correr_ffmpeg(cmd: list[str], entrada: bytes | None, para: str) -> bytes | None:
    try:
        r = subprocess.run(cmd, input=entrada, capture_output=True, timeout=CAPTURA_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as erro:
        registo.warning("Não consegui %s: %s", para, type(erro).__name__)
        return None
    if r.returncode != 0 or not r.stdout.startswith(_INICIO):
        registo.warning("Não consegui %s (ffmpeg terminou com %s)", para, r.returncode)
        return None
    return r.stdout


# --- guardar e servir as imagens das anomalias ---


def _pasta() -> Path:
    """Ao lado da base de dados: em produção fica no mesmo volume (/data)."""
    return Path(db.CAMINHO).resolve().parent / "imagens"


def guardar(jpeg: bytes) -> str:
    """Guarda a imagem e devolve o caminho para a `imagemUrl` da anomalia ("/imagens/<id>.jpg")."""
    pasta = _pasta()
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{uuid.uuid4().hex}.jpg"
    (pasta / nome).write_bytes(jpeg)
    return f"/imagens/{nome}"


router = APIRouter()


@router.get("/imagens/{nome}")
def servir(nome: str) -> FileResponse:
    ficheiro = _pasta() / nome
    if not _NOME_IMAGEM.match(nome) or not ficheiro.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(ficheiro, media_type="image/jpeg")


# --- o detetor de movimento no vídeo ---


def separar(dados: bytes) -> tuple[list[bytes], bytes]:
    """As imagens JPEG completas em `dados` e o que sobra (uma imagem a meio)."""
    imagens = []
    while True:
        inicio = dados.find(_INICIO)
        if inicio == -1:
            return imagens, b""
        fim = dados.find(_FIM, inicio + 2)
        if fim == -1:
            return imagens, dados[inicio:]
        imagens.append(dados[inicio : fim + 2])
        dados = dados[fim + 2 :]


def _abrir_ffmpeg(url: str, limiar: float) -> subprocess.Popen:
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-skip_frame", "nokey",
           "-rtsp_transport", "tcp", "-i", url,
           "-vf", f"select='gt(scene,{limiar})',{ESCALA}", "-fps_mode", "vfr",
           "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", "5", "pipe:1"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


class Detetor:
    """Conta os movimentos que o `ffmpeg` vê no stream; volta a ligar-se se o stream cair."""

    def __init__(
        self,
        url: str,
        *,
        limiar: float,
        pausa_s: float,
        abrir: Callable[[str, float], object] = _abrir_ffmpeg,
        relogio: Callable[[], float] = time.monotonic,
        esperar: Callable[[float], bool] | None = None,
    ):
        self._url, self._limiar, self._pausa_s = url, limiar, pausa_s
        self._abrir, self._relogio = abrir, relogio
        self._esperar = esperar
        self._processo = None
        self._ultimo: float | None = None
        self.movimentos = 0

    def correr(self, parar: threading.Event) -> None:
        esperar = self._esperar or parar.wait
        espera = ESPERA_MIN_S
        while not parar.is_set():
            try:
                self._processo = self._abrir(self._url, self._limiar)
            except OSError as erro:
                registo.warning("O detetor de movimento não arrancou: %s", type(erro).__name__)
            else:
                if self._ler(self._processo):
                    espera = ESPERA_MIN_S  # o stream funcionou: a próxima falha espera pouco
                self._processo.wait()
            if esperar(espera):
                return
            espera = min(espera * 2, ESPERA_MAX_S)

    def terminar(self) -> None:
        if self._processo is not None:
            self._processo.kill()

    def _ler(self, processo) -> bool:
        """Lê o stdout até o ffmpeg acabar; True se chegou alguma imagem."""
        resto, viu = b"", False
        while bloco := processo.stdout.read(65536):
            imagens, resto = separar(resto + bloco)
            for _ in imagens:
                viu = True
                agora = self._relogio()
                if self._ultimo is None or agora - self._ultimo >= self._pausa_s:
                    self._ultimo = agora
                    self.movimentos += 1
        return viu


_detetor: Detetor | None = None
_simulados = 0  # os de /dev/us13


def simular_movimento() -> None:
    """Para a demo: conta como se o detetor tivesse visto um movimento."""
    global _simulados
    _simulados += 1


def movimentos() -> int:
    """Quantos movimentos o detetor já viu desde o arranque, mais os simulados."""
    return (_detetor.movimentos if _detetor is not None else 0) + _simulados


def arrancar() -> Callable[[], None] | None:
    """Liga o detetor numa thread; devolve a função que o para, ou None se não há câmara."""
    global _detetor
    url = _url()
    if not url or os.environ.get("DETETOR_VIDEO", "1") == "0":
        return None
    from backend.regras._comum import numero

    _detetor = Detetor(url, limiar=numero("DETETOR_LIMIAR", 0.1), pausa_s=numero("DETETOR_PAUSA_S", 30))
    parar = threading.Event()
    threading.Thread(target=_detetor.correr, args=(parar,), name="detetor-camara", daemon=True).start()
    registo.info("Detetor de movimento da câmara ligado")

    def terminar() -> None:
        parar.set()
        _detetor.terminar()

    return terminar
