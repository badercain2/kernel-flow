"""Pruebas unitarias para el modelo Proceso y la carga de archivos CSV (HU1)."""

from pathlib import Path
import tempfile
import unittest

from carga import ErrorCargaProcesos, cargar_procesos_desde_csv
from proceso import ESTADO_NUEVO, Proceso


class TestProceso(unittest.TestCase):
    """Verifica el contrato tecnico del modelo Proceso."""

    def test_creacion_proceso_inicializa_estado_nuevo_y_tiempos(self) -> None:
        proceso = Proceso(id="P1", tamanio=100, tiempo_arribo=0, tiempo_irrupcion=5)

        self.assertEqual(proceso.id, "P1")
        self.assertEqual(proceso.tamanio, 100)
        self.assertEqual(proceso.tiempo_arribo, 0)
        self.assertEqual(proceso.tiempo_irrupcion, 5)
        self.assertEqual(proceso.tiempo_restante, 5)
        self.assertEqual(proceso.estado, ESTADO_NUEVO)
        self.assertIsNone(proceso.tiempo_inicio)
        self.assertIsNone(proceso.tiempo_finalizacion)

    def test_validaciones_basicas_del_modelo(self) -> None:
        with self.assertRaises(ValueError):
            Proceso(id="", tamanio=100, tiempo_arribo=0, tiempo_irrupcion=5)
        with self.assertRaises(ValueError):
            Proceso(id="P1", tamanio=0, tiempo_arribo=0, tiempo_irrupcion=5)
        with self.assertRaises(ValueError):
            Proceso(id="P1", tamanio=100, tiempo_arribo=-1, tiempo_irrupcion=5)
        with self.assertRaises(ValueError):
            Proceso(id="P1", tamanio=100, tiempo_arribo=0, tiempo_irrupcion=0)
        with self.assertRaises(ValueError):
            Proceso(
                id="P1",
                tamanio=100,
                tiempo_arribo=0,
                tiempo_irrupcion=5,
                estado="BLOQUEADO",
            )


class TestCargaProcesos(unittest.TestCase):
    """Verifica los criterios de aceptacion de la HU1 en carga.py."""

    def _crear_csv_temporal(self, contenido: str) -> Path:
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        ruta = Path(directorio.name) / "procesos.csv"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    def test_cargar_archivo_demo_del_repositorio(self) -> None:
        ruta_demo = Path(__file__).resolve().parent.parent / "data" / "procesos_demo.csv"
        procesos = cargar_procesos_desde_csv(ruta_demo)

        self.assertEqual(len(procesos), 6)
        self.assertTrue(all(p.estado == ESTADO_NUEVO for p in procesos))
        self.assertEqual(procesos[0].id, "P1")
        self.assertEqual(procesos[0].tamanio, 120)
        self.assertEqual(procesos[0].tiempo_arribo, 0)
        self.assertEqual(procesos[0].tiempo_irrupcion, 8)
        self.assertEqual(procesos[0].tiempo_restante, 8)

    def test_cargar_un_proceso_valido(self) -> None:
        ruta = self._crear_csv_temporal("P1,64,2,7\n")
        procesos = cargar_procesos_desde_csv(ruta)

        self.assertEqual(len(procesos), 1)
        self.assertEqual(procesos[0].id, "P1")
        self.assertEqual(procesos[0].tamanio, 64)
        self.assertEqual(procesos[0].tiempo_arribo, 2)
        self.assertEqual(procesos[0].tiempo_irrupcion, 7)
        self.assertEqual(procesos[0].estado, ESTADO_NUEVO)

    def test_cargar_diez_procesos_validos_en_el_limite(self) -> None:
        lineas = [f"P{i},{50 + i},{i - 1},{i + 1}" for i in range(1, 11)]
        ruta = self._crear_csv_temporal("\n".join(lineas))

        procesos = cargar_procesos_desde_csv(ruta)

        self.assertEqual(len(procesos), 10)
        self.assertEqual([p.id for p in procesos], [f"P{i}" for i in range(1, 11)])
        self.assertTrue(all(p.estado == ESTADO_NUEVO for p in procesos))

    def test_rechazar_mas_de_diez_procesos(self) -> None:
        lineas = [f"P{i},50,{i - 1},3" for i in range(1, 12)]
        ruta = self._crear_csv_temporal("\n".join(lineas))

        with self.assertRaises(ErrorCargaProcesos) as ctx:
            cargar_procesos_desde_csv(ruta)

        self.assertIn("maximo permitido es 10", str(ctx.exception))

    def test_rechazar_archivo_inexistente(self) -> None:
        with self.assertRaises(ErrorCargaProcesos):
            cargar_procesos_desde_csv("data/archivo_que_no_existe.csv")

    def test_rechazar_archivo_vacio(self) -> None:
        ruta_vacia = self._crear_csv_temporal("   \n\n")
        with self.assertRaises(ErrorCargaProcesos):
            cargar_procesos_desde_csv(ruta_vacia)

    def test_rechazar_archivo_claramente_invalido(self) -> None:
        casos_invalidos = [
            "P1,100,0\n",
            "P1,100,0,5,extra\n",
            "P1,abc,0,5\n",
            "P1,100,0,xyz\n",
            "P1,-50,0,5\n",
            "P1,100,-1,5\n",
            "P1,100,0,0\n",
            ",100,0,5\n",
            "P1,100,0,5\nP1,120,1,4\n",
        ]
        for contenido in casos_invalidos:
            with self.subTest(contenido=contenido.strip()):
                ruta = self._crear_csv_temporal(contenido)
                with self.assertRaises(ErrorCargaProcesos):
                    cargar_procesos_desde_csv(ruta)


if __name__ == "__main__":
    unittest.main()
