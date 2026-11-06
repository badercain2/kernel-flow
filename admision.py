"""Llegadas, colas y admision de procesos con grado maximo cinco."""

from dataclasses import dataclass
from typing import List, Optional, Sequence

from estados import cambiar_estado
from memoria import GestorMemoria
from proceso import (
    ESTADO_EJECUCION,
    ESTADO_LISTO,
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_NUEVO,
    ESTADO_TERMINADO,
    Proceso,
)


GRADO_MAXIMO_MULTIPROGRAMACION = 5


class ErrorAdmision(ValueError):
    """Indica que la entrada no permite iniciar una simulacion valida."""


@dataclass(frozen=True)
class Transicion:
    """Registro de un intento de admision y su resultado.

    Si ``origen`` y ``destino`` coinciden, el proceso no cambio de estado
    (por ejemplo, un suspendido que todavia no entra en memoria) y ``motivo``
    explica por que.
    """

    proceso: Proceso
    origen: str
    destino: str
    motivo: str


class Admision:
    """Administra el cupo, la residencia en memoria y las colas de procesos.

    Los arribos se atienden por tiempo y, ante empate, por orden de entrada.
    Cuando se libera memoria, los suspendidos se reintentan en orden FIFO antes
    de admitir procesos NUEVO que esperan un cupo de multiprogramacion.
    """

    def __init__(self, procesos: Sequence[Proceso], memoria: GestorMemoria) -> None:
        self.procesos = list(procesos)
        self.memoria = memoria
        self._sin_arribar = sorted(
            enumerate(self.procesos),
            key=lambda item: (item[1].tiempo_arribo, item[0]),
        )
        self._nuevos_pendientes: List[Proceso] = []
        self._listos: List[Proceso] = []
        self._suspendidos: List[Proceso] = []
        self._en_ejecucion: Optional[Proceso] = None
        self._transiciones: List[Transicion] = []

        ids = set()
        for proceso in self.procesos:
            if proceso.id in ids:
                raise ErrorAdmision(f"El ID '{proceso.id}' esta repetido.")
            ids.add(proceso.id)
            if proceso.estado != ESTADO_NUEVO:
                raise ErrorAdmision(
                    f"El proceso '{proceso.id}' debe comenzar en estado NUEVO."
                )
            if proceso.tamanio > memoria.memoria_usuario_kb:
                raise ErrorAdmision(
                    f"El proceso '{proceso.id}' requiere {proceso.tamanio}K, "
                    f"pero la memoria de usuario tiene {memoria.memoria_usuario_kb}K."
                )

    def procesar_arribos(self, tiempo: int) -> List[Proceso]:
        """Registra los arribos hasta ``tiempo`` y admite los que tienen cupo."""
        arribados: List[Proceso] = []
        while self._sin_arribar and self._sin_arribar[0][1].tiempo_arribo <= tiempo:
            _, proceso = self._sin_arribar.pop(0)
            self._nuevos_pendientes.append(proceso)
            arribados.append(proceso)
        self._admitir_nuevos()
        return arribados

    def extraer_transiciones(self) -> List[Transicion]:
        """Retorna y vacia las transiciones de admision registradas."""
        transiciones = self._transiciones
        self._transiciones = []
        return transiciones

    def obtener_nuevos(self) -> List[Proceso]:
        """Retorna los procesos en NUEVO, incluidos los que aun no arribaron."""
        return list(self._nuevos_pendientes) + [
            proceso for _, proceso in self._sin_arribar
        ]

    def obtener_listos(self) -> List[Proceso]:
        """Retorna una copia de la cola LISTO en su orden actual."""
        return list(self._listos)

    def obtener_listos_suspendidos(self) -> List[Proceso]:
        """Retorna una copia de la cola LISTO_SUSPENDIDO en orden FIFO."""
        return list(self._suspendidos)

    def grado_multiprogramacion(self) -> int:
        """Cuenta EJECUCION, LISTO y LISTO_SUSPENDIDO."""
        return len(self._listos) + len(self._suspendidos) + int(
            self._en_ejecucion is not None
        )

    def enviar_a_ejecucion(self, proceso: Proceso) -> None:
        """Mueve un proceso LISTO a la CPU seleccionada por el planificador."""
        if self._en_ejecucion is not None:
            raise ValueError("La CPU ya tiene un proceso en EJECUCION.")
        if proceso not in self._listos:
            raise ValueError(f"El proceso '{proceso.id}' no esta en LISTO.")
        cambiar_estado(proceso, ESTADO_EJECUCION)
        self._listos.remove(proceso)
        self._en_ejecucion = proceso

    def devolver_a_listo(self, proceso: Proceso) -> None:
        """Devuelve a LISTO el proceso cuya CPU fue apropiada."""
        if proceso is not self._en_ejecucion:
            raise ValueError(f"El proceso '{proceso.id}' no esta en EJECUCION.")
        cambiar_estado(proceso, ESTADO_LISTO)
        self._en_ejecucion = None
        self._listos.append(proceso)

    def finalizar(self, proceso: Proceso) -> None:
        """Pasa a TERMINADO el proceso que completo su tiempo de CPU."""
        if proceso is not self._en_ejecucion:
            raise ValueError(f"El proceso '{proceso.id}' no esta en EJECUCION.")
        cambiar_estado(proceso, ESTADO_TERMINADO)
        self._en_ejecucion = None

    def reintentar_suspendidos(self) -> List[Proceso]:
        """Reintenta suspendidos y ocupa cupos liberados con procesos NUEVO."""
        admitidos: List[Proceso] = []
        for proceso in list(self._suspendidos):
            if self._intentar_cargar(proceso, ESTADO_LISTO_SUSPENDIDO):
                self._suspendidos.remove(proceso)
                self._listos.append(proceso)
                admitidos.append(proceso)
        admitidos.extend(self._admitir_nuevos())
        return admitidos

    def hay_procesos_pendientes(self) -> bool:
        """Indica si falta completar al menos un proceso de la entrada."""
        return any(proceso.estado != ESTADO_TERMINADO for proceso in self.procesos)

    def _admitir_nuevos(self) -> List[Proceso]:
        admitidos: List[Proceso] = []
        while (
            self._nuevos_pendientes
            and self.grado_multiprogramacion() < GRADO_MAXIMO_MULTIPROGRAMACION
        ):
            proceso = self._nuevos_pendientes.pop(0)
            if self._intentar_cargar(proceso, ESTADO_NUEVO):
                self._listos.append(proceso)
                admitidos.append(proceso)
            else:
                self._suspendidos.append(proceso)
        return admitidos

    def _intentar_cargar(self, proceso: Proceso, origen: str) -> bool:
        """Intenta asignar memoria Best-Fit y registra el resultado.

        Retorna ``True`` si el proceso paso a LISTO. Si no hay hueco, un
        proceso NUEVO pasa a LISTO_SUSPENDIDO y uno suspendido permanece alli.
        """
        mayor_hueco = self.memoria.mayor_hueco_libre()
        libre_total = self.memoria.memoria_libre_total()
        huecos = [hueco.tamanio for hueco in self.memoria.obtener_huecos()]
        particion = self.memoria.asignar(proceso)

        if particion is not None:
            cambiar_estado(proceso, ESTADO_LISTO)
            motivo = (
                f"Best-Fit crea la particion {particion.numero} de "
                f"{particion.tamanio}K en "
                f"[{particion.direccion_inicio}K - {particion.direccion_fin}K)"
            )
            if len(huecos) > 1:
                motivo += (
                    "; elige el hueco mas chico donde entra entre: "
                    + ", ".join(f"{tamanio}K" for tamanio in huecos)
                )
            self._transiciones.append(
                Transicion(proceso, origen, ESTADO_LISTO, motivo)
            )
            return True

        if libre_total >= proceso.tamanio:
            motivo = (
                f"requiere {proceso.tamanio}K; hay {libre_total}K libres pero "
                f"el mayor hueco contiguo es de {mayor_hueco}K "
                "(fragmentacion externa)"
            )
        else:
            motivo = (
                f"requiere {proceso.tamanio}K y solo hay {libre_total}K libres"
            )
        if origen != ESTADO_LISTO_SUSPENDIDO:
            cambiar_estado(proceso, ESTADO_LISTO_SUSPENDIDO)
        self._transiciones.append(
            Transicion(proceso, origen, ESTADO_LISTO_SUSPENDIDO, motivo)
        )
        return False
