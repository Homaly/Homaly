from backend.formatos import Resolucao

from .conftest import AGORA


def test_resolucao_diz_como_acabou():
    r = Resolucao(us="US08", texto="a porta fechou às 15:00", em=AGORA)

    assert (r.us, r.texto, r.em) == ("US08", "a porta fechou às 15:00", AGORA)
