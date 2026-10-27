"""Punto de entrada y panel de consola del simulador KernelFlow para Linux."""

import argparse
from itertools import zip_longest
from pathlib import Path
import shutil
import sys
import termios
import textwrap
import tty
from typing import Optional, Sequence

from admision import Admision, ErrorAdmision, GRADO_MAXIMO_MULTIPROGRAMACION
from carga import ErrorCargaProcesos, cargar_procesos
from memoria import GestorMemoria
from planificador import EventoPlanificador, PlanificadorSRTF
from presentacion import PresentacionConsola, seleccionar_archivo_csv
from proceso import (
    ESTADO_EJECUCION,
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_TERMINADO,
    Proceso,
)


RUTA_CSV_PREDETERMINADA = Path("data/procesos_demo.csv")
DIRECTORIO_PROYECTO = Path(__file__).resolve().parent
RUTA_LOGO_UTN = DIRECTORIO_PROYECTO / "data/logo_utn.txt"


def _ancho_terminal() -> int:
    """Obtiene el ancho disponible para presentar el contenido."""
    return shutil.get_terminal_size(fallback=(100, 24)).columns


def _prefijo_centrado(texto: str) -> str:
    """Agrega espacios a la izquierda sin rellenar el final de la linea."""
    return " " * max(0, (_ancho_terminal() - len(texto)) // 2) + texto


def _imprimir_linea_centrada(texto: str) -> None:
    print(_prefijo_centrado(texto))


def _imprimir_bloque_centrado(lineas: Sequence[str]) -> None:
    """Centra un bloque conservando la alineacion interna de sus lineas."""
    if not lineas:
        return
    ancho_bloque = max(len(linea) for linea in lineas)
    margen = " " * max(0, (_ancho_terminal() - ancho_bloque) // 2)
    for linea in lineas:
        print(margen + linea if linea else "")


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
        print()
        _imprimir_linea_centrada(f"KernelFlow | Procesos cargados desde: {ruta_csv}")

    def mostrar_paso(
        self, eventos: Sequence[EventoPlanificador], tiempo: int, numero: int
    ) -> None:
        """Muestra juntos los cambios observados durante un avance del reloj."""
        ancho = _ancho_terminal()
        print("\n\n" + "=" * ancho)
        print()
        _imprimir_linea_centrada(f"COMIENZO DEL PASO {numero} | RELOJ: {tiempo} ut")
        print()
        print("=" * ancho)
        lineas_eventos = []
        for evento in eventos:
            lineas_eventos.extend(textwrap.wrap(
                f"t = {evento.tiempo} | {evento.detalle}",
                width=max(20, ancho - 8),
                subsequent_indent="    ",
            ))
        _imprimir_bloque_centrado(lineas_eventos)
        print("-" * ancho)
        self._mostrar_resumen(tiempo)
        self._mostrar_tablas()
        print(f" FIN DEL PASO {numero} ".center(ancho, "="))

    def mostrar_fin(self, tiempo: int) -> None:
        print("-" * _ancho_terminal())
        _imprimir_linea_centrada(f"Simulacion finalizada en t = {tiempo}.")
        _imprimir_linea_centrada(
            f"Memoria de usuario libre: {self.memoria.memoria_libre_total()}K."
        )

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
        _imprimir_linea_centrada(
            f"TIEMPO: {tiempo} ut   CPU: {cpu}   RESTANTE: {restante} ut"
        )
        _imprimir_linea_centrada(
            f"TERMINADOS: {terminados}/{len(self.procesos)}   "
            "MULTIPROGRAMACION: "
            f"{self.admision.grado_multiprogramacion()}/"
            f"{GRADO_MAXIMO_MULTIPROGRAMACION}"
        )
        _imprimir_linea_centrada(
            f"MEMORIA LIBRE: {resumen['memoria_libre_usuario_kb']}K/"
            f"{self.memoria.memoria_usuario_kb}K"
        )
        print()
        _imprimir_linea_centrada(
            f"LISTO: {self._formatear_ids(self.admision.obtener_listos())}"
        )
        _imprimir_linea_centrada(
            "LISTO_SUSPENDIDO: "
            f"{self._formatear_ids(self.admision.obtener_listos_suspendidos())}"
        )

    def _tabla_procesos(self) -> str:
        filas = [
            (
                proceso.id,
                proceso.tiempo_arribo,
                proceso.tamanio,
                proceso.tiempo_irrupcion,
                proceso.tiempo_irrupcion - proceso.tiempo_restante,
                proceso.tiempo_restante,
                "L/SUSP."
                if proceso.estado == ESTADO_LISTO_SUSPENDIDO
                else proceso.estado,
            )
            for proceso in self.procesos
        ]
        return _tabla(
            ("ID", "Arribo", "KB", "TI", "Usado", "Restante", "Estado"),
            filas,
        )

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
        ancho_terminal = _ancho_terminal()

        print()
        if self._interactivo and ancho_procesos + ancho_memoria + 3 <= ancho_terminal:
            lineas = [
                "PROCESOS CARGADOS".ljust(ancho_procesos)
                + "   MEMORIA PRINCIPAL (KB)"
            ]
            for izquierda, derecha in zip_longest(
                tabla_procesos, tabla_memoria, fillvalue=""
            ):
                lineas.append(f"{izquierda:<{ancho_procesos}}   {derecha}")
            _imprimir_bloque_centrado(lineas)
        else:
            _imprimir_linea_centrada("PROCESOS CARGADOS")
            _imprimir_bloque_centrado(tabla_procesos)
            print()
            _imprimir_linea_centrada("MEMORIA PRINCIPAL (KB)")
            _imprimir_bloque_centrado(tabla_memoria)

        resumen = self.memoria.obtener_resumen_memoria()
        _imprimir_linea_centrada(
            f"Libre usuario: {resumen['memoria_libre_usuario_kb']}K"
        )


def _mostrar_menu() -> None:
    ancho = _ancho_terminal()

    logo = RUTA_LOGO_UTN.read_text(encoding="utf-8").splitlines()
    margen_logo = min(len(linea) - len(linea.lstrip()) for linea in logo)
    _imprimir_bloque_centrado([linea[margen_logo:] for linea in logo])

    print("=" * ancho)
    _imprimir_linea_centrada("K E R N E L F L O W")
    _imprimir_linea_centrada("Simulador de procesos y memoria para Linux")
    print("=" * ancho)
    _imprimir_linea_centrada("GRUPO 15")
    _imprimir_bloque_centrado((
        "BADER SORAIRE Cain Abel",
        "GONZALEZ Carlos Alfredo",
        "LEIVA ROMERO Agustin Nazareno",
        "SEELAFF Mauricio Guillermo",
        "TORRES Alejandro Valentin",
        "WOLKOWYSKI Braian Leonel",
        "ZURANO LANG Lucas Maximiliano",
    ))
    print("-" * ancho)
    _imprimir_bloque_centrado((
        "[1] Iniciar simulacion SRTF y Best-Fit (CSV de prueba)",
        "[2] Cargar otro archivo CSV",
        "[3] Ver guia rapida",
        "[0] Salir",
    ))
    print("-" * ancho)


def _mostrar_guia_rapida() -> None:
    """Explica la entrada, las reglas y la lectura de la simulacion."""
    guia = """
============================================================
  GUIA RAPIDA DE KERNELFLOW
============================================================
1. Preparar el archivo CSV
   Una fila representa un proceso. No escriba encabezados.
   Formato: id,tamanio,tiempo_arribo,tiempo_irrupcion
   Ejemplo: P1,120,0,8
   - id: nombre unico del proceso.
   - tamanio: memoria requerida en KB, entre 1 y 450.
   - tiempo_arribo: instante de llegada, desde 0.
   - tiempo_irrupcion: unidades de CPU necesarias, mayor que 0.
   Se admiten entre 1 y 10 procesos. Los numeros deben ser enteros.

2. Elegir como iniciar
   [1] Usa el CSV de prueba incluido en data/procesos_demo.csv.
   [2] Abre un explorador para elegir otro archivo CSV.

3. Que hace el simulador
   - Reserva 100K para el sistema operativo y 450K para procesos.
   - MVT crea particiones variables. Best-Fit asigna el hueco libre
     mas pequeno donde entre cada proceso.
   - Pueden estar admitidos hasta 5 procesos al mismo tiempo.
   - SRTF ejecuta el proceso LISTO con menos tiempo de CPU restante.
     Si llega otro mas corto, puede quitarle la CPU (apropiacion).
   - Al terminar un proceso, libera su memoria y se vuelve a
     intentar el ingreso de los que esperan.

4. Como leer la pantalla
   Se muestran el reloj, la CPU, los eventos, las colas LISTO y
   LISTO_SUSPENDIDO, el estado de cada proceso y la memoria.
   NUEVO espera su llegada o un cupo; LISTO espera la CPU;
   LISTO_SUSPENDIDO espera memoria; EJECUCION usa la CPU;
   TERMINADO ya completo su trabajo. La CPU puede estar OCIOSA.

5. Controles durante la simulacion
   Espacio, Enter o N: ver el siguiente cambio relevante.
   Q: detener la simulacion y volver al menu.
   El reloj avanza internamente; no hace falta pulsar una tecla
   por cada unidad de tiempo.
============================================================"""
    _imprimir_bloque_centrado(guia.strip("\n").splitlines())


def _limpiar_pantalla() -> None:
    """Borra la pantalla al entrar en otra seccion desde el menu."""
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="", flush=True)


def _esperar_avance() -> bool:
    """Espera una tecla en Linux; ``q`` permite volver al menu."""
    print(
        "\n" + _prefijo_centrado(
            "[Espacio/Enter] siguiente cambio  [q] volver al menu: "
        ),
        end="",
        flush=True,
    )
    descriptor = sys.stdin.fileno()
    configuracion_anterior = termios.tcgetattr(descriptor)
    try:
        tty.setcbreak(descriptor)
        while True:
            tecla = sys.stdin.read(1)
            if tecla in (" ", "\r", "\n", "n", "N"):
                print()
                return True
            if tecla in ("q", "Q", ""):
                print()
                return False
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, configuracion_anterior)


def _menu_interactivo() -> int:
    """Permite elegir el archivo y volver al menu tras la simulacion."""
    while True:
        _mostrar_menu()
        try:
            opcion = input(_prefijo_centrado("Opcion: ")).strip()
        except EOFError:
            return 0

        if opcion == "0":
            return 0
        if opcion == "1":
            ruta = RUTA_CSV_PREDETERMINADA
            _limpiar_pantalla()
        elif opcion == "2":
            _limpiar_pantalla()
            ruta = seleccionar_archivo_csv(DIRECTORIO_PROYECTO)
            if ruta is None:
                continue
        elif opcion == "3":
            _limpiar_pantalla()
            _mostrar_guia_rapida()
            input("\n" + _prefijo_centrado("Presione Enter para volver al menu..."))
            continue
        else:
            _imprimir_linea_centrada("Opcion no valida.")
            input(_prefijo_centrado("Presione Enter para continuar..."))
            continue

        ejecutar_simulacion(ruta, modo_visual=True)
        input("\n" + _prefijo_centrado("Presione Enter para volver al menu..."))


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
        _imprimir_linea_centrada(f"Error: {error}")
        return 1

    memoria = GestorMemoria()
    try:
        admision = Admision(procesos, memoria)
    except ErrorAdmision as error:
        _imprimir_linea_centrada(f"Error: {error}")
        return 1
    clase_presentacion = PanelConsola if modo_visual else PresentacionConsola
    presentacion = clase_presentacion(procesos, admision, memoria)

    presentacion.mostrar_inicio(ruta_csv)

    if modo_visual:
        eventos_paso = []
        planificador = PlanificadorSRTF(admision, memoria, eventos_paso.append)
        numero_paso = 0
        while admision.hay_procesos_pendientes():
            eventos_paso.clear()
            planificador.avanzar_unidad()
            if eventos_paso:
                numero_paso += 1
                presentacion.mostrar_paso(
                    eventos_paso, planificador.reloj, numero_paso
                )
                if (
                    sys.stdin.isatty()
                    and sys.stdout.isatty()
                    and admision.hay_procesos_pendientes()
                ):
                    if not _esperar_avance():
                        _imprimir_linea_centrada(
                            f"Simulacion detenida en t = {planificador.reloj}."
                        )
                        return 0
    else:
        planificador = PlanificadorSRTF(
            admision, memoria, presentacion.mostrar_evento
        )
        planificador.simular()

    presentacion.mostrar_fin(planificador.reloj)
    return 0


def main(argumentos: Optional[Sequence[str]] = None) -> int:
    """Ejecuta KernelFlow y retorna un codigo apto para la consola de Linux."""
    opciones = crear_argumentos(argumentos)
    try:
        if opciones.archivo is not None:
            return ejecutar_simulacion(opciones.archivo, modo_visual=True)
        if sys.stdin.isatty() and sys.stdout.isatty():
            return _menu_interactivo()
        return ejecutar_simulacion(RUTA_CSV_PREDETERMINADA, modo_visual=True)
    except (EOFError, KeyboardInterrupt):
        print()
        _imprimir_linea_centrada("Simulacion interrumpida.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
