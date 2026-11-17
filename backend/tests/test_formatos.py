from backend.formatos import Contexto, Desvio


def test_desvio_imediato_por_omissao_falso():
    d = Desvio(us="US08", classe="seguranca", resumo="r", habitual=None)
    assert d.imediato is False


def test_contexto_com_quatro_campos_continua_a_funcionar():
    assert Contexto([], [], [], False).aparelho_tomada is None
