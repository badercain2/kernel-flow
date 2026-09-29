"""Punto de entrada y panel de consola del simulador KernelFlow para Linux."""

import argparse
from itertools import zip_longest
from pathlib import Path
import shutil
import sys
from typing import Optional, Sequence

from admision import Admision, ErrorAdmision, GRADO_MAXIMO_MULTIPROGRAMACION
from carga import ErrorCargaProcesos, cargar_procesos
from memoria import GestorMemoria
from planificador import EventoPlanificador, PlanificadorSRTF
from presentacion import PresentacionConsola
from proceso import (
    ESTADO_EJECUCION,
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_TERMINADO,
    Proceso,
)


RUTA_CSV_PREDETERMINADA = Path("data/procesos_demo.csv")


def _tabla(encabezados: Sequence[str], filas: Sequence[Sequence[object]]) -> str:
    """Construye una tabla ASCII para una consola Linux comun."""
    celdas = [[str(valor) for valor in fila] for fila in filas]
    anchos = [
        max([len(nombre)] + [len(fila[indice]) for fila in celdas])
        for indice, nombre in enumerate(encabezados)
    ]
    borde = "+" + "+".join("-" * (ancho + 2) for ancho in anchos) + "+"

    def formar_fila(valores: Sequence[str]) -> str:
        return "| " + " | ".join(
            f"{valor:<{ancho}}" for valor, ancho in zip(valores, anchos)
        ) + " |"

    lineas = [borde, formar_fila(encabezados), borde]
    lineas.extend(formar_fila(fila) for fila in celdas)
    lineas.append(borde)
    return "\n".join(lineas)


class PanelConsola(PresentacionConsola):
    """Vista compacta para la ejecucion desde la terminal.

    Los datos siguen perteneciendo a admision, memoria y los procesos. El
    panel solo los consulta; no decide transiciones ni selecciona la CPU.
    """

    def __init__(
        self,
        procesos: Sequence[Proceso],
        admision: Admision,
        memoria: GestorMemoria,
    ) -> None:
        super().__init__(procesos, admision, memoria)
        self._interactivo = sys.stdout.isatty()

    def mostrar_inicio(self, ruta_csv: Path) -> None:
        print(f"\nKernelFlow | Procesos cargados desde: {ruta_csv}")

    def mostrar_evento(self, evento: EventoPlanificador) -> None:
        print("\n" + "=" * 76)
        print(f"t = {evento.tiempo} | {evento.detalle}")
        print("-" * 76)
        self._mostrar_resumen(evento.tiempo)
        self._mostrar_tablas()

    def mostrar_fin(self, tiempo: int) -> None:
        print("-" * 76)
        print(f"Simulacion finalizada en t = {tiempo}.")
        print(f"Memoria de usuario libre: {self.memoria.memoria_libre_total()}K.")

    def _mostrar_resumen(self, tiempo: int) -> None:
        en_cpu = next(
            (proceso for proceso in self.procesos if proceso.estado == ESTADO_EJECUCION),
            None,
        )
        cpu = en_cpu.id if en_cpu is not None else "OCIOSA"
        restante = en_cpu.tiempo_restante if en_cpu is not None else "-"
        terminados = sum(
            proceso.estado == ESTADO_TERMINADO for proceso in self.procesos
        )
        resumen = self.memoria.obtener_resumen_memoria()
        print(
            f"TIEMPO: {tiempo} ut   CPU: {cpu}   RESTANTE: {restante} ut   "
            f"TERMINADOS: {terminados}/{len(self.procesos)}"
        )
        print(
            "MULTIPROGRAMACION: "
            f"{self.admision.grado_multiprogramacion()}/"
            f"{GRADO_MAXIMO_MULTIPROGRAMACION}   "
            f"MEMORIA LIBRE: {resumen['memoria_libre_usuario_kb']}K/"
            f"{self.memoria.memoria_usuario_kb}K"
        )
        print(f"LISTO: {self._formatear_ids(self.admision.obtener_listos())}")
        print(
            "LISTO_SUSPENDIDO: "
            f"{self._formatear_ids(self.admision.obtener_listos_suspendidos())}"
        )

    def _tabla_procesos(self) -> str:
        filas = [
            (
                proceso.id,
                proceso.tiempo_arribo,
                proceso.tamanio,
                proceso.tiempo_restante,
                "L/SUSP."
                if proceso.estado == ESTADO_LISTO_SUSPENDIDO
                else proceso.estado,
            )
            for proceso in self.procesos
        ]
        return _tabla(("ID", "Arribo", "KB", "CPU", "Estado"), filas)

    def _tabla_memoria(self) -> str:
        resumen = self.memoria.obtener_resumen_memoria()
        particiones = [resumen["particion_so"], *resumen["particiones_usuario"]]
        filas = [
            (
                particion.direccion_inicio,
                particion.tamanio,
                particion.proceso_id or "LIBRE",
            )
            for particion in particiones
        ]
        return _tabla(("Inicio", "KB", "Asignado"), filas)

    def _mostrar_tablas(self) -> None:
        tabla_procesos = self._tabla_procesos().splitlines()
        tabla_memoria = self._tabla_memoria().splitlines()
        ancho_procesos = len(tabla_procesos[0])
        ancho_memoria = len(tabla_memoria[0])
        ancho_terminal = shutil.get_terminal_size(fallback=(80, 24)).columns

        if self._interactivo and ancho_procesos + ancho_memoria + 3 <= ancho_terminal:
            print(
                "\n"
                + "PROCESOS CARGADOS".ljust(ancho_procesos)
                + "   MEMORIA PRINCIPAL (KB)"
            )
            for izquierda, derecha in zip_longest(
                tabla_procesos, tabla_memoria, fillvalue=""
            ):
                print(f"{izquierda:<{ancho_procesos}}   {derecha}")
        else:
            print("\nPROCESOS CARGADOS")
            print("\n".join(tabla_procesos))
            print("\nMEMORIA PRINCIPAL (KB)")
            print("\n".join(tabla_memoria))

        resumen = self.memoria.obtener_resumen_memoria()
        print(f"Libre usuario: {resumen['memoria_libre_usuario_kb']}K")


def _mostrar_menu() -> None:
    print("\n" + "=" * 60)
    print("  K E R N E L F L O W")
    print("  Simulador de procesos y memoria para Linux")
    print("=" * 60)
    print("  [1] Ejecutar CSV de demostracion")
    print("  [2] Cargar otro archivo CSV")
    print("  [3] Ver guia rapida")
    print("  [0] Salir")
    print("-" * 60)


def _menu_interactivo() -> int:
    """Permite elegir el archivo; la simulacion avanza automaticamente."""
    while True:
        _mostrar_menu()
        try:
            opcion = input("Opcion: ").strip()
        except EOFError:
            return 0

        if opcion == "0":
            return 0
        if opcion == "1":
            ruta = RUTA_CSV_PREDETERMINADA
        elif opcion == "2":
            ruta_ingresada = input("Ruta del CSV (Enter para volver): ").strip()
            if not ruta_ingresada:
                continue
            ruta = Path(ruta_ingresada.strip('"'))
        elif opcion == "3":
            print("\nCSV: id,tamanio,tiempo_arribo,tiempo_irrupcion (sin encabezado).")
            print("Memoria: 100K para SO y 450K para usuario; Best-Fit.")
            print("CPU: SRTF apropiativo. Multiprogramacion maxima: 5.")
            input("\nPresione Enter para volver al menu...")
            continue
        else:
            print("Opcion no valida.")
            input("Presione Enter para continuar...")
            continue

        ejecutar_simulacion(ruta, modo_visual=True)
        input("\nPresione Enter para volver al menu...")


def crear_argumentos(argumentos: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Interpreta los argumentos de la aplicacion de consola."""
    analizador = argparse.ArgumentParser(
        description="Simulador de procesos con SRTF y memoria MVT Best-Fit."
    )
    analizador.add_argument(
        "archivo",
        nargs="?",
        type=Path,
        default=None,
        help="CSV de procesos (por defecto: data/procesos_demo.csv).",
    )
    return analizador.parse_args(argumentos)


def ejecutar_simulacion(ruta_csv: Path, modo_visual: bool = False) -> int:
    """Compone los modulos del simulador y ejecuta el ciclo principal."""
    try:
        procesos = cargar_procesos(ruta_csv)
    except ErrorCargaProcesos as error:
        print(f"Error: {error}")
        return 1

    memoria = GestorMemoria()
    try:
        admision = Admision(procesos, memoria)
    except ErrorAdmision as error:
        print(f"Error: {error}")
        return 1
    clase_presentacion = PanelConsola if modo_visual else PresentacionConsola
    presentacion = clase_presentacion(procesos, admision, memoria)

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
    try:
        if opciones.archivo is not None:
            return ejecutar_simulacion(opciones.archivo, modo_visual=True)
        if sys.stdin.isatty():
            return _menu_interactivo()
        return ejecutar_simulacion(RUTA_CSV_PREDETERMINADA, modo_visual=True)
    except (EOFError, KeyboardInterrupt):
        print("\nSimulacion interrumpida.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
