"""Pruebas unitarias para la administracion de memoria MVT y Best-Fit (HU2)."""

import unittest

from memoria import (
    DIRECCION_INICIO_USUARIO,
    MEMORIA_SO_KB,
    MEMORIA_TOTAL_KB,
    MEMORIA_USUARIO_KB,
    GestorMemoria,
)
from proceso import Proceso


class TestGestorMemoria(unittest.TestCase):
    """Verifica el contrato tecnico de memoria MVT y Best-Fit."""

    def test_estado_inicial_respeta_reserva_so_y_450k_usuario(self) -> None:
        memoria = GestorMemoria()

        self.assertEqual(memoria.memoria_so_kb, MEMORIA_SO_KB)
        self.assertEqual(memoria.memoria_usuario_kb, MEMORIA_USUARIO_KB)
        self.assertEqual(memoria.memoria_total_kb, MEMORIA_TOTAL_KB)
        self.assertEqual(memoria.direccion_inicio_usuario, DIRECCION_INICIO_USUARIO)

        particion_so = memoria.particion_sistema_operativo()
        self.assertEqual(particion_so.direccion_inicio, 0)
        self.assertEqual(particion_so.tamanio, 100)
        self.assertEqual(particion_so.direccion_fin, 100)

        huecos = memoria.obtener_huecos()
        self.assertEqual(len(huecos), 1)
        self.assertEqual(huecos[0].direccion_inicio, 100)
        self.assertEqual(huecos[0].tamanio, 450)
        self.assertEqual(huecos[0].direccion_fin, 550)
        self.assertTrue(huecos[0].libre)

    def test_asignar_memoria_exacta_llena_y_memoria_insuficiente(self) -> None:
        memoria = GestorMemoria()
        p_exacto = Proceso(id="P1", tamanio=450, tiempo_arribo=0, tiempo_irrupcion=5)
        p_extra = Proceso(id="P2", tamanio=10, tiempo_arribo=1, tiempo_irrupcion=3)

        asignacion = memoria.asignar(p_exacto)
        self.assertIsNotNone(asignacion)
        assert asignacion is not None
        self.assertEqual(asignacion.direccion_inicio, 100)
        self.assertEqual(asignacion.tamanio, 450)
        self.assertEqual(memoria.memoria_libre_total(), 0)
        self.assertEqual(memoria.memoria_ocupada_total(), 450)
        self.assertEqual(len(memoria.obtener_huecos()), 0)

        # Memoria llena: no puede asignar otro proceso
        self.assertFalse(memoria.puede_asignar(p_extra.tamanio))
        self.assertIsNone(memoria.asignar(p_extra))

    def test_rechazar_proceso_mayor_a_450k(self) -> None:
        memoria = GestorMemoria()
        p_grande = Proceso(id="P1", tamanio=451, tiempo_arribo=0, tiempo_irrupcion=4)

        self.assertFalse(memoria.puede_asignar(p_grande.tamanio))
        self.assertIsNone(memoria.asignar(p_grande))
        self.assertEqual(memoria.memoria_libre_total(), 450)

    def test_best_fit_elige_el_hueco_libre_mas_pequenio_suficiente(self) -> None:
        memoria = GestorMemoria()
        # Distribucion inicial de 450K (direcciones 100..550):
        # P1: 120K [100..220) -> se liberara (hueco de 120K)
        # P2: 50K  [220..270) -> permanece ocupado (separador)
        # P3: 80K  [270..350) -> se liberara (hueco de 80K)
        # P4: 50K  [350..400) -> permanece ocupado (separador)
        # Hueco final remanente: 150K [400..550)
        memoria.asignar("P1", 120)
        memoria.asignar("P2", 50)
        memoria.asignar("P3", 80)
        memoria.asignar("P4", 50)

        self.assertTrue(memoria.liberar("P1"))
        self.assertTrue(memoria.liberar("P3"))

        huecos = memoria.obtener_huecos()
        self.assertEqual(
            [(h.direccion_inicio, h.tamanio) for h in huecos],
            [(100, 120), (270, 80), (400, 150)],
        )

        # Un proceso de 70K entra en los tres huecos (120K, 80K, 150K).
        # Best-Fit debe elegir el hueco de 80K en direccion 270.
        p5 = Proceso(id="P5", tamanio=70, tiempo_arribo=2, tiempo_irrupcion=4)
        asignacion_p5 = memoria.asignar(p5)

        self.assertIsNotNone(asignacion_p5)
        assert asignacion_p5 is not None
        self.assertEqual(asignacion_p5.direccion_inicio, 270)
        self.assertEqual(asignacion_p5.tamanio, 70)

        # El hueco de 80K en 270 ahora deja un remanente libre de 10K en 340.
        self.assertEqual(
            [(h.direccion_inicio, h.tamanio) for h in memoria.obtener_huecos()],
            [(100, 120), (340, 10), (400, 150)],
        )

    def test_ciclo_asignar_liberar_y_reutilizar_con_fusion_de_huecos(self) -> None:
        memoria = GestorMemoria()
        p1 = Proceso(id="P1", tamanio=150, tiempo_arribo=0, tiempo_irrupcion=5)
        p2 = Proceso(id="P2", tamanio=200, tiempo_arribo=1, tiempo_irrupcion=6)
        p3 = Proceso(id="P3", tamanio=100, tiempo_arribo=2, tiempo_irrupcion=4)

        memoria.asignar(p1)  # [100..250)
        memoria.asignar(p2)  # [250..450)
        memoria.asignar(p3)  # [450..550)
        self.assertEqual(memoria.memoria_libre_total(), 0)

        # Liberamos P1 (150K) y P2 (200K): al ser contiguos deben fusionarse en un hueco de 350K [100..450)
        self.assertTrue(memoria.liberar(p1))
        self.assertTrue(memoria.liberar(p2))

        huecos = memoria.obtener_huecos()
        self.assertEqual(len(huecos), 1)
        self.assertEqual(huecos[0].direccion_inicio, 100)
        self.assertEqual(huecos[0].tamanio, 350)

        # Reutilizamos el espacio fusionado para un proceso P4 de 300K
        p4 = Proceso(id="P4", tamanio=300, tiempo_arribo=3, tiempo_irrupcion=2)
        asignacion_p4 = memoria.asignar(p4)
        self.assertIsNotNone(asignacion_p4)
        assert asignacion_p4 is not None
        self.assertEqual(asignacion_p4.direccion_inicio, 100)
        self.assertEqual(asignacion_p4.tamanio, 300)

        # Queda un hueco de 50K [400..450) y P3 sigue en [450..550)
        self.assertEqual(
            [(p.direccion_inicio, p.tamanio, p.proceso_id) for p in memoria.obtener_particiones()],
            [(100, 300, "P4"), (400, 50, None), (450, 100, "P3")],
        )

    def test_resumen_observable_para_presentacion(self) -> None:
        memoria = GestorMemoria()
        memoria.asignar("P1", 120)

        resumen = memoria.obtener_resumen_memoria()
        self.assertEqual(resumen["memoria_total_kb"], 550)
        self.assertEqual(resumen["memoria_so_kb"], 100)
        self.assertEqual(resumen["memoria_usuario_kb"], 450)
        self.assertEqual(resumen["memoria_ocupada_usuario_kb"], 120)
        self.assertEqual(resumen["memoria_libre_usuario_kb"], 330)


if __name__ == "__main__":
    unittest.main()
