import unittest

from agentes import logs

LOG = """2026-11-15 10:00:01,123 INFO  Pedido 4812 creado en 35 ms para 192.168.1.20
2026-11-15 10:00:02,456 INFO  Pedido 4813 creado en 41 ms para 192.168.1.21
2026-11-15T10:00:03Z INFO  Pedido 4814 creado en 12 ms para 10.0.0.7
2026-11-15 10:00:04,000 ERROR No se pudo cobrar el pedido 4814: timeout tras 30000 ms
2026-11-15 10:00:05,000 DEBUG sesion 3f2b8c1e-9a4d-4e6f-8b7a-1c2d3e4f5a6b puntero 0x7ffde4a1
2026-11-15 10:00:06,000 INFO  Pedido 4815 creado en 20 ms para 10.0.0.7
""".splitlines()


class TestPlantilla(unittest.TestCase):
    def test_lineas_que_solo_cambian_en_datos_dan_la_misma_plantilla(self):
        self.assertEqual(len({logs.plantilla(l) for l in (LOG[0], LOG[1], LOG[2], LOG[5])}), 1)

    def test_tapa_fecha_ip_uuid_hex_y_numeros_pero_deja_las_palabras(self):
        p = logs.plantilla(LOG[4])
        self.assertEqual(p, "<*> DEBUG sesion <*> puntero <*>")


class TestAgrupar(unittest.TestCase):
    def test_cuenta_y_guarda_el_primer_ejemplo(self):
        grupos = logs.agrupar(LOG)
        self.assertEqual(len(grupos), 3)
        mayor = max(grupos, key=lambda g: g.veces)
        self.assertEqual((mayor.veces, mayor.linea, mayor.ejemplo), (4, 1, LOG[0]))

    def test_lineas_vacias_no_cuentan(self):
        self.assertEqual(logs.agrupar(["", "   ", "hola 1"])[0].veces, 1)


class TestFusionar(unittest.TestCase):
    def test_plantillas_que_solo_cambian_en_una_palabra_se_juntan(self):
        lineas = [f"Info Cargando paquete {n} desde disco" for n in ("Alfa", "Beta", "Gama", "Alfa")]
        grupos = logs.agrupar(lineas + ["Info Listo"])
        self.assertEqual(sorted((g.plantilla, g.veces) for g in grupos),
                         [("Info Cargando paquete <*> desde disco", 4), ("Info Listo", 1)])
        self.assertEqual(max(grupos, key=lambda g: g.veces).linea, 1)

    def test_dos_variantes_no_bastan_y_los_errores_no_se_juntan(self):
        self.assertEqual(len(logs.agrupar(["modo claro activo", "modo oscuro activo"])), 2)
        errores = [f"ERROR conexion {x}" for x in ("rechazada", "cerrada", "reiniciada")]
        self.assertEqual(len(logs.agrupar(errores)), 3)


class TestElegir(unittest.TestCase):
    def test_los_errores_van_primero_y_luego_las_raras(self):
        elegidos = logs.elegir(logs.agrupar(LOG), tope=2)
        self.assertIn("ERROR", elegidos[0].plantilla)
        self.assertIn("DEBUG", elegidos[1].plantilla)  # 1 vez; la de "Pedido" (4 veces) queda fuera


class TestInforme(unittest.TestCase):
    def test_informe_sin_ia_trae_cifras_y_tabla(self):
        md = logs.informe(LOG, modelo=None)
        self.assertIn("6 líneas, 3 plantillas", md)
        self.assertIn("| 4 | 1 |", md)
        self.assertNotIn("## Explicación", md)

    def test_el_modelo_recibe_plantillas_tapadas_y_su_texto_va_al_informe(self):
        vistos = []
        clave = "tok" + "9f8a7b6c5d4e3f2a"
        md = logs.informe(LOG + [f'2026-11-15 10:00:07 ERROR login con "{clave}"'],
                          modelo=lambda t: vistos.append(t) or "El cobro falla por timeout.")
        self.assertIn("## Explicación\n\nEl cobro falla por timeout.", md)
        self.assertNotIn(clave, vistos[0])
        self.assertNotIn(clave, md)

    def test_si_el_modelo_falla_el_informe_sale_igual_con_aviso(self):
        def roto(t):
            raise OSError("sin conexión")
        md = logs.informe(LOG, modelo=roto)
        self.assertIn("6 líneas", md)
        self.assertIn("no respondió", md)


if __name__ == "__main__":
    unittest.main()
