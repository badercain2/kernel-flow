"""Punto de entrada y panel de consola del simulador KernelFlow."""

import argparse
from itertools import zip_longest
import os
from pathlib import Path
import shutil
import sys
import textwrap
from typing import Optional, Sequence

from admision import Admision, ErrorAdmision, GRADO_MAXIMO_MULTIPROGRAMACION
from carga import ErrorCargaProcesos, cargar_procesos
from memoria import GestorMemoria
from planificador import EventoPlanificador, PlanificadorSRTF
from presentacion import PresentacionConsola, seleccionar_archivo_csv
from proceso import ESTADO_TERMINADO, Proceso


DIRECTORIO_PROYECTO = Path(__file__).resolve().parent
RUTA_CSV_PREDETERMINADA = DIRECTORIO_PROYECTO / "data/procesos_demo.csv"
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
        _imprimir_linea_centrada(
            f"{len(self.procesos)} proceso(s) en estado NUEVO, esperando su "
            "tiempo de arribo."
        )

    def mostrar_paso(
        self, eventos: Sequence[EventoPlanificador], tiempo: int, numero: int
    ) -> None:
        """Muestra juntos los cambios observados durante un avance del reloj."""
        ancho = _ancho_terminal()
        print("\n\n" + "#" * ancho)
        _imprimir_linea_centrada(
            f"COMIENZO DEL PASO {numero} | RELOJ: t = {tiempo} ut"
        )
        print("#" * ancho)
        print()
        _imprimir_linea_centrada("EVENTOS DE ESTE PASO")
        lineas_eventos = []
        for evento in eventos:
            lineas_eventos.extend(textwrap.wrap(
                f"- t = {evento.tiempo} | {evento.detalle}",
                width=max(20, min(ancho - 8, 110)),
                subsequent_indent="    ",
            ))
        _imprimir_bloque_centrado(lineas_eventos)
        print("-" * ancho)
        self._mostrar_resumen(tiempo)
        self._mostrar_tablas()
        print(f" FIN DEL PASO {numero} ".center(ancho, "="))

    def mostrar_fin(self, tiempo: int) -> None:
        ancho = _ancho_terminal()
        print("\n" + "#" * ancho)
        _imprimir_linea_centrada(f"SIMULACION FINALIZADA EN t = {tiempo} ut")
        print("#" * ancho)
        _imprimir_linea_centrada(
            f"Memoria de usuario libre: {self.memoria.memoria_libre_total()}K."
        )
        print()
        _imprimir_bloque_centrado(self.lineas_informe(tiempo))

    def _mostrar_resumen(self, tiempo: int) -> None:
        terminados = sum(
            proceso.estado == ESTADO_TERMINADO for proceso in self.procesos
        )
        resumen, listos, suspendidos = self.lineas_resumen(tiempo)
        _imprimir_linea_centrada(resumen)
        _imprimir_linea_centrada(
            f"TERMINADOS: {terminados}/{len(self.procesos)}   "
            "MULTIPROGRAMACION: "
            f"{self.admision.grado_multiprogramacion()}/"
            f"{GRADO_MAXIMO_MULTIPROGRAMACION}"
        )
        print()
        _imprimir_linea_centrada(f"COLA {listos}")
        _imprimir_linea_centrada(f"COLA {suspendidos}")
        _imprimir_linea_centrada("(entre parentesis: tiempo restante en ut)")

    def _mostrar_tablas(self) -> None:
        tabla_procesos = self.tabla_procesos().splitlines()
        tabla_memoria = self.tabla_memoria().splitlines()
        ancho_procesos = len(tabla_procesos[0])
        ancho_memoria = len(tabla_memoria[0])
        ancho_terminal = _ancho_terminal()

        print()
        if self._interactivo and ancho_procesos + ancho_memoria + 3 <= ancho_terminal:
            lineas = [
                "ESTADO DE LOS PROCESOS".ljust(ancho_procesos)
                + "   TABLA DE PARTICIONES (KB)"
            ]
            for izquierda, derecha in zip_longest(
                tabla_procesos, tabla_memoria, fillvalue=""
            ):
                lineas.append(f"{izquierda:<{ancho_procesos}}   {derecha}")
            _imprimir_bloque_centrado(lineas)
        else:
            _imprimir_linea_centrada("ESTADO DE LOS PROCESOS")
            _imprimir_bloque_centrado(tabla_procesos)
            print()
            _imprimir_linea_centrada("TABLA DE PARTICIONES (KB)")
            _imprimir_bloque_centrado(tabla_memoria)

        _imprimir_linea_centrada(self.linea_memoria_libre())


OPCIONES_MENU = (
    (
        "1",
        "Iniciar simulacion con el CSV de prueba",
        "Ejecuta data/procesos_demo.csv: 6 procesos que muestran apropiacion "
        "SRTF, un proceso en LISTO_SUSPENDIDO y la reutilizacion de memoria.",
    ),
    (
        "2",
        "Cargar otro archivo CSV",
        "Abre un explorador para elegir su propio archivo (hasta 10 procesos, "
        "formato: id,tamanio,arribo,irrupcion) y lo simula.",
    ),
    (
        "3",
        "Ver guia rapida",
        "Explica el formato del CSV, las reglas del simulador (MVT, Best-Fit, "
        "SRTF, multiprogramacion 5), los estados y los controles.",
    ),
    ("0", "Salir", "Cierra el simulador."),
)


def _mostrar_menu() -> None:
    ancho = _ancho_terminal()

    try:
        logo = RUTA_LOGO_UTN.read_text(encoding="utf-8").splitlines()
    except OSError:
        logo = []
    if logo:
        margen_logo = min(
            len(linea) - len(linea.lstrip()) for linea in logo if linea.strip()
        )
        _imprimir_bloque_centrado([linea[margen_logo:] for linea in logo])

    print("=" * ancho)
    _imprimir_linea_centrada("K E R N E L F L O W")
    _imprimir_linea_centrada(
        "Simulador de planificacion SRTF y memoria MVT (Best-Fit)"
    )
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
    lineas = []
    ancho_texto = max(30, min(ancho - 10, 72))
    for clave, titulo, descripcion in OPCIONES_MENU:
        lineas.append(f"[{clave}] {titulo}")
        lineas.extend(
            textwrap.wrap(
                descripcion,
                width=ancho_texto,
                initial_indent="    ",
                subsequent_indent="    ",
            )
        )
        lineas.append("")
    _imprimir_bloque_centrado(lineas[:-1])
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
   - tiempo_irrupcion: tiempo de irrupcion (rafaga), mayor que 0.
   Se admiten entre 1 y 10 procesos. Los numeros deben ser enteros.

2. Elegir como iniciar
   [1] Usa el CSV de prueba incluido en data/procesos_demo.csv.
   [2] Abre un explorador para elegir otro archivo CSV.
   [3] Muestra esta guia.
   [0] Cierra el simulador.

3. Que hace el simulador
   - Reserva 100K para el sistema operativo y 450K para procesos.
   - MVT crea particiones variables. Best-Fit asigna el hueco libre
     mas pequeno donde entre cada proceso.
   - Pueden estar admitidos hasta 5 procesos al mismo tiempo
     (EJECUCION + LISTO + LISTO_SUSPENDIDO).
   - SRTF ejecuta el proceso LISTO con menor tiempo restante.
     Si llega otro mas corto, le quita la CPU (apropiacion).
   - Al terminar un proceso, libera su memoria y se vuelve a
     intentar el ingreso de los que esperan.

4. Como leer la pantalla
   Cada paso empieza con "COMIENZO DEL PASO" y termina con
   "FIN DEL PASO". Dentro de cada paso se listan todos los
   cambios de estado ocurridos (llegadas, admisiones,
   suspensiones, apropiaciones y finalizaciones) con su motivo.
   Luego se muestran la CPU, las colas LISTO y LISTO_SUSPENDIDO
   (con el tiempo restante entre parentesis), la tabla de
   procesos y la tabla de particiones de memoria.
   NUEVO espera su llegada o un cupo; LISTO espera la CPU;
   LISTO_SUSPENDIDO espera memoria; EJECUCION usa la CPU;
   TERMINADO ya completo su trabajo. La CPU puede estar OCIOSA.

5. Columnas de la tabla de procesos
   T. Irrupcion: tiempo total de CPU que necesita el proceso.
   T. Ejecutado: tiempo de CPU ya consumido.
   T. Restante: tiempo de CPU que le falta (lo usa SRTF).

6. Informe final
   Al terminar se muestran, por proceso, el tiempo de retorno
   (finalizacion - arribo) y de espera (retorno - irrupcion),
   sus promedios y el rendimiento (trabajos / tiempo total).

7. Controles durante la simulacion
   Espacio, Enter o N: ver el siguiente cambio relevante.
   Q: detener la simulacion y volver al menu.
   El reloj avanza internamente; no hace falta pulsar una tecla
   por cada unidad de tiempo.
============================================================"""
    _imprimir_bloque_centrado(guia.strip("\n").splitlines())


def _limpiar_pantalla() -> None:
    """Borra la pantalla (incluido el menu) al entrar en otra seccion."""
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def _leer_tecla() -> str:
    """Lee una sola tecla sin esperar Enter, en Linux y en Windows."""
    if os.name == "nt":
        import msvcrt

        return msvcrt.getwch()

    import termios
    import tty

    descriptor = sys.stdin.fileno()
    configuracion_anterior = termios.tcgetattr(descriptor)
    try:
        tty.setcbreak(descriptor)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, configuracion_anterior)


def _esperar_avance() -> bool:
    """Espera una tecla; ``q`` permite volver al menu."""
    print(
        "\n" + _prefijo_centrado(
            "[Espacio/Enter] siguiente cambio  [q] volver al menu: "
        ),
        end="",
        flush=True,
    )
    while True:
        tecla = _leer_tecla()
        if tecla in (" ", "\r", "\n", "n", "N"):
            print()
            return True
        if tecla in ("q", "Q", "", "\x1b"):
            print()
            return False


def _menu_interactivo() -> int:
    """Permite elegir el archivo y volver al menu tras la simulacion."""
    while True:
        _limpiar_pantalla()
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
        interactivo = sys.stdin.isatty() and sys.stdout.isatty()
        while True:
            # Los eventos de una finalizacion en t (producidos al ejecutar la
            # unidad t-1) se muestran junto con los arribos del mismo t.
            if admision.hay_procesos_pendientes():
                planificador.procesar_instante()
            if eventos_paso:
                numero_paso += 1
                presentacion.mostrar_paso(
                    eventos_paso, planificador.reloj, numero_paso
                )
                eventos_paso.clear()
                if interactivo and admision.hay_procesos_pendientes():
                    if not _esperar_avance():
                        _imprimir_linea_centrada(
                            f"Simulacion detenida en t = {planificador.reloj}."
                        )
                        return 0
            if not admision.hay_procesos_pendientes():
                break
            planificador.ejecutar_unidad()
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
