from servicio import tema_del_dia


def test_tema():
    assert tema_del_dia() in ["claro", "oscuro", "sepia"]
