"""Pruebas del flujo integrado de admision, memoria y planificacion."""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from admision import Admision, GRADO_MAXIMO_MULTIPROGRAMACION
from main import ejecutar_simulacion
from memoria import GestorMemoria
from planificador import (
    TIPO_APROPIACION,
    TIPO_CPU_OCIOSA,
    TIPO_NUEVA_ADMISION,
    PlanificadorSRTF,
)
from proceso import (
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_NUEVO,
    ESTADO_TERMINADO,
    Proceso,
)


class TestIntegracion(unittest.TestCase):
    def test_diez_procesos_respetan_cupo_y_liberan_toda_la_memoria(self):
        procesos = [Proceso(f"P{indice}", 50, 0, 1) for indice in range(1, 11)]
        memoria = GestorMemoria()
        admision = Admision(procesos, memoria)

        admision.procesar_arribos(0)
        self.assertEqual(admision.grado_multiprogramacion(), 5)
        self.assertEqual(sum(p.estado == ESTADO_NUEVO for p in procesos), 5)
        self.assertEqual(memoria.memoria_ocupada_total(), 250)

        grados_observados = []
        planificador = PlanificadorSRTF(
            admision,
            memoria,
            lambda evento: grados_observados.append(admision.grado_multiprogramacion()),
        )
        planificador.simular()

        self.assertTrue(
            all(grado <= GRADO_MAXIMO_MULTIPROGRAMACION for grado in grados_observados)
        )
        self.assertTrue(all(p.estado == ESTADO_TERMINADO for p in procesos))
        self.assertEqual(
            sorted(p.tiempo_finalizacion for p in procesos), list(range(1, 11))
        )
        self.assertEqual(memoria.memoria_libre_total(), 450)

    def test_suspendido_ingresa_al_liberarse_memoria(self):
        primero = Proceso("P1", 300, 0, 2)
        segundo = Proceso("P2", 300, 0, 1)
        memoria = GestorMemoria()
        admision = Admision([primero, segundo], memoria)
        eventos = []
        planificador = PlanificadorSRTF(admision, memoria, eventos.append)

        planificador.avanzar_unidad()
        self.assertEqual(segundo.estado, ESTADO_LISTO_SUSPENDIDO)
        self.assertIsNone(memoria.obtener_asignacion(segundo))

        planificador.simular()
        self.assertEqual(segundo.tiempo_inicio, 2)
        self.assertEqual(segundo.tiempo_finalizacion, 3)
        self.assertTrue(any(evento.tipo == TIPO_NUEVA_ADMISION for evento in eventos))
        self.assertEqual(memoria.memoria_libre_total(), 450)

    def test_empate_conserva_cpu_y_un_arribo_mas_corto_apropia(self):
        procesos = [
            Proceso("P1", 50, 0, 5),
            Proceso("P2", 50, 1, 4),
            Proceso("P3", 50, 2, 1),
        ]
        memoria = GestorMemoria()
        admision = Admision(procesos, memoria)
        eventos = []
        planificador = PlanificadorSRTF(admision, memoria, eventos.append)
        planificador.simular()

        apropiaciones = [evento for evento in eventos if evento.tipo == TIPO_APROPIACION]
        self.assertEqual(
            [(evento.tiempo, evento.proceso_id) for evento in apropiaciones],
            [(2, "P3")],
        )
        self.assertEqual([p.tiempo_inicio for p in procesos], [0, 6, 2])
        self.assertEqual([p.tiempo_finalizacion for p in procesos], [6, 10, 3])

    def test_cpu_ociosa_hasta_el_primer_arribo(self):
        proceso = Proceso("P1", 450, 3, 2)
        memoria = GestorMemoria()
        admision = Admision([proceso], memoria)
        eventos = []
        planificador = PlanificadorSRTF(admision, memoria, eventos.append)
        planificador.simular()

        self.assertEqual(
            [evento.tiempo for evento in eventos if evento.tipo == TIPO_CPU_OCIOSA],
            [0],
        )
        self.assertEqual(proceso.tiempo_inicio, 3)
        self.assertEqual(proceso.tiempo_finalizacion, 5)
        self.assertEqual(memoria.memoria_libre_total(), 450)

    def test_demo_muestra_eventos_colas_memoria_y_finalizacion(self):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = ejecutar_simulacion(Path("data/procesos_demo.csv"))

        texto = salida.getvalue()
        self.assertEqual(codigo, 0)
        self.assertIn("t = 0 | Llegan: P1.", texto)
        self.assertIn("apropia la CPU", texto)
        self.assertIn("LISTO_SUSPENDIDO: P5", texto)
        self.assertIn("Se admiten a LISTO: P5.", texto)
        self.assertIn("Se libera la memoria", texto)
        self.assertIn("Inicio   Tamanio   Proceso", texto)
        self.assertIn("Libre usuario: 450K", texto)
        self.assertIn("Simulacion finalizada en t = 31.", texto)


if __name__ == "__main__":
    unittest.main()
