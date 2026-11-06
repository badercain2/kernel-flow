"""Pruebas del estilo de consola y del panel con tablas."""

import io
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from admision import Admision
from carga import cargar_procesos
from estilo import Celda, Estilo, acomodar_en_filas, largo_visible
from memoria import GestorMemoria
from panel import PanelConsola
from planificador import PlanificadorSRTF


class TestEstilo(unittest.TestCase):
    def test_sin_color_no_agrega_codigos(self):
        estilo = Estilo(color=False)
        self.assertEqual(estilo.c("hola", "rojo"), "hola")

    def test_color_no_cambia_el_largo_visible(self):
        estilo = Estilo(color=True)
        texto = estilo.c("P1", "amarillo", "negrita")
        self.assertNotEqual(texto, "P1")
        self.assertEqual(largo_visible(texto), 2)

    def test_tabla_con_colores_queda_alineada(self):
        estilo = Estilo(color=True, unicode=True)
        lineas = estilo.tabla(
            ("ID", "Estado"),
            [(Celda("P1", ("amarillo",)), Celda("EJECUCION", ("verde",))),
             ("P10", "LISTO")],
            titulo="Procesos",
        )
        anchos = {largo_visible(linea) for linea in lineas[1:]}
        self.assertEqual(len(anchos), 1, lineas)
        self.assertTrue(lineas[1].endswith("\x1b[0m"))

    def test_tabla_ascii_si_no_hay_unicode(self):
        lineas = Estilo(color=False, unicode=False).tabla(("A",), [(1,)])
        self.assertTrue(lineas[0].startswith("+"))
        self.assertIn("| A |", lineas[1])

    def test_tabla_vacia_muestra_texto(self):
        lineas = Estilo().tabla(("ID", "KB"), [], vacia="CPU OCIOSA")
        self.assertTrue(any("CPU OCIOSA" in linea for linea in lineas))

    def test_numeros_a_la_derecha(self):
        lineas = Estilo().tabla(("Valor",), [(5,), (150,)])
        self.assertIn("|     5 |", lineas[3])

    def test_acomodar_en_filas_respeta_el_ancho(self):
        a = ["A" * 10, "A" * 10]
        b = ["B" * 10]
        juntos = acomodar_en_filas([a, b], ancho_maximo=30)
        self.assertEqual(juntos[0], "A" * 10 + "   " + "B" * 10)
        separados = acomodar_en_filas([a, b], ancho_maximo=15)
        self.assertEqual(separados, ["A" * 10, "A" * 10, "", "B" * 10])

    def test_detectar_desactiva_color_fuera_de_terminal_y_con_no_color(self):
        self.assertFalse(Estilo.detectar(io.StringIO()).color)

        class Terminal(io.StringIO):
            encoding = "utf-8"

            def isatty(self):
                return True

        self.assertTrue(Estilo.detectar(Terminal()).color)
        self.assertFalse(Estilo.detectar(Terminal(), sin_color=True).color)
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(Estilo.detectar(Terminal()).color)


class TestPanel(unittest.TestCase):
    def test_panel_muestra_cpu_colas_particiones_e_informe(self):
        procesos = cargar_procesos(Path("data/procesos_demo.csv"))
        memoria = GestorMemoria()
        admision = Admision(procesos, memoria)
        panel = PanelConsola(procesos, admision, memoria, Estilo(color=True))
        eventos = []
        planificador = PlanificadorSRTF(admision, memoria, eventos.append)

        salida = io.StringIO()
        with redirect_stdout(salida), mock.patch(
            "panel.ancho_terminal", return_value=200
        ):
            for _ in range(5):  # hasta t = 4: P5 queda suspendido
                planificador.procesar_instante()
                planificador.ejecutar_unidad()
            planificador.procesar_instante()
            panel.mostrar_paso(eventos, planificador.reloj, 1)
            planificador.simular()
            panel.mostrar_fin(planificador.reloj)

        texto = salida.getvalue()
        for esperado in (
            "CPU - EJECUCION",
            "Cola LISTO (en memoria)",
            "Cola LISTO_SUSPENDIDO (sin memoria)",
            "Memoria principal (KB)",
            "Frag.Int.",
            "Ocupada",
            "[SUSPENSION]",
            "[APROPIACION]",
            "Informe estadistico por proceso",
            "14.00 ut",
            "0.1935",
        ):
            self.assertIn(esperado, texto)


if __name__ == "__main__":
    unittest.main()
