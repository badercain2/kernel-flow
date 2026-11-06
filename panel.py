"""Panel de consola de la simulacion: tablas con bordes y colores.

Solo consulta el estado de procesos, admision y memoria; no decide
transiciones ni selecciona la CPU.
"""

import re
import shutil
import textwrap
from pathlib import Path
from typing import List, Optional, Sequence

from admision import GRADO_MAXIMO_MULTIPROGRAMACION
from estadisticas import calcular_estadisticas
from estilo import Celda, Estilo, acomodar_en_filas, largo_visible
from memoria import GestorMemoria
from planificador import (
    TIPO_APROPIACION,
    TIPO_ARRIBO,
    TIPO_CPU_OCIOSA,
    TIPO_FINALIZACION,
    TIPO_INICIO,
    TIPO_MEMORIA_LIBERADA,
    TIPO_NUEVA_ADMISION,
    TIPO_SIGUE_SUSPENDIDO,
    AdministradorAdmision,
    EventoPlanificador,
)
from presentacion import PresentacionConsola
from proceso import (
    ESTADO_EJECUCION,
    ESTADO_LISTO,
    ESTADO_LISTO_SUSPENDIDO,
    ESTADO_NUEVO,
    ESTADO_TERMINADO,
    Proceso,
)

COLOR_ESTADO = {
    ESTADO_NUEVO: ("gris",),
    ESTADO_LISTO: ("cian",),
    ESTADO_LISTO_SUSPENDIDO: ("amarillo",),
    ESTADO_EJECUCION: ("verde", "negrita"),
    ESTADO_TERMINADO: ("azul",),
}
NOMBRE_ESTADO = {ESTADO_LISTO_SUSPENDIDO: "LISTO/SUSP."}

# (etiqueta, colores) de cada tipo de evento.
ETIQUETA_EVENTO = {
    TIPO_ARRIBO: ("LLEGADA", ("cian",)),
    TIPO_NUEVA_ADMISION: ("ADMISION", ("verde",)),
    TIPO_SIGUE_SUSPENDIDO: ("SIN MEMORIA", ("amarillo",)),
    TIPO_APROPIACION: ("APROPIACION", ("magenta", "negrita")),
    TIPO_INICIO: ("CPU", ("verde", "negrita")),
    TIPO_FINALIZACION: ("FIN", ("azul", "negrita")),
    TIPO_MEMORIA_LIBERADA: ("MEMORIA", ("azul",)),
    TIPO_CPU_OCIOSA: ("CPU OCIOSA", ("gris",)),
}
ETIQUETA_SUSPENSION = ("SUSPENSION", ("amarillo", "negrita"))
ANCHO_ETIQUETA = max(len(e) for e, _ in ETIQUETA_EVENTO.values()) + 2


def ancho_terminal() -> int:
    return shutil.get_terminal_size(fallback=(120, 30)).columns


def centrar_linea(texto: str) -> str:
    return " " * max(0, (ancho_terminal() - largo_visible(texto)) // 2) + texto


def imprimir_centrado(texto: str) -> None:
    print(centrar_linea(texto))


def imprimir_bloque(lineas: Sequence[str]) -> None:
    """Centra un bloque respetando la alineacion interna de sus lineas."""
    if not lineas:
        return
    ancho_bloque = max(largo_visible(linea) for linea in lineas)
    margen = " " * max(0, (ancho_terminal() - ancho_bloque) // 2)
    for linea in lineas:
        print(margen + linea if linea else "")


class PanelConsola(PresentacionConsola):
    """Vista de la simulacion para la terminal, con tablas y colores."""

    def __init__(
        self,
        procesos: Sequence[Proceso],
        admision: AdministradorAdmision,
        memoria: GestorMemoria,
        estilo: Optional[Estilo] = None,
    ) -> None:
        super().__init__(procesos, admision, memoria)
        self.estilo = estilo if estilo is not None else Estilo.detectar()
        ids = sorted((re.escape(p.id) for p in procesos), key=len, reverse=True)
        self._patron_ids = (
            re.compile(r"(?<![\w])(" + "|".join(ids) + r")(?![\w])") if ids else None
        )

    # ------------------------------------------------------------------
    # Pantallas
    # ------------------------------------------------------------------

    def mostrar_inicio(self, ruta_csv: Path) -> None:
        e = self.estilo
        self._encabezado("PROCESOS CARGADOS", f"Archivo: {ruta_csv.name}")
        imprimir_centrado(
            f"{len(self.procesos)} proceso(s) leido(s) correctamente. Todos "
            "comienzan en " + e.c("NUEVO", "gris") + " y esperan su arribo."
        )
        print()
        imprimir_bloque(self._tabla_procesos(tiempo=None, titulo="Procesos del lote"))
        print()
        imprimir_bloque((
            e.c("Memoria:", "negrita") + " 100K para el SO + 450K para usuario"
            " (particiones variables MVT, Best-Fit)",
            e.c("CPU:", "negrita") + " SRTF apropiativo   "
            + e.c("Multiprogramacion maxima:", "negrita") + " 5",
        ))

    def mostrar_paso(
        self, eventos: Sequence[EventoPlanificador], tiempo: int, numero: int
    ) -> None:
        e = self.estilo
        print("\n")
        self._encabezado(
            f"PASO {numero}",
            f"Reloj: t = {tiempo} ut",
        )
        imprimir_centrado(e.c("EVENTOS DE ESTE PASO", "negrita"))
        imprimir_bloque(self._lineas_eventos(eventos))
        print()
        imprimir_bloque(acomodar_en_filas(
            [
                self._tabla_procesos(tiempo),
                self._tabla_particiones(),
            ],
            ancho_terminal() - 2,
        ))
        print()
        imprimir_bloque(acomodar_en_filas(
            [
                self._tabla_cpu(tiempo),
                self._tabla_listos(tiempo),
                self._tabla_suspendidos(tiempo),
            ],
            ancho_terminal() - 2,
        ))
        print()
        imprimir_centrado(self._barra_estado(tiempo))
        print(e.c(f" FIN DEL PASO {numero} ".center(ancho_terminal(), "─"
                                                     if e.unicode else "-"),
                  "gris"))

    def mostrar_fin(self, tiempo: int) -> None:
        e = self.estilo
        print("\n")
        self._encabezado(
            "SIMULACION FINALIZADA",
            f"t = {tiempo} ut   Memoria de usuario libre: "
            f"{self.memoria.memoria_libre_total()}K",
        )
        informe = calcular_estadisticas(self.procesos, tiempo)
        filas = [
            (
                self._id(fila.id),
                fila.tiempo_arribo,
                fila.tiempo_irrupcion,
                fila.tiempo_inicio,
                fila.tiempo_finalizacion,
                Celda(fila.tiempo_retorno, ("verde",)),
                Celda(fila.tiempo_espera, ("amarillo",)),
                Celda(fila.tiempo_respuesta, ("cian",)),
            )
            for fila in informe.procesos
        ]
        filas.append((
            Celda("PROMEDIO", ("negrita",)), "", "", "", "",
            Celda(f"{informe.retorno_promedio:.2f}", ("verde", "negrita"), ">"),
            Celda(f"{informe.espera_promedio:.2f}", ("amarillo", "negrita"), ">"),
            Celda(f"{informe.respuesta_promedio:.2f}", ("cian", "negrita"), ">"),
        ))
        imprimir_bloque(e.tabla(
            ("ID", "T. Arribo", "T. Irrupcion", "T. Inicio", "T. Final.",
             "T. Retorno", "T. Espera", "T. Respuesta"),
            filas,
            titulo="Informe estadistico por proceso",
        ))
        print()
        resumen = e.tabla(
            ("Metrica", "Valor", "Formula"),
            [
                ("Tiempo de retorno promedio",
                 Celda(f"{informe.retorno_promedio:.2f} ut", ("verde", "negrita")),
                 "T. Finalizacion - T. Arribo"),
                ("Tiempo de espera promedio",
                 Celda(f"{informe.espera_promedio:.2f} ut", ("amarillo", "negrita")),
                 "T. Retorno - T. Irrupcion"),
                ("Tiempo de respuesta promedio",
                 Celda(f"{informe.respuesta_promedio:.2f} ut", ("cian", "negrita")),
                 "Primer uso de CPU - T. Arribo"),
                ("Rendimiento del sistema",
                 Celda(f"{informe.rendimiento:.4f} trab./ut", ("magenta", "negrita")),
                 f"{informe.trabajos_terminados} trabajos / "
                 f"{informe.tiempo_total} ut"),
            ],
            titulo="Resumen",
        )
        imprimir_bloque(resumen)

    # ------------------------------------------------------------------
    # Bloques
    # ------------------------------------------------------------------

    def _encabezado(self, titulo: str, subtitulo: str = "") -> None:
        e = self.estilo
        ancho = ancho_terminal()
        print(e.c(e.linea(ancho, doble=True), "cian"))
        imprimir_centrado(e.c(titulo, "negrita", "blanco"))
        if subtitulo:
            imprimir_centrado(e.c(subtitulo, "cian"))
        print(e.c(e.linea(ancho, doble=True), "cian"))

    def _lineas_eventos(self, eventos: Sequence[EventoPlanificador]) -> List[str]:
        e = self.estilo
        ancho = max(40, min(ancho_terminal() - 6, 118))
        lineas: List[str] = []
        for evento in eventos:
            etiqueta, colores = ETIQUETA_EVENTO.get(evento.tipo, ("EVENTO", ()))
            if "a LISTO_SUSPENDIDO" in evento.detalle and evento.tipo in (
                TIPO_ARRIBO, TIPO_NUEVA_ADMISION
            ):
                etiqueta, colores = ETIQUETA_SUSPENSION
            prefijo = f"t={evento.tiempo:<3} " + f"[{etiqueta}]".ljust(ANCHO_ETIQUETA) + " "
            envueltas = textwrap.wrap(
                evento.detalle,
                width=ancho - len(prefijo),
            ) or [""]
            for indice, texto in enumerate(envueltas):
                texto = self._resaltar_ids(texto)
                if indice == 0:
                    cabeza = (
                        e.c(f"t={evento.tiempo:<3} ", "gris")
                        + e.c(f"[{etiqueta}]".ljust(ANCHO_ETIQUETA), *colores)
                        + " "
                    )
                    lineas.append(cabeza + texto)
                else:
                    lineas.append(" " * len(prefijo) + texto)
        return lineas

    def _tabla_procesos(self, tiempo: Optional[int], titulo: str = "Procesos") -> List[str]:
        filas = []
        hay_sin_cupo = False
        for proceso in self.procesos:
            estado = NOMBRE_ESTADO.get(proceso.estado, proceso.estado)
            if (
                tiempo is not None
                and proceso.estado == ESTADO_NUEVO
                and proceso.tiempo_arribo <= tiempo
            ):
                estado += "*"
                hay_sin_cupo = True
            filas.append((
                self._id(proceso.id),
                proceso.tamanio,
                proceso.tiempo_arribo,
                proceso.tiempo_irrupcion,
                proceso.tiempo_irrupcion - proceso.tiempo_restante,
                Celda(proceso.tiempo_restante,
                      ("negrita",) if proceso.estado == ESTADO_EJECUCION else ()),
                Celda(estado, COLOR_ESTADO.get(proceso.estado, ())),
            ))
        lineas = self.estilo.tabla(
            ("ID", "KB", "Arribo", "T.Irrup.", "T.Ejec.", "T.Rest.", "Estado"),
            filas,
            titulo=titulo,
        )
        nota = "T.Irrup.=irrupcion  T.Ejec.=ejecutado  T.Rest.=restante"
        lineas.append(self.estilo.c(nota, "gris"))
        if hay_sin_cupo:
            lineas.append(self.estilo.c(
                "* llego y espera cupo de multiprogramacion", "gris"
            ))
        return lineas

    def _tabla_particiones(self) -> List[str]:
        resumen = self.memoria.obtener_resumen_memoria()
        filas = []
        for particion in [resumen["particion_so"], *resumen["particiones_usuario"]]:
            if particion.libre:
                proceso, estado, frag = Celda("-", ("gris",)), Celda("Libre", ("verde",)), "-"
            elif particion.proceso_id == "SO":
                proceso, estado, frag = (
                    Celda("SO", ("magenta",)), Celda("Sistema", ("magenta",)), "-"
                )
            else:
                proceso = self._id(particion.proceso_id)
                estado, frag = Celda("Ocupada", ("rojo",)), "0"
            filas.append((
                Celda("-", ("gris",), ">") if particion.numero is None
                else particion.numero,
                particion.direccion_inicio,
                particion.tamanio,
                proceso,
                frag,
                estado,
            ))
        lineas = self.estilo.tabla(
            ("Part.", "Inicio", "Tamanio", "Proceso", "Frag.Int.", "Estado"),
            filas,
            titulo="Memoria principal (KB)",
        )
        huecos = self.memoria.obtener_huecos()
        lineas.append(self.estilo.c(
            f"Libre: {self.memoria.memoria_libre_total()}K en {len(huecos)} "
            f"hueco(s); mayor hueco: {self.memoria.mayor_hueco_libre()}K",
            "gris",
        ))
        return lineas

    def _tabla_cpu(self, tiempo: int) -> List[str]:
        en_cpu = self.proceso_en_cpu()
        if en_cpu is None:
            filas = []
        else:
            filas = [(
                self._id(en_cpu.id),
                en_cpu.tamanio,
                self._numero_particion(en_cpu),
                en_cpu.tiempo_irrupcion - en_cpu.tiempo_restante,
                Celda(en_cpu.tiempo_restante, ("verde", "negrita")),
            )]
        return self.estilo.tabla(
            ("ID", "KB", "Part.", "T.Ejec.", "T.Rest."),
            filas,
            titulo="CPU - EJECUCION",
            color_titulo=("negrita", "verde"),
            vacia="CPU OCIOSA",
        )

    def _tabla_listos(self, tiempo: int) -> List[str]:
        filas = [
            (
                orden,
                self._id(proceso.id),
                proceso.tamanio,
                self._numero_particion(proceso),
                proceso.tiempo_arribo,
                Celda(proceso.tiempo_restante, ("cian",)),
                self._espera_acumulada(proceso, tiempo),
            )
            for orden, proceso in enumerate(self._ordenar_srtf(
                self.admision.obtener_listos()), start=1)
        ]
        return self.estilo.tabla(
            ("Orden", "ID", "KB", "Part.", "Arribo", "T.Rest.", "Espera"),
            filas,
            titulo="Cola LISTO (en memoria)",
            color_titulo=("negrita", "cian"),
            vacia="sin procesos",
        )

    def _tabla_suspendidos(self, tiempo: int) -> List[str]:
        filas = [
            (
                orden,
                self._id(proceso.id),
                proceso.tamanio,
                proceso.tiempo_arribo,
                Celda(proceso.tiempo_restante, ("amarillo",)),
                self._espera_acumulada(proceso, tiempo),
            )
            for orden, proceso in enumerate(
                self.admision.obtener_listos_suspendidos(), start=1)
        ]
        return self.estilo.tabla(
            ("Orden", "ID", "KB", "Arribo", "T.Rest.", "Espera"),
            filas,
            titulo="Cola LISTO_SUSPENDIDO (sin memoria)",
            color_titulo=("negrita", "amarillo"),
            vacia="sin procesos",
        )

    def _barra_estado(self, tiempo: int) -> str:
        e = self.estilo
        en_cpu = self.proceso_en_cpu()
        terminados = sum(p.estado == ESTADO_TERMINADO for p in self.procesos)
        sep = e.c("  |  ", "gris")
        partes = [
            e.c("t = ", "gris") + e.c(f"{tiempo} ut", "negrita"),
            e.c("CPU: ", "gris") + (
                e.c(en_cpu.id, "verde", "negrita") if en_cpu else e.c("OCIOSA", "gris")
            ),
            e.c("Multiprogramacion: ", "gris") + e.c(
                f"{self.admision.grado_multiprogramacion()}/"
                f"{GRADO_MAXIMO_MULTIPROGRAMACION}", "negrita"),
            e.c("Memoria libre: ", "gris") + e.c(
                f"{self.memoria.memoria_libre_total()}K/"
                f"{self.memoria.memoria_usuario_kb}K", "negrita"),
            e.c("Terminados: ", "gris") + e.c(
                f"{terminados}/{len(self.procesos)}", "negrita"),
        ]
        return sep.join(partes)

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------

    def _id(self, proceso_id: str) -> Celda:
        return Celda(proceso_id, ("amarillo",))

    def _resaltar_ids(self, texto: str) -> str:
        if not self.estilo.color or self._patron_ids is None:
            return texto
        return self._patron_ids.sub(
            lambda m: self.estilo.c(m.group(1), "amarillo"), texto
        )

    def _numero_particion(self, proceso: Proceso) -> object:
        particion = self.memoria.obtener_asignacion(proceso)
        if particion is None or particion.numero is None:
            return "-"
        return particion.numero

    @staticmethod
    def _espera_acumulada(proceso: Proceso, tiempo: int) -> int:
        """Tiempo en el sistema sin usar la CPU hasta el instante actual."""
        ejecutado = proceso.tiempo_irrupcion - proceso.tiempo_restante
        return max(0, tiempo - proceso.tiempo_arribo - ejecutado)

    @staticmethod
    def _ordenar_srtf(procesos: Sequence[Proceso]) -> List[Proceso]:
        """Orden en que SRTF los elegiria: menor restante, arribo e ID."""
        return sorted(
            procesos,
            key=lambda p: (p.tiempo_restante, p.tiempo_arribo, p.id),
        )
