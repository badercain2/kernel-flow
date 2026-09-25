"""Modulo de lectura y validacion de procesos desde archivos CSV."""

import csv
from pathlib import Path
from typing import List, Sequence, Union

from proceso import ESTADO_NUEVO, Proceso

MAX_PROCESOS = 10
COLUMNAS_ESPERADAS = ("id", "tamanio", "tiempo_arribo", "tiempo_irrupcion")


class ErrorCargaProcesos(ValueError):
    """Error controlado durante la lectura o validacion del archivo de procesos."""


def _es_fila_vacia(fila: Sequence[str]) -> bool:
    return not fila or all(celda.strip() == "" for celda in fila)


def _parsear_entero(valor: str, nombre_campo: str, numero_linea: int) -> int:
    texto = valor.strip()
    if not texto:
        raise ErrorCargaProcesos(
            f"Linea {numero_linea}: el campo '{nombre_campo}' esta vacio."
        )
    try:
        return int(texto)
    except ValueError as exc:
        raise ErrorCargaProcesos(
            f"Linea {numero_linea}: el campo '{nombre_campo}' ('{texto}') debe ser un numero entero."
        ) from exc


def cargar_procesos_desde_csv(ruta_archivo: Union[str, Path]) -> List[Proceso]:
    """Lee y valida un archivo CSV sin encabezado devolviendo los procesos en estado NUEVO.

    Cada fila debe tener el formato: ``id,tamanio,tiempo_arribo,tiempo_irrupcion``.

    Argumentos:
        ruta_archivo: Ruta al archivo CSV a cargar.

    Retorna:
        Lista de instancias ``Proceso`` validadas (entre 1 y ``MAX_PROCESOS``).

    Excepciones:
        ErrorCargaProcesos: Si el archivo no existe, no puede leerse, tiene formato
            invalido, datos fuera de rango o supera los 10 procesos permitidos.
    """
    if ruta_archivo is None or str(ruta_archivo).strip() == "":
        raise ErrorCargaProcesos("Debe especificar una ruta de archivo CSV valida.")

    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise ErrorCargaProcesos(f"No se encontro el archivo '{ruta}'.")
    if not ruta.is_file():
        raise ErrorCargaProcesos(f"La ruta '{ruta}' no corresponde a un archivo.")

    try:
        with ruta.open(mode="r", encoding="utf-8-sig", newline="") as archivo:
            lector = csv.reader(archivo)
            filas_datos = [
                (numero_linea, fila)
                for numero_linea, fila in enumerate(lector, start=1)
                if not _es_fila_vacia(fila)
            ]
    except UnicodeDecodeError as exc:
        raise ErrorCargaProcesos(
            f"El archivo '{ruta}' no tiene una codificacion de texto UTF-8 valida."
        ) from exc
    except (OSError, csv.Error) as exc:
        raise ErrorCargaProcesos(
            f"No se pudo leer el archivo CSV '{ruta}': {exc}"
        ) from exc

    if not filas_datos:
        raise ErrorCargaProcesos(f"El archivo '{ruta}' esta vacio.")

    if len(filas_datos) > MAX_PROCESOS:
        raise ErrorCargaProcesos(
            f"El archivo contiene {len(filas_datos)} procesos, pero el maximo permitido es {MAX_PROCESOS}."
        )

    procesos: List[Proceso] = []
    ids_vistos = set()

    for numero_linea, fila in filas_datos:
        if len(fila) != len(COLUMNAS_ESPERADAS):
            raise ErrorCargaProcesos(
                f"Linea {numero_linea}: se esperaban 4 columnas "
                f"({', '.join(COLUMNAS_ESPERADAS)}), pero se encontraron {len(fila)}."
            )

        id_crudo, tamanio_crudo, arribo_crudo, irrupcion_cruda = fila
        id_proceso = id_crudo.strip()
        if not id_proceso:
            raise ErrorCargaProcesos(
                f"Linea {numero_linea}: el campo 'id' no puede estar vacio."
            )
        if id_proceso in ids_vistos:
            raise ErrorCargaProcesos(
                f"Linea {numero_linea}: el ID de proceso '{id_proceso}' esta duplicado."
            )

        tamanio = _parsear_entero(tamanio_crudo, "tamanio", numero_linea)
        tiempo_arribo = _parsear_entero(arribo_crudo, "tiempo_arribo", numero_linea)
        tiempo_irrupcion = _parsear_entero(
            irrupcion_cruda, "tiempo_irrupcion", numero_linea
        )

        try:
            proceso = Proceso(
                id=id_proceso,
                tamanio=tamanio,
                tiempo_arribo=tiempo_arribo,
                tiempo_irrupcion=tiempo_irrupcion,
                estado=ESTADO_NUEVO,
            )
        except ValueError as exc:
            raise ErrorCargaProcesos(f"Linea {numero_linea}: {exc}") from exc

        ids_vistos.add(id_proceso)
        procesos.append(proceso)

    return procesos


cargar_procesos = cargar_procesos_desde_csv
