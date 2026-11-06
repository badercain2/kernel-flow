"""Salida de consola para los eventos y el estado observable del simulador."""

from pathlib import Path
from typing import List, Optional, Sequence

from estadisticas import InformeEstadistico, calcular_estadisticas
from memoria import GestorMemoria
from planificador import AdministradorAdmision, EventoPlanificador
from proceso import ESTADO_EJECUCION, ESTADO_LISTO_SUSPENDIDO, Proceso


def seleccionar_archivo_csv(directorio_inicial: Path) -> Optional[Path]:
    """Abre un explorador de archivos para elegir un CSV de procesos."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print(
            "No se pudo abrir el explorador: "
            "falta tkinter en esta instalacion de Python."
        )
        return None

    ventana = None
    try:
        ventana = tk.Tk()
        ventana.withdraw()
        ruta = filedialog.askopenfilename(
            parent=ventana,
            title="Seleccionar archivo CSV de procesos",
            initialdir=str(directorio_inicial),
            filetypes=(("Archivos CSV", "*.csv"), ("Todos los archivos", "*")),
        )
        return Path(ruta) if ruta else None
    except (tk.TclError, OSError):
        print(
            "No se pudo abrir el explorador. "
            "Verifique que haya un entorno grafico disponible."
        )
        return None
    finally:
        if ventana is not None:
            ventana.destroy()


def tabla_ascii(encabezados: Sequence[str], filas: Sequence[Sequence[object]]) -> str:
    """Construye una tabla ASCII apta para cualquier consola."""
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


class PresentacionConsola:
    """Muestra instantaneas cuando ocurre un evento relevante.

    Los estados pertenecen a los procesos, las colas a admision y las
    particiones al gestor de memoria. Esta clase solo consulta esos datos.
    """

    def __init__(
        self,
        procesos: Sequence[Proceso],
        admision: AdministradorAdmision,
        memoria: GestorMemoria,
    ) -> None:
        self.procesos = procesos
        self.admision = admision
        self.memoria = memoria

    def mostrar_inicio(self, ruta_csv: Path) -> None:
        """Informa el archivo cargado antes del primer evento."""
        print(f"KernelFlow | Procesos cargados desde: {ruta_csv}")

    def mostrar_evento(self, evento: EventoPlanificador) -> None:
        """Imprime el evento y una instantanea del sistema en ese momento."""
        print("\n" + "-" * 60)
        print(f"t = {evento.tiempo} | {evento.detalle}")
        for linea in self.lineas_resumen(evento.tiempo):
            print(linea)
        print("PROCESOS:")
        print(self.tabla_procesos())
        print("TABLA DE PARTICIONES DE MEMORIA (KB):")
        print(self.tabla_memoria())

    def mostrar_fin(self, tiempo: int) -> None:
        """Cierra la salida y presenta el informe estadistico."""
        print("\n" + "-" * 60)
        print(f"Simulacion finalizada en t = {tiempo}.")
        print(f"Libre usuario: {self.memoria.memoria_libre_total()}K")
        print()
        for linea in self.lineas_informe(tiempo):
            print(linea)

    # ------------------------------------------------------------------
    # Construccion de contenido reutilizable por las distintas vistas.
    # ------------------------------------------------------------------

    def proceso_en_cpu(self) -> Optional[Proceso]:
        return next(
            (proceso for proceso in self.procesos if proceso.estado == ESTADO_EJECUCION),
            None,
        )

    def lineas_resumen(self, tiempo: int) -> List[str]:
        """Estado del procesador y de las colas en el instante actual."""
        en_cpu = self.proceso_en_cpu()
        if en_cpu is None:
            cpu = "CPU: OCIOSA"
        else:
            cpu = (
                f"CPU: {en_cpu.id} (T. restante: {en_cpu.tiempo_restante} ut "
                f"de {en_cpu.tiempo_irrupcion} ut de irrupcion)"
            )
        return [
            f"TIEMPO: {tiempo} ut   {cpu}",
            f"LISTO: {self._formatear_cola(self.admision.obtener_listos())}",
            "LISTO_SUSPENDIDO: "
            f"{self._formatear_cola(self.admision.obtener_listos_suspendidos())}",
        ]

    def tabla_procesos(self) -> str:
        filas = [
            (
                proceso.id,
                proceso.tamanio,
                proceso.tiempo_arribo,
                proceso.tiempo_irrupcion,
                proceso.tiempo_irrupcion - proceso.tiempo_restante,
                proceso.tiempo_restante,
                "L/SUSP."
                if proceso.estado == ESTADO_LISTO_SUSPENDIDO
                else proceso.estado,
            )
            for proceso in self.procesos
        ]
        return tabla_ascii(
            (
                "ID",
                "KB",
                "T. Arribo",
                "T. Irrupcion",
                "T. Ejecutado",
                "T. Restante",
                "Estado",
            ),
            filas,
        )

    def tabla_memoria(self) -> str:
        """Tabla de particiones exigida por la consigna.

        El ID de particion lo asigna memoria al crear cada particion y no
        cambia mientras exista (0 es el SO); los huecos libres se muestran
        con "-". En MVT cada particion se crea del tamanio exacto del
        proceso, por lo que la fragmentacion interna es siempre 0K.
        """
        resumen = self.memoria.obtener_resumen_memoria()
        particiones = [resumen["particion_so"], *resumen["particiones_usuario"]]
        filas = []
        for particion in particiones:
            if particion.libre:
                asignado, fragmentacion = "LIBRE", "-"
            else:
                asignado = particion.proceso_id
                fragmentacion = "-" if particion.proceso_id == "SO" else "0"
            filas.append(
                (
                    "-" if particion.numero is None else particion.numero,
                    particion.direccion_inicio,
                    particion.tamanio,
                    asignado,
                    fragmentacion,
                )
            )
        return tabla_ascii(
            ("ID Part.", "Inicio", "Tamanio", "Proceso", "Frag. Int."),
            filas,
        )

    def linea_memoria_libre(self) -> str:
        huecos = self.memoria.obtener_huecos()
        return (
            f"Libre usuario: {self.memoria.memoria_libre_total()}K en "
            f"{len(huecos)} hueco(s); mayor hueco: "
            f"{self.memoria.mayor_hueco_libre()}K"
        )

    def lineas_informe(self, tiempo: int) -> List[str]:
        """Informe estadistico final: retorno, espera, promedios y rendimiento."""
        informe = calcular_estadisticas(self.procesos, tiempo)
        return formatear_informe(informe).splitlines()

    @staticmethod
    def _formatear_ids(procesos: Sequence[Proceso]) -> str:
        return ", ".join(proceso.id for proceso in procesos) or "-"

    @staticmethod
    def _formatear_cola(procesos: Sequence[Proceso]) -> str:
        """Muestra cada proceso con su tiempo restante entre parentesis."""
        return ", ".join(
            f"{proceso.id}({proceso.tiempo_restante})" for proceso in procesos
        ) or "-"


def formatear_informe(informe: InformeEstadistico) -> str:
    """Convierte el informe estadistico en texto con tablas ASCII."""
    filas = [
        (
            fila.id,
            fila.tiempo_arribo,
            fila.tiempo_irrupcion,
            fila.tiempo_inicio,
            fila.tiempo_finalizacion,
            fila.tiempo_retorno,
            fila.tiempo_espera,
            fila.tiempo_respuesta,
        )
        for fila in informe.procesos
    ]
    filas.append(
        (
            "PROMEDIO",
            "",
            "",
            "",
            "",
            f"{informe.retorno_promedio:.2f}",
            f"{informe.espera_promedio:.2f}",
            f"{informe.respuesta_promedio:.2f}",
        )
    )
    lineas = [
        "INFORME ESTADISTICO FINAL",
        tabla_ascii(
            (
                "ID",
                "T. Arribo",
                "T. Irrupcion",
                "T. Inicio",
                "T. Finalizacion",
                "T. Retorno",
                "T. Espera",
                "T. Respuesta",
            ),
            filas,
        ),
        "T. Inicio    = primer instante en que el proceso usa la CPU",
        "T. Retorno   = T. Finalizacion - T. Arribo",
        "T. Espera    = T. Retorno - T. Irrupcion",
        "T. Respuesta = T. Inicio - T. Arribo",
        "",
        f"Tiempo de retorno promedio:   {informe.retorno_promedio:.2f} ut",
        f"Tiempo de espera promedio:    {informe.espera_promedio:.2f} ut",
        f"Tiempo de respuesta promedio: {informe.respuesta_promedio:.2f} ut",
        (
            f"Rendimiento del sistema: {informe.trabajos_terminados} trabajos / "
            f"{informe.tiempo_total} ut = {informe.rendimiento:.4f} "
            "trabajos por unidad de tiempo"
        ),
    ]
    return "\n".join(lineas)
