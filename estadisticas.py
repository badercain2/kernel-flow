"""Calculo del informe estadistico final de la simulacion.

Convenciones (unidades de tiempo discretas, ut):
    - Tiempo de retorno = tiempo de finalizacion - tiempo de arribo.
    - Tiempo de espera  = tiempo de retorno - tiempo de irrupcion.
      Incluye todo el tiempo que el proceso estuvo en el sistema sin usar la
      CPU: en NUEVO esperando cupo, en LISTO_SUSPENDIDO y en LISTO.
    - Rendimiento = trabajos terminados / tiempo total de la simulacion.
      El tiempo total es el instante en que termina el ultimo proceso.
"""

from dataclasses import dataclass
from typing import List, Sequence

from proceso import ESTADO_TERMINADO, Proceso


@dataclass(frozen=True)
class EstadisticaProceso:
    """Tiempos calculados para un proceso terminado."""

    id: str
    tiempo_arribo: int
    tiempo_irrupcion: int
    tiempo_inicio: int
    tiempo_finalizacion: int
    tiempo_retorno: int
    tiempo_espera: int


@dataclass(frozen=True)
class InformeEstadistico:
    """Resumen completo de la simulacion."""

    procesos: List[EstadisticaProceso]
    retorno_promedio: float
    espera_promedio: float
    tiempo_total: int
    trabajos_terminados: int
    rendimiento: float


def calcular_estadisticas(
    procesos: Sequence[Proceso], tiempo_total: int
) -> InformeEstadistico:
    """Calcula retorno, espera, promedios y rendimiento de los terminados."""
    filas: List[EstadisticaProceso] = []
    for proceso in procesos:
        if proceso.estado != ESTADO_TERMINADO or proceso.tiempo_finalizacion is None:
            continue
        retorno = proceso.tiempo_finalizacion - proceso.tiempo_arribo
        filas.append(
            EstadisticaProceso(
                id=proceso.id,
                tiempo_arribo=proceso.tiempo_arribo,
                tiempo_irrupcion=proceso.tiempo_irrupcion,
                tiempo_inicio=proceso.tiempo_inicio,
                tiempo_finalizacion=proceso.tiempo_finalizacion,
                tiempo_retorno=retorno,
                tiempo_espera=retorno - proceso.tiempo_irrupcion,
            )
        )

    cantidad = len(filas)
    retorno_promedio = (
        sum(fila.tiempo_retorno for fila in filas) / cantidad if cantidad else 0.0
    )
    espera_promedio = (
        sum(fila.tiempo_espera for fila in filas) / cantidad if cantidad else 0.0
    )
    rendimiento = cantidad / tiempo_total if tiempo_total > 0 else 0.0

    return InformeEstadistico(
        procesos=filas,
        retorno_promedio=retorno_promedio,
        espera_promedio=espera_promedio,
        tiempo_total=tiempo_total,
        trabajos_terminados=cantidad,
        rendimiento=rendimiento,
    )
