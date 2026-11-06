# KernelFlow

Simulador de procesos y memoria por consola para Linux, desarrollado en Python 3.
Carga hasta 10 procesos desde un CSV, asigna 450K de memoria de usuario con
MVT y Best-Fit, y planifica la CPU con SRTF apropiativo. Los primeros 100K
quedan reservados para el sistema operativo.

## Ejecucion

Desde la raiz del proyecto:

```bash
python3 main.py
```

Para usar otro archivo:

```bash
python3 main.py ruta/al/archivo.csv
```

No se requieren paquetes externos de Python. El archivo predeterminado es
`data/procesos_demo.csv`.

El menu muestra el logo de la UTN y una breve descripcion debajo de cada
opcion. Al elegir una opcion se limpia la pantalla:

- `[1]` simula el CSV de prueba `data/procesos_demo.csv`.
- `[2]` abre un explorador de archivos para elegir otro CSV (requiere
  `tkinter` y entorno grafico; al cancelar se vuelve al menu).
- `[3]` muestra la guia rapida: formato del CSV, reglas, estados, columnas,
  informe final y controles.
- `[0]` sale del simulador.

Durante la simulacion, Espacio/Enter avanza al siguiente cambio y `q` vuelve
al menu. Funciona en Linux y tambien en Windows (`py main.py`).

## Formato del CSV

Cada linea contiene `id,tamanio,tiempo_arribo,tiempo_irrupcion`, sin encabezado.
El tamanio se expresa en KB y los tiempos en unidades discretas.

```csv
P1,120,0,8
P2,150,1,4
P3,100,2,9
```

El simulador admite entre 1 y 10 procesos. Un proceso que requiere mas de
450K se rechaza antes de iniciar, porque nunca podria alojarse en memoria.

## Comportamiento

Los estados son `NUEVO`, `LISTO`, `LISTO_SUSPENDIDO`, `EJECUCION` y
`TERMINADO`. Como maximo cinco procesos pueden estar simultaneamente en
`LISTO`, `LISTO_SUSPENDIDO` o `EJECUCION`. Un proceso sin cupo permanece en
`NUEVO`; uno con cupo pero sin hueco de memoria pasa a `LISTO_SUSPENDIDO`.

Los arribos simultaneos se atienden segun el orden del CSV. Al liberar memoria,
se reintentan primero los suspendidos en orden de llegada y luego los nuevos
que esperan cupo. La simulacion avanza sin pedir una tecla por unidad y se
detiene en cada instante con cambios relevantes (llegadas, finalizaciones,
admisiones, apropiaciones o CPU ociosa).

Cada paso empieza con "COMIENZO DEL PASO" y termina con "FIN DEL PASO", y
muestra el estado del sistema en el instante del evento (`t`). Dentro del paso
se informan todas las transiciones con su origen, destino y motivo, por
ejemplo:

- `P5 llega y pasa a LISTO_SUSPENDIDO (requiere 200K y solo hay 0K libres).`
- `P5 permanece en LISTO_SUSPENDIDO (... el mayor hueco contiguo es de 150K (fragmentacion externa)).`
- `P2 apropia la CPU a P1 ... P2 pasa de LISTO a EJECUCION y P1 pasa de EJECUCION a LISTO.`

Las colas muestran el tiempo restante de cada proceso entre parentesis. En la
tabla de procesos, `T. Irrupcion` es el tiempo de irrupcion original,
`T. Ejecutado` el tiempo de CPU ya consumido y `T. Restante` el que falta para
terminar. La tabla de particiones muestra el ID de particion (0 es el SO),
direccion de comienzo, tamanio, proceso asignado y fragmentacion interna, que
en MVT es siempre 0K porque cada particion se crea del tamanio exacto del
proceso.

Al terminar, se presenta el informe estadistico:

- tiempo de retorno = finalizacion - arribo;
- tiempo de espera = retorno - irrupcion (incluye el tiempo en `NUEVO`,
  `LISTO_SUSPENDIDO` y `LISTO`);
- promedios de retorno y espera;
- rendimiento = trabajos terminados / tiempo total de la simulacion.

## Caso de demostracion

`python3 main.py` ejecuta los seis procesos de `data/procesos_demo.csv`. Durante
el recorrido, P2 apropia la CPU en `t = 1`, P5 espera en
`LISTO_SUSPENDIDO` desde `t = 4` (en `t = 13` hay 230K libres pero
fragmentados), P6 apropia la CPU en `t = 6` y P5 ingresa a memoria en
`t = 20`. La ejecucion termina en `t = 31` con los 450K de usuario libres,
retorno promedio de 14.00 ut, espera promedio de 8.83 ut y rendimiento de
0.1935 trabajos por unidad de tiempo.

## Estructura

- `carga.py` y `proceso.py`: lectura y modelo de procesos.
- `memoria.py`: MVT y Best-Fit.
- `estados.py` y `admision.py`: transiciones, cupo y colas.
- `planificador.py`: reloj y SRTF apropiativo.
- `estadisticas.py`: retorno, espera, promedios y rendimiento.
- `presentacion.py`: salida de consola e informe final.
- `main.py`: menu, entrada e integracion de los modulos.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```
