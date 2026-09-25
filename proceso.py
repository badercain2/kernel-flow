"""Modelo de dominio para los procesos del simulador KernelFlow."""

from dataclasses import dataclass
from typing import Optional

ESTADO_NUEVO = "NUEVO"
ESTADO_LISTO = "LISTO"
ESTADO_LISTO_SUSPENDIDO = "LISTO_SUSPENDIDO"
ESTADO_EJECUCION = "EJECUCION"
ESTADO_TERMINADO = "TERMINADO"

ESTADOS_VALIDOS = (
    ESTADO_NUEVO,
    ESTADO_LISTO,
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_EJECUCION,
    ESTADO_TERMINADO,
)


def _es_entero(valor: object) -> bool:
    """Verifica que el valor sea un entero puro (excluyendo booleanos)."""
    return isinstance(valor, int) and not isinstance(valor, bool)


@dataclass
class Proceso:
    """Representa un proceso dentro de la simulacion.

    Atributos requeridos por el contrato tecnico:
        id: Identificador unico del proceso.
        tamanio: Tamanio de memoria requerido por el proceso (en KB).
        tiempo_arribo: Instante discreto de llegada al sistema.
        tiempo_irrupcion: Duracion total de rafaga de CPU requerida.
        tiempo_restante: Unidades de CPU pendientes de ejecucion.
        estado: Estado actual del proceso (inicia en ``NUEVO``).
        tiempo_inicio: Instante en que el proceso accede por primera vez a CPU.
        tiempo_finalizacion: Instante en que el proceso completa su ejecucion.
    """

    id: str
    tamanio: int
    tiempo_arribo: int
    tiempo_irrupcion: int
    tiempo_restante: Optional[int] = None
    estado: str = ESTADO_NUEVO
    tiempo_inicio: Optional[int] = None
    tiempo_finalizacion: Optional[int] = None

    def __post_init__(self) -> None:
        if self.id is None:
            raise ValueError("El ID del proceso no puede ser nulo.")
        self.id = str(self.id).strip()
        if not self.id:
            raise ValueError("El ID del proceso no puede estar vacio.")

        if not _es_entero(self.tamanio) or self.tamanio <= 0:
            raise ValueError(
                f"El tamanio del proceso '{self.id}' debe ser un entero positivo."
            )

        if not _es_entero(self.tiempo_arribo) or self.tiempo_arribo < 0:
            raise ValueError(
                f"El tiempo de arribo del proceso '{self.id}' debe ser un entero mayor o igual a 0."
            )

        if not _es_entero(self.tiempo_irrupcion) or self.tiempo_irrupcion <= 0:
            raise ValueError(
                f"El tiempo de irrupcion del proceso '{self.id}' debe ser un entero positivo."
            )

        if self.tiempo_restante is None:
            self.tiempo_restante = self.tiempo_irrupcion
        elif (
            not _es_entero(self.tiempo_restante)
            or self.tiempo_restante < 0
            or self.tiempo_restante > self.tiempo_irrupcion
        ):
            raise ValueError(
                f"El tiempo restante del proceso '{self.id}' debe estar entre 0 y {self.tiempo_irrupcion}."
            )

        if self.estado not in ESTADOS_VALIDOS:
            raise ValueError(
                f"El estado '{self.estado}' no es valido. Estados permitidos: {', '.join(ESTADOS_VALIDOS)}."
            )
