"""Planificacion apropiativa SRTF y reloj discreto de la simulacion."""

from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Sequence

from memoria import GestorMemoria
from proceso import Proceso


TIPO_INICIO = "INICIO_EJECUCION"
TIPO_APROPIACION = "APROPIACION"
TIPO_FINALIZACION = "FINALIZACION"
TIPO_CPU_OCIOSA = "CPU_OCIOSA"
TIPO_MEMORIA_LIBERADA = "MEMORIA_LIBERADA"
TIPO_NUEVA_ADMISION = "NUEVA_ADMISION"


@dataclass(frozen=True)
class EventoPlanificador:
    """Describe un cambio relevante producido por el planificador."""

    tiempo: int
    tipo: str
    proceso_id: Optional[str] = None
    detalle: str = ""


class AdministradorAdmision(Protocol):
    """Contrato que HU-03 debe ofrecer al planificador.

    La admision conserva la propiedad de las colas y de las transiciones de
    estado. El planificador solo solicita los cambios que corresponden a SRTF.
    """

    def procesar_arribos(self, tiempo: int) -> Sequence[Proceso]:
        """Procesa los procesos cuyo tiempo de arribo coincide con ``tiempo``."""

    def obtener_listos(self) -> Sequence[Proceso]:
        """Retorna una vista de los procesos que pueden usar la CPU."""

    def enviar_a_ejecucion(self, proceso: Proceso) -> None:
        """Pasa un proceso LISTO a EJECUCION."""

    def devolver_a_listo(self, proceso: Proceso) -> None:
        """Devuelve a LISTO un proceso apropiado."""

    def finalizar(self, proceso: Proceso) -> None:
        """Pasa un proceso en EJECUCION a TERMINADO."""

    def reintentar_suspendidos(self) -> Sequence[Proceso]:
        """Reintenta admitir procesos luego de liberar memoria."""

    def hay_procesos_pendientes(self) -> bool:
        """Indica si quedan procesos sin terminar."""


ObservadorEventos = Callable[[EventoPlanificador], None]


class PlanificadorSRTF:
    """Coordina la CPU con Shortest Remaining Time First apropiativo.

    Convencion temporal: los arribos del instante ``t`` se procesan antes de
    elegir la CPU. Una unidad ejecutada en ``t`` termina en ``t + 1``.

    Desempate: el proceso que ya ocupa la CPU continua si empata en tiempo
    restante con el mejor proceso LISTO. Cuando la CPU esta libre, se elige por
    menor tiempo restante, luego menor tiempo de arribo y finalmente menor ID.
    """

    def __init__(
        self,
        admision: AdministradorAdmision,
        memoria: GestorMemoria,
        observador: Optional[ObservadorEventos] = None,
    ) -> None:
        self.admision = admision
        self.memoria = memoria
        self.observador = observador
        self.reloj = 0
        self.proceso_en_ejecucion: Optional[Proceso] = None
        self.cambios_contexto = 0
        self._cpu_ociosa_informada = False

    @staticmethod
    def seleccionar_srtf(procesos: Sequence[Proceso]) -> Optional[Proceso]:
        """Selecciona en forma determinista el proceso con menor tiempo restante."""
        if not procesos:
            return None

        for proceso in procesos:
            if proceso.tiempo_restante is None or proceso.tiempo_restante <= 0:
                raise ValueError(
                    f"El proceso '{proceso.id}' no tiene tiempo restante positivo."
                )

        return min(
            procesos,
            key=lambda proceso: (
                proceso.tiempo_restante,
                proceso.tiempo_arribo,
                proceso.id,
            ),
        )

    def simular(self) -> None:
        """Ejecuta automaticamente hasta que admision no tenga trabajo pendiente."""
        while self.admision.hay_procesos_pendientes():
            self.avanzar_unidad()

    def avanzar_unidad(self) -> None:
        """Procesa arribos, reevalua SRTF y avanza una unidad discreta."""
        self.admision.procesar_arribos(self.reloj)
        self._reevaluar_cpu()

        if self.proceso_en_ejecucion is None:
            self._informar_cpu_ociosa()
            self.reloj += 1
            return

        self._cpu_ociosa_informada = False
        proceso = self.proceso_en_ejecucion
        if proceso.tiempo_inicio is None:
            proceso.tiempo_inicio = self.reloj

        proceso.tiempo_restante -= 1
        self.reloj += 1

        if proceso.tiempo_restante == 0:
            self._finalizar(proceso)

    def _reevaluar_cpu(self) -> None:
        listos = list(self.admision.obtener_listos())
        elegido = self.seleccionar_srtf(listos)
        actual = self.proceso_en_ejecucion

        if actual is not None:
            if elegido is None or actual.tiempo_restante <= elegido.tiempo_restante:
                return

            self.admision.devolver_a_listo(actual)
            self.admision.enviar_a_ejecucion(elegido)
            self.proceso_en_ejecucion = elegido
            self.cambios_contexto += 1
            self._emitir(
                TIPO_APROPIACION,
                elegido,
                f"{elegido.id} apropia la CPU a {actual.id}.",
            )
            return

        if elegido is not None:
            self.admision.enviar_a_ejecucion(elegido)
            self.proceso_en_ejecucion = elegido
            self.cambios_contexto += 1
            self._emitir(
                TIPO_INICIO,
                elegido,
                f"{elegido.id} ingresa a la CPU.",
            )

    def _finalizar(self, proceso: Proceso) -> None:
        proceso.tiempo_finalizacion = self.reloj
        self.admision.finalizar(proceso)
        self.proceso_en_ejecucion = None
        self._emitir(
            TIPO_FINALIZACION,
            proceso,
            f"{proceso.id} finaliza su ejecucion.",
        )

        if self.memoria.liberar(proceso):
            self._emitir(
                TIPO_MEMORIA_LIBERADA,
                proceso,
                f"Se libera la memoria de {proceso.id}.",
            )

        admitidos = self.admision.reintentar_suspendidos()
        if admitidos:
            ids = ", ".join(proceso_admitido.id for proceso_admitido in admitidos)
            self._emitir(
                TIPO_NUEVA_ADMISION,
                detalle=f"Se admiten desde LISTO_SUSPENDIDO: {ids}.",
            )

    def _informar_cpu_ociosa(self) -> None:
        if not self._cpu_ociosa_informada:
            self._emitir(TIPO_CPU_OCIOSA, detalle="La CPU se encuentra ociosa.")
            self._cpu_ociosa_informada = True

    def _emitir(
        self,
        tipo: str,
        proceso: Optional[Proceso] = None,
        detalle: str = "",
    ) -> None:
        if self.observador is not None:
            self.observador(
                EventoPlanificador(
                    tiempo=self.reloj,
                    tipo=tipo,
                    proceso_id=None if proceso is None else proceso.id,
                    detalle=detalle,
                )
            )
