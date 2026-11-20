"""Os eventos do histórico (US06): cada dispositivo comparado com a sua leitura anterior."""

from datetime import datetime

from backend.dispositivos import mudancas
from backend.formatos import Leitura

EM = datetime(2026, 11, 20, 10, 0)


def test_eventos_de_cada_janela_com_o_nome_do_inventario(casa):
    observador = mudancas.Observador()
    observador.ver([
        Leitura("porta", "sensorState", "normal", EM, "porta-rua"),
        Leitura("porta", "sensorState", "normal", EM, "janela-quarto"),
    ])

    eventos = observador.ver([
        Leitura("porta", "sensorState", "normal", EM, "porta-rua"),
        Leitura("porta", "sensorState", "alarm", EM, "janela-quarto"),
    ])

    assert [(e.dispositivo, e.descricao) for e in eventos] == [("Janela do quarto", "Abriu")]
