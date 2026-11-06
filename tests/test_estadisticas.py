"""Pruebas del informe estadistico final."""

import unittest

from admision import Admision
from estadisticas import calcular_estadisticas
from memoria import GestorMemoria
from planificador import PlanificadorSRTF
from proceso import ESTADO_TERMINADO, Proceso


def _simular(procesos):
    memoria = GestorMemoria()
    admision = Admision(procesos, memoria)
    planificador = PlanificadorSRTF(admision, memoria)
    planificador.simular()
    return planificador.reloj


class TestEstadisticas(unittest.TestCase):
    def test_un_proceso_sin_espera(self):
        procesos = [Proceso("P1", 50, 2, 4)]
        tiempo = _simular(procesos)
        informe = calcular_estadisticas(procesos, tiempo)

        self.assertEqual(tiempo, 6)
        fila = informe.procesos[0]
        self.assertEqual(fila.tiempo_retorno, 4)
        self.assertEqual(fila.tiempo_espera, 0)
        self.assertAlmostEqual(informe.rendimiento, 1 / 6)

    def test_apropiacion_calcula_retorno_espera_y_promedios(self):
        # P1 corre en t=0, P2 la apropia en t=1 y termina en t=3,
        # P1 termina en t=7.
        procesos = [Proceso("P1", 50, 0, 5), Proceso("P2", 50, 1, 2)]
        tiempo = _simular(procesos)
        informe = calcular_estadisticas(procesos, tiempo)
        por_id = {fila.id: fila for fila in informe.procesos}

        self.assertEqual(por_id["P2"].tiempo_finalizacion, 3)
        self.assertEqual(por_id["P2"].tiempo_retorno, 2)
        self.assertEqual(por_id["P2"].tiempo_espera, 0)
        self.assertEqual(por_id["P1"].tiempo_finalizacion, 7)
        self.assertEqual(por_id["P1"].tiempo_retorno, 7)
        self.assertEqual(por_id["P1"].tiempo_espera, 2)
        self.assertAlmostEqual(informe.retorno_promedio, 4.5)
        self.assertAlmostEqual(informe.espera_promedio, 1.0)
        # Ambos usan la CPU apenas llegan: respuesta 0.
        self.assertEqual(por_id["P1"].tiempo_respuesta, 0)
        self.assertEqual(por_id["P2"].tiempo_respuesta, 0)
        self.assertAlmostEqual(informe.respuesta_promedio, 0.0)
        self.assertEqual(informe.trabajos_terminados, 2)
        self.assertAlmostEqual(informe.rendimiento, 2 / 7)

    def test_espera_incluye_tiempo_en_listo_suspendido(self):
        procesos = [Proceso("P1", 300, 0, 3), Proceso("P2", 300, 0, 1)]
        tiempo = _simular(procesos)
        informe = calcular_estadisticas(procesos, tiempo)
        por_id = {fila.id: fila for fila in informe.procesos}

        # P2 es mas corto, pero no entra en memoria hasta que P1 termina.
        self.assertEqual(por_id["P2"].tiempo_finalizacion, 4)
        self.assertEqual(por_id["P2"].tiempo_espera, 3)
        self.assertEqual(por_id["P2"].tiempo_respuesta, 3)

    def test_solo_cuenta_procesos_terminados(self):
        terminado = Proceso("P1", 50, 0, 2)
        terminado.estado = ESTADO_TERMINADO
        terminado.tiempo_inicio = 0
        terminado.tiempo_finalizacion = 2
        pendiente = Proceso("P2", 50, 0, 2)

        informe = calcular_estadisticas([terminado, pendiente], 2)
        self.assertEqual(len(informe.procesos), 1)
        self.assertEqual(informe.trabajos_terminados, 1)

    def test_sin_tiempo_no_divide_por_cero(self):
        informe = calcular_estadisticas([], 0)
        self.assertEqual(informe.rendimiento, 0.0)
        self.assertEqual(informe.retorno_promedio, 0.0)


if __name__ == "__main__":
    unittest.main()
