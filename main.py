"""Punto de entrada y menu de consola del simulador KernelFlow."""

import argparse
import os
from pathlib import Path
import sys
import textwrap
from typing import Optional, Sequence

from admision import Admision, ErrorAdmision
from carga import ErrorCargaProcesos, cargar_procesos
from estilo import Estilo, preparar_terminal
from memoria import GestorMemoria
from panel import (
    PanelConsola,
    ancho_terminal as _ancho_terminal,
    centrar_linea as _prefijo_centrado,
    imprimir_bloque as _imprimir_bloque_centrado,
    imprimir_centrado as _imprimir_linea_centrada,
)
from planificador import PlanificadorSRTF
from presentacion import PresentacionConsola, seleccionar_archivo_csv


if getattr(sys, "frozen", False):
    # Ejecutable de PyInstaller: data/ se distribuye junto al ejecutable.
    DIRECTORIO_PROYECTO = Path(sys.executable).resolve().parent
else:
    DIRECTORIO_PROYECTO = Path(__file__).resolve().parent
DIRECTORIO_DATOS = DIRECTORIO_PROYECTO / "data"
RUTA_CSV_PREDETERMINADA = DIRECTORIO_DATOS / "procesos_demo.csv"
RUTA_LOGO_UTN = DIRECTORIO_DATOS / "logo_utn.txt"

# Se define en main() segun la terminal y la opcion --sin-color.
ESTILO = Estilo()


OPCIONES_MENU = (
    (
        "1",
        "Iniciar simulacion con el CSV de prueba",
        "Ejecuta data/procesos_demo.csv: 6 procesos que muestran apropiacion "
        "SRTF, un proceso en LISTO_SUSPENDIDO y la reutilizacion de memoria.",
    ),
    (
        "2",
        "Elegir otro archivo CSV",
        "Lista los lotes de prueba de la carpeta data/ y permite escribir la "
        "ruta de un archivo propio (hasta 10 procesos, formato: "
        "id,tamanio,arribo,irrupcion).",
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
        _imprimir_bloque_centrado(
            [ESTILO.c(linea[margen_logo:], "azul") for linea in logo]
        )

    e = ESTILO
    doble = e.c(e.linea(ancho, doble=True), "cian")
    simple = e.c(e.linea(ancho), "gris")
    print(doble)
    _imprimir_linea_centrada(e.c("K E R N E L F L O W", "negrita", "cian"))
    _imprimir_linea_centrada(
        "Simulador de planificacion SRTF y memoria MVT (Best-Fit)"
    )
    print(doble)
    _imprimir_linea_centrada(e.c("GRUPO 15", "negrita"))
    _imprimir_bloque_centrado([e.c(nombre, "gris") for nombre in (
        "BADER SORAIRE Cain Abel",
        "GONZALEZ Carlos Alfredo",
        "LEIVA ROMERO Agustin Nazareno",
        "SEELAFF Mauricio Guillermo",
        "TORRES Alejandro Valentin",
        "WOLKOWYSKI Braian Leonel",
        "ZURANO LANG Lucas Maximiliano",
    )])
    print(simple)
    lineas = []
    ancho_texto = max(30, min(ancho - 10, 72))
    for clave, titulo, descripcion in OPCIONES_MENU:
        lineas.append(e.c(f"[{clave}]", "amarillo", "negrita") + " " + e.c(titulo, "negrita"))
        lineas.extend(
            e.c(linea, "gris") for linea in textwrap.wrap(
                descripcion,
                width=ancho_texto,
                initial_indent="    ",
                subsequent_indent="    ",
            )
        )
        lineas.append("")
    _imprimir_bloque_centrado(lineas[:-1])
    print(simple)


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
   [2] Lista los CSV de la carpeta data/ para elegir uno por
       numero, o permite escribir la ruta de otro archivo.
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
   Luego se muestran en tablas: los procesos, la memoria
   principal (particiones), la CPU, la cola LISTO (en el orden
   en que SRTF los elegiria) y la cola LISTO_SUSPENDIDO, con el
   tiempo restante y la espera acumulada de cada proceso.
   Si los colores no se ven bien, use la opcion --sin-color.
   NUEVO espera su llegada o un cupo; LISTO espera la CPU;
   LISTO_SUSPENDIDO espera memoria; EJECUCION usa la CPU;
   TERMINADO ya completo su trabajo. La CPU puede estar OCIOSA.

5. Columnas de la tabla de procesos
   T.Irrup.: tiempo de irrupcion (CPU total que necesita).
   T.Ejec.: tiempo de CPU ya consumido.
   T.Rest.: tiempo de CPU que le falta (lo usa SRTF).
   Espera: tiempo en el sistema sin usar la CPU hasta ahora.
   NUEVO*: el proceso ya llego pero espera cupo (maximo 5).

6. Informe final
   Al terminar se muestran, por proceso, el tiempo de retorno
   (finalizacion - arribo), de espera (retorno - irrupcion) y de
   respuesta (primer uso de CPU - arribo), sus promedios y el
   rendimiento (trabajos terminados / tiempo total).

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
    return _esperar_tecla_avance()


def _esperar_tecla_avance() -> bool:
    """Retorna ``True`` para avanzar y ``False`` si se pidio volver al menu."""
    while True:
        tecla = _leer_tecla()
        if tecla in (" ", "\r", "\n", "n", "N"):
            print()
            return True
        if tecla in ("q", "Q", "", "\x1b"):
            print()
            return False


def _contar_procesos(ruta: Path) -> str:
    """Cuenta las filas no vacias de un CSV para mostrarlas en la lista."""
    try:
        with ruta.open(encoding="utf-8-sig") as archivo:
            cantidad = sum(1 for linea in archivo if linea.strip())
    except (OSError, UnicodeDecodeError):
        return "no se puede leer"
    return f"{cantidad} proceso(s)"


def _elegir_csv() -> Optional[Path]:
    """Muestra los CSV de data/ y permite elegir uno o escribir otra ruta.

    No depende de un entorno grafico; el explorador de archivos queda como
    opcion adicional para quien tenga tkinter disponible.
    """
    archivos = sorted(
        ruta for ruta in DIRECTORIO_DATOS.glob("*.csv") if ruta.is_file()
    )
    while True:
        _limpiar_pantalla()
        ancho = _ancho_terminal()
        print("=" * ancho)
        _imprimir_linea_centrada("SELECCIONAR ARCHIVO CSV")
        print("=" * ancho)
        lineas = []
        if archivos:
            ancho_nombre = max(len(ruta.name) for ruta in archivos)
            for numero, ruta in enumerate(archivos, start=1):
                lineas.append(
                    f"[{numero}] {ruta.name:<{ancho_nombre}}  "
                    f"({_contar_procesos(ruta)})"
                )
        else:
            lineas.append(f"No hay archivos CSV en {DIRECTORIO_DATOS}.")
        lineas.extend((
            "",
            "[R] Escribir la ruta de otro archivo CSV",
            "[E] Buscarlo con el explorador de archivos (requiere entorno grafico)",
            "[0] Volver al menu",
        ))
        _imprimir_bloque_centrado(lineas)
        print("-" * ancho)

        opcion = input(_prefijo_centrado("Opcion: ")).strip().lower()
        if opcion == "0":
            return None
        if opcion.isdigit() and 1 <= int(opcion) <= len(archivos):
            return archivos[int(opcion) - 1]
        if opcion == "r":
            texto = input(_prefijo_centrado("Ruta del archivo CSV: "))
            ruta = Path(texto.strip().strip('"').strip("'")).expanduser()
            if ruta.is_file():
                return ruta
            _imprimir_linea_centrada(f"No se encontro el archivo '{ruta}'.")
        elif opcion == "e":
            ruta = seleccionar_archivo_csv(DIRECTORIO_DATOS)
            if ruta is not None:
                return ruta
            _imprimir_linea_centrada("No se selecciono ningun archivo.")
        else:
            _imprimir_linea_centrada("Opcion no valida.")
        input(_prefijo_centrado("Presione Enter para continuar..."))


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
            ruta = _elegir_csv()
            if ruta is None:
                continue
            _limpiar_pantalla()
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
    analizador.add_argument(
        "--sin-color",
        action="store_true",
        help="Muestra la salida sin colores (util si la terminal no los soporta).",
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
    if modo_visual:
        presentacion = PanelConsola(procesos, admision, memoria, ESTILO)
    else:
        presentacion = PresentacionConsola(procesos, admision, memoria)

    presentacion.mostrar_inicio(ruta_csv)

    if modo_visual:
        eventos_paso = []
        planificador = PlanificadorSRTF(admision, memoria, eventos_paso.append)
        numero_paso = 0
        interactivo = sys.stdin.isatty() and sys.stdout.isatty()
        if interactivo:
            print(
                "\n" + _prefijo_centrado(
                    "[Espacio/Enter] comenzar la simulacion  [q] volver al menu: "
                ),
                end="",
                flush=True,
            )
            if not _esperar_tecla_avance():
                return 0
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
    global ESTILO
    opciones = crear_argumentos(argumentos)
    preparar_terminal()
    ESTILO = Estilo.detectar(sin_color=opciones.sin_color)
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
