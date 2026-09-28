"""Estados y transiciones permitidas del ciclo de vida de un proceso."""

from proceso import (
    ESTADO_EJECUCION,
    ESTADO_LISTO,
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_NUEVO,
    ESTADO_TERMINADO,
    Proceso,
)


TRANSICIONES_PERMITIDAS = {
    ESTADO_NUEVO: {ESTADO_LISTO, ESTADO_LISTO_SUSPENDIDO},
    ESTADO_LISTO: {ESTADO_EJECUCION},
    ESTADO_LISTO_SUSPENDIDO: {ESTADO_LISTO},
    ESTADO_EJECUCION: {ESTADO_LISTO, ESTADO_TERMINADO},
    ESTADO_TERMINADO: set(),
}


def cambiar_estado(proceso: Proceso, estado_destino: str) -> None:
    """Cambia el estado si la transicion pertenece al ciclo de vida acordado."""
    if estado_destino not in TRANSICIONES_PERMITIDAS.get(proceso.estado, set()):
        raise ValueError(
            f"No se puede pasar el proceso '{proceso.id}' "
            f"de {proceso.estado} a {estado_destino}."
        )
    proceso.estado = estado_destino
