"""Administracion de memoria MVT con estrategia de asignacion Best-Fit."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from proceso import Proceso

MEMORIA_SO_KB = 100
MEMORIA_USUARIO_KB = 450
MEMORIA_TOTAL_KB = MEMORIA_SO_KB + MEMORIA_USUARIO_KB
DIRECCION_INICIO_SO = 0
DIRECCION_INICIO_USUARIO = MEMORIA_SO_KB


def _es_entero_positivo(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def _es_entero_no_negativo(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0


@dataclass(frozen=True)
class ParticionMemoria:
    """Representa una particion ocupada o un hueco libre en la memoria."""

    direccion_inicio: int
    tamanio: int
    proceso_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not _es_entero_no_negativo(self.direccion_inicio):
            raise ValueError(
                "La direccion de inicio de la particion debe ser un entero mayor o igual a 0."
            )
        if not _es_entero_positivo(self.tamanio):
            raise ValueError(
                "El tamanio de la particion debe ser un entero positivo."
            )
        if self.proceso_id is not None:
            id_limpio = str(self.proceso_id).strip()
            if not id_limpio:
                raise ValueError("El ID del proceso en la particion no puede estar vacio.")
            object.__setattr__(self, "proceso_id", id_limpio)

    @property
    def direccion_fin(self) -> int:
        """Direccion limite exclusiva donde termina la particion."""
        return self.direccion_inicio + self.tamanio

    @property
    def libre(self) -> bool:
        """Indica si la particion es un hueco libre."""
        return self.proceso_id is None


class GestorMemoria:
    """Gestiona la memoria de usuario mediante particiones variables (MVT) y Best-Fit.

    La memoria total es de 550K:
        - [0, 100): 100K reservados para el Sistema Operativo.
        - [100, 550): 450K disponibles para procesos de usuario.
    """

    def __init__(
        self,
        memoria_so_kb: int = MEMORIA_SO_KB,
        memoria_usuario_kb: int = MEMORIA_USUARIO_KB,
    ) -> None:
        if not _es_entero_no_negativo(memoria_so_kb):
            raise ValueError("La memoria reservada al SO debe ser un entero no negativo.")
        if not _es_entero_positivo(memoria_usuario_kb):
            raise ValueError("La memoria de usuario debe ser un entero positivo.")

        self._memoria_so_kb = memoria_so_kb
        self._memoria_usuario_kb = memoria_usuario_kb
        self._direccion_inicio_usuario = memoria_so_kb
        self._particiones: List[ParticionMemoria] = [
            ParticionMemoria(
                direccion_inicio=self._direccion_inicio_usuario,
                tamanio=self._memoria_usuario_kb,
                proceso_id=None,
            )
        ]

    @property
    def memoria_so_kb(self) -> int:
        """Tamanio en KB reservado para el sistema operativo."""
        return self._memoria_so_kb

    @property
    def memoria_usuario_kb(self) -> int:
        """Tamanio total en KB de la memoria de usuario."""
        return self._memoria_usuario_kb

    @property
    def memoria_total_kb(self) -> int:
        """Tamanio total en KB de la memoria del sistema (SO + usuario)."""
        return self._memoria_so_kb + self._memoria_usuario_kb

    @property
    def direccion_inicio_usuario(self) -> int:
        """Direccion donde comienza el espacio de memoria de usuario."""
        return self._direccion_inicio_usuario

    def particion_sistema_operativo(self) -> ParticionMemoria:
        """Retorna la particion reservada al Sistema Operativo."""
        return ParticionMemoria(
            direccion_inicio=DIRECCION_INICIO_SO,
            tamanio=self._memoria_so_kb,
            proceso_id="SO",
        )

    def obtener_particiones(self) -> List[ParticionMemoria]:
        """Retorna una copia ordenada de todas las particiones del area de usuario."""
        return list(self._particiones)

    def obtener_huecos(self) -> List[ParticionMemoria]:
        """Retorna la lista de huecos libres actuales en el area de usuario."""
        return [particion for particion in self._particiones if particion.libre]

    def obtener_particiones_ocupadas(self) -> List[ParticionMemoria]:
        """Retorna la lista de particiones asignadas a procesos de usuario."""
        return [particion for particion in self._particiones if not particion.libre]

    def obtener_asignacion(
        self, proceso_o_id: Union[Proceso, str]
    ) -> Optional[ParticionMemoria]:
        """Retorna la particion asignada a un proceso especifico o ``None`` si no reside en memoria."""
        id_buscado = self._extraer_id_proceso(proceso_o_id)
        for particion in self._particiones:
            if particion.proceso_id == id_buscado:
                return particion
        return None

    def memoria_libre_total(self) -> int:
        """Suma total en KB de los huecos libres en el area de usuario."""
        return sum(hueco.tamanio for hueco in self.obtener_huecos())

    def memoria_ocupada_total(self) -> int:
        """Suma total en KB de las particiones ocupadas en el area de usuario."""
        return sum(
            particion.tamanio for particion in self.obtener_particiones_ocupadas()
        )

    def mayor_hueco_libre(self) -> int:
        """Retorna el tamanio en KB del hueco libre mas grande disponible (o 0 si no hay huecos)."""
        huecos = self.obtener_huecos()
        if not huecos:
            return 0
        return max(hueco.tamanio for hueco in huecos)

    def puede_asignar(self, tamanio: int) -> bool:
        """Indica si existe un hueco libre capaz de alojar ``tamanio`` KB."""
        if not _es_entero_positivo(tamanio):
            raise ValueError("El tamanio a consultar debe ser un entero positivo.")
        if tamanio > self._memoria_usuario_kb:
            return False
        return any(
            particion.libre and particion.tamanio >= tamanio
            for particion in self._particiones
        )

    def asignar(
        self,
        proceso_o_id: Union[Proceso, str],
        tamanio: Optional[int] = None,
    ) -> Optional[ParticionMemoria]:
        """Intenta asignar memoria mediante Best-Fit para el proceso indicado.

        Elige el hueco libre mas pequenio en el que entre el proceso. En caso de
        empate de tamanio entre dos huecos libres, selecciona el de menor direccion
        inicial.

        Argumentos:
            proceso_o_id: Instancia de ``Proceso`` o identificador ``str`` del proceso.
            tamanio: Tamanio en KB a asignar (opcional si se recibe un ``Proceso``).

        Retorna:
            La ``ParticionMemoria`` asignada con su direccion inicial y tamanio,
            o ``None`` si no existe un hueco libre suficiente.
        """
        id_proceso, tamanio_requerido = self._extraer_datos_asignacion(
            proceso_o_id, tamanio
        )

        if self.obtener_asignacion(id_proceso) is not None:
            raise ValueError(
                f"El proceso '{id_proceso}' ya tiene una particion de memoria asignada."
            )

        if tamanio_requerido > self._memoria_usuario_kb:
            return None

        indice_mejor_hueco = self._buscar_indice_best_fit(tamanio_requerido)
        if indice_mejor_hueco is None:
            return None

        hueco_seleccionado = self._particiones[indice_mejor_hueco]
        particion_asignada = ParticionMemoria(
            direccion_inicio=hueco_seleccionado.direccion_inicio,
            tamanio=tamanio_requerido,
            proceso_id=id_proceso,
        )

        tamanio_remanente = hueco_seleccionado.tamanio - tamanio_requerido
        if tamanio_remanente == 0:
            self._particiones[indice_mejor_hueco] = particion_asignada
        else:
            hueco_remanente = ParticionMemoria(
                direccion_inicio=particion_asignada.direccion_fin,
                tamanio=tamanio_remanente,
                proceso_id=None,
            )
            self._particiones[indice_mejor_hueco : indice_mejor_hueco + 1] = [
                particion_asignada,
                hueco_remanente,
            ]

        return particion_asignada

    def liberar(self, proceso_o_id: Union[Proceso, str]) -> bool:
        """Libera la particion ocupada por el proceso y fusiona huecos libres contiguos.

        Argumentos:
            proceso_o_id: Instancia de ``Proceso`` o identificador ``str`` del proceso.

        Retorna:
            ``True`` si el proceso tenia memoria asignada y fue liberada;
            ``False`` si el proceso no se encontraba en memoria.
        """
        id_proceso = self._extraer_id_proceso(proceso_o_id)

        for indice, particion in enumerate(self._particiones):
            if particion.proceso_id == id_proceso:
                self._particiones[indice] = ParticionMemoria(
                    direccion_inicio=particion.direccion_inicio,
                    tamanio=particion.tamanio,
                    proceso_id=None,
                )
                self._compactar_huecos_adyacentes()
                return True

        return False

    def obtener_resumen_memoria(self) -> Dict[str, object]:
        """Retorna una instantanea observable del estado de memoria para presentacion."""
        return {
            "memoria_total_kb": self.memoria_total_kb,
            "memoria_so_kb": self._memoria_so_kb,
            "memoria_usuario_kb": self._memoria_usuario_kb,
            "memoria_ocupada_usuario_kb": self.memoria_ocupada_total(),
            "memoria_libre_usuario_kb": self.memoria_libre_total(),
            "particion_so": self.particion_sistema_operativo(),
            "particiones_usuario": self.obtener_particiones(),
            "huecos_libres": self.obtener_huecos(),
            "particiones_ocupadas": self.obtener_particiones_ocupadas(),
        }

    def _buscar_indice_best_fit(self, tamanio_requerido: int) -> Optional[int]:
        candidatos: List[Tuple[int, int, int]] = []
        for indice, particion in enumerate(self._particiones):
            if particion.libre and particion.tamanio >= tamanio_requerido:
                candidatos.append(
                    (particion.tamanio, particion.direccion_inicio, indice)
                )

        if not candidatos:
            return None

        _, _, indice_elegido = min(candidatos)
        return indice_elegido

    def _compactar_huecos_adyacentes(self) -> None:
        if not self._particiones:
            return

        compactadas: List[ParticionMemoria] = [self._particiones[0]]
        for actual in self._particiones[1:]:
            anterior = compactadas[-1]
            if anterior.libre and actual.libre:
                compactadas[-1] = ParticionMemoria(
                    direccion_inicio=anterior.direccion_inicio,
                    tamanio=anterior.tamanio + actual.tamanio,
                    proceso_id=None,
                )
            else:
                compactadas.append(actual)

        self._particiones = compactadas

    @staticmethod
    def _extraer_id_proceso(proceso_o_id: Union[Proceso, str]) -> str:
        if isinstance(proceso_o_id, Proceso):
            return proceso_o_id.id
        if isinstance(proceso_o_id, str):
            id_limpio = proceso_o_id.strip()
            if id_limpio:
                return id_limpio
        raise ValueError("Debe proporcionar un Proceso o un ID de proceso valido.")

    @classmethod
    def _extraer_datos_asignacion(
        cls,
        proceso_o_id: Union[Proceso, str],
        tamanio: Optional[int],
    ) -> Tuple[str, int]:
        if isinstance(proceso_o_id, Proceso):
            tamanio_final = (
                proceso_o_id.tamanio if tamanio is None else tamanio
            )
            if not _es_entero_positivo(tamanio_final):
                raise ValueError("El tamanio del proceso debe ser un entero positivo.")
            return proceso_o_id.id, tamanio_final

        id_proceso = cls._extraer_id_proceso(proceso_o_id)
        if not _es_entero_positivo(tamanio):
            raise ValueError(
                "Debe indicar un tamanio entero positivo al asignar por ID de proceso."
            )
        return id_proceso, int(tamanio)
