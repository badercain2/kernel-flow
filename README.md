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

No se requieren dependencias externas. El archivo predeterminado es
`data/procesos_demo.csv`.

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
que esperan cupo. La simulacion avanza sin pedir una tecla por unidad y muestra
los eventos relevantes, CPU, colas, estados y particiones de memoria.

## Caso de demostracion

`python3 main.py` ejecuta los seis procesos de `data/procesos_demo.csv`. Durante
el recorrido, P2 apropia la CPU en `t = 1`, P5 espera en
`LISTO_SUSPENDIDO` desde `t = 4`, P6 apropia la CPU en `t = 6` y P5
ingresa a memoria en `t = 20`. La ejecucion termina en `t = 31` con los
450K de usuario libres. Este caso sirve como version candidata para la
revision de QA en Linux.

## Estructura

- `carga.py` y `proceso.py`: lectura y modelo de procesos.
- `memoria.py`: MVT y Best-Fit.
- `estados.py` y `admision.py`: transiciones, cupo y colas.
- `planificador.py`: reloj y SRTF apropiativo.
- `presentacion.py`: salida de consola.
- `main.py`: entrada e integracion de los modulos.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Las estadisticas de espera, retorno, promedios y rendimiento pertenecen a la
segunda entrega y todavia no se muestran.
