"""Salida de consola para los eventos y el estado observable del simulador."""

from pathlib import Path
from typing import Sequence

from memoria import GestorMemoria, ParticionMemoria
from planificador import AdministradorAdmision, EventoPlanificador
from proceso import ESTADO_EJECUCION, Proceso


class PresentacionConsola:
    """Muestra instantaneas cuando ocurre un evento relevante.

    Los estados pertenecen a los procesos, las colas a admision y las
    particiones al gestor de memoria. Esta clase solo consulta esos datos.
    """

    def __init__(
        self,
        procesos: Sequence[Proceso],
        admision: AdministradorAdmision,
        memoria: GestorMemoria,
    ) -> None:
        self.procesos = procesos
        self.admision = admision
        self.memoria = memoria

    def mostrar_inicio(self, ruta_csv: Path) -> None:
        """Informa el archivo cargado antes del primer evento."""
        print(f"KernelFlow | Procesos cargados desde: {ruta_csv}")

    def mostrar_evento(self, evento: EventoPlanificador) -> None:
        """Imprime el evento y una instantanea del sistema en ese momento."""
        print("\n" + "-" * 60)
        print(f"t = {evento.tiempo} | {evento.detalle}")
        self._mostrar_cpu_y_colas()
        self._mostrar_estados()
        self._mostrar_memoria()

    def mostrar_fin(self, tiempo: int) -> None:
        """Cierra la salida al finalizar todos los procesos."""
        print("\n" + "-" * 60)
        print(f"Simulacion finalizada en t = {tiempo}.")

    def _mostrar_cpu_y_colas(self) -> None:
        en_cpu = next(
            (proceso for proceso in self.procesos if proceso.estado == ESTADO_EJECUCION),
            None,
        )
        print(f"CPU: {en_cpu.id if en_cpu is not None else 'OCIOSA'}")
        print(f"LISTO: {self._formatear_ids(self.admision.obtener_listos())}")
        print(
            "LISTO_SUSPENDIDO: "
            f"{self._formatear_ids(self.admision.obtener_listos_suspendidos())}"
        )

    def _mostrar_estados(self) -> None:
        print("ESTADOS:")
        for proceso in self.procesos:
            print(
                f"  {proceso.id}: {proceso.estado} "
                f"(CPU restante: {proceso.tiempo_restante})"
            )

    def _mostrar_memoria(self) -> None:
        print("MEMORIA (KB):")
        print("  Inicio   Tamanio   Proceso")
        resumen = self.memoria.obtener_resumen_memoria()
        particiones = [resumen["particion_so"], *resumen["particiones_usuario"]]
        for particion in particiones:
            self._mostrar_particion(particion)
        print(f"  Libre usuario: {resumen['memoria_libre_usuario_kb']}K")

    @staticmethod
    def _mostrar_particion(particion: ParticionMemoria) -> None:
        ocupante = particion.proceso_id if not particion.libre else "LIBRE"
        print(
            f"  {particion.direccion_inicio:<8} "
            f"{particion.tamanio:<9} {ocupante}"
        )

    @staticmethod
    def _formatear_ids(procesos: Sequence[Proceso]) -> str:
        return ", ".join(proceso.id for proceso in procesos) or "-"
