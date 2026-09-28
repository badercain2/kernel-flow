"""Punto de entrada e integracion del simulador KernelFlow para Linux."""

import argparse
from pathlib import Path
from typing import Optional, Sequence

from carga import ErrorCargaProcesos, cargar_procesos
from memoria import GestorMemoria
from planificador import EventoPlanificador, PlanificadorSRTF


RUTA_CSV_PREDETERMINADA = Path("data/procesos_demo.csv")


def crear_argumentos(argumentos: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Interpreta los argumentos de la aplicacion de consola."""
    analizador = argparse.ArgumentParser(
        description="Simulador de procesos con SRTF y memoria MVT Best-Fit."
    )
    analizador.add_argument(
        "archivo",
        nargs="?",
        type=Path,
        default=RUTA_CSV_PREDETERMINADA,
        help="CSV de procesos (por defecto: data/procesos_demo.csv).",
    )
    return analizador.parse_args(argumentos)


def ejecutar_simulacion(ruta_csv: Path) -> int:
    """Compone los modulos del simulador y ejecuta el ciclo principal."""
    try:
        procesos = cargar_procesos(ruta_csv)
    except ErrorCargaProcesos as error:
        print(f"Error: {error}")
        return 1

    from admision import Admision, ErrorAdmision
    from presentacion import PresentacionConsola

    memoria = GestorMemoria()
    try:
        admision = Admision(procesos, memoria)
    except ErrorAdmision as error:
        print(f"Error: {error}")
        return 1
    presentacion = PresentacionConsola(procesos, admision, memoria)

    def mostrar_evento(evento: EventoPlanificador) -> None:
        presentacion.mostrar_evento(evento)

    planificador = PlanificadorSRTF(admision, memoria, mostrar_evento)
    presentacion.mostrar_inicio(ruta_csv)
    planificador.simular()
    presentacion.mostrar_fin(planificador.reloj)
    return 0


def main(argumentos: Optional[Sequence[str]] = None) -> int:
    """Ejecuta KernelFlow y retorna un codigo apto para la consola de Linux."""
    opciones = crear_argumentos(argumentos)
    return ejecutar_simulacion(opciones.archivo)


if __name__ == "__main__":
    raise SystemExit(main())
