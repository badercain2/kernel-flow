# AGENTS.md

Guia operativa para trabajar en `kernel-flow`, el simulador de procesos y
administracion de memoria del TPI.

Este archivo es la referencia tecnica del repositorio. Si una decision nueva
contradice esta guia, hay que actualizarla junto con el codigo y dejar la
decision documentada en el cambio correspondiente.

## Contexto del proyecto

- Aplicacion de consola desarrollada en Python 3.
- El simulador debe hacerse para sistema operativo Linux.
- Simulador de procesos con planificacion SRTF apropiativa.
- Administracion de memoria MVT sobre 450K de memoria de usuario.
- 100K de memoria quedan reservados para el sistema operativo.
- La asignacion de memoria utiliza Best-Fit.
- Se admiten como maximo 10 procesos de entrada.
- El grado maximo de multiprogramacion es 5.
- Estados requeridos: `NUEVO`, `LISTO`, `LISTO_SUSPENDIDO`, `EJECUCION` y
  `TERMINADO`.
- No se implementan E/S ni estado `BLOQUEADO`.
- La simulacion debe mostrar CPU, memoria, colas, estados y eventos relevantes.
- Todo el codigo, comentarios y documentacion deben escribirse en espanol.

## Estado actual

El repositorio parte de una base minima. Antes de agregar funcionalidad:

1. Mantener la estructura simple y explicita.
2. Definir primero los contratos entre modulos.
3. Agregar un caso CSV reproducible para demostracion.
4. Documentar en `README.md` los comandos reales de ejecucion cuando queden
   definidos.

## Estructura esperada

La implementacion debe conservar responsabilidades separadas:

```text
kernel-flow/
├── main.py
├── proceso.py
├── carga.py
├── memoria.py
├── estados.py
├── admision.py
├── planificador.py
├── presentacion.py
├── estadisticas.py       # Se incorpora en la segunda entrega
├── data/
│   └── procesos_demo.csv
├── tests/
└── README.md
```

Los nombres pueden cambiar solo si existe una razon concreta y se actualizan
las referencias relacionadas. No mezclar logica de memoria, planificacion,
entrada de datos y presentacion en `main.py`.

## Responsabilidad de cada modulo

- `proceso.py`: modelo `Proceso`, datos de entrada, estado actual y tiempos
  necesarios para la simulacion y las estadisticas.
- `carga.py`: lectura y validacion del CSV. Debe rechazar entradas invalidas
  con errores claros y nunca terminar el programa con un traceback evitable.
- `memoria.py`: MVT, Best-Fit, asignacion, liberacion, reutilizacion y estado
  observable de los huecos y particiones.
- `estados.py`: nombres y reglas de transicion de estados. No debe contener
  decisiones propias del algoritmo SRTF.
- `admision.py`: llegada de procesos, limite de multiprogramacion y manejo de
  las colas `NUEVO`, `LISTO` y `LISTO_SUSPENDIDO`.
- `planificador.py`: reloj, seleccion SRTF, apropiacion, cambios de contexto,
  ejecucion y finalizacion.
- `presentacion.py`: salida de consola y eventos visibles. No debe decidir
  asignaciones de memoria ni seleccionar procesos.
- `estadisticas.py`: calculos de espera, retorno, promedios y rendimiento;
  pertenece a la segunda entrega.
- `main.py`: composicion de dependencias y ciclo principal de la aplicacion,
  sin concentrar reglas de negocio.

## Contratos tecnicos minimos

### Proceso

Cada proceso debe conservar, como minimo:

- `id`
- `tamanio`
- `tiempo_arribo`
- `tiempo_irrupcion`
- `tiempo_restante`
- `estado`
- `tiempo_inicio` o los datos equivalentes necesarios
- `tiempo_finalizacion`

Los tiempos deben utilizar una convencion unica en toda la aplicacion. La
unidad de tiempo se considera discreta y el reloj debe avanzar internamente,
sin exigir un `Enter` por cada unidad.

### Memoria

- El rango de usuario debe modelarse como 450K y comenzar despues de los 100K
  reservados al sistema operativo.
- Best-Fit elige el hueco libre mas pequeno en el que entre el proceso.
- Una asignacion debe conservar direccion inicial y tamanio asignado.
- Una liberacion debe permitir reutilizar el espacio posteriormente.
- La presentacion debe consultar el estado de memoria, no reconstruirlo.

### Admisiones y estados

- `EJECUCION + LISTO + LISTO_SUSPENDIDO` nunca puede superar 5.
- La falta de memoria no debe confundirse con falta de cupo de
  multiprogramacion.
- Al liberar memoria, se debe volver a intentar admitir procesos suspendidos
  de acuerdo con una politica determinista.
- No agregar `BLOQUEADO` ni E/S sin una decision explicita del equipo.

### SRTF

- Siempre se selecciona el proceso listo con menor tiempo restante.
- La llegada de un proceso puede provocar apropiacion.
- Los empates deben resolverse de forma determinista y documentarse.
- Una finalizacion debe disparar la liberacion de memoria y un nuevo intento de
  admision.
- La CPU ociosa debe representarse y mostrarse de forma basica.

## Alcance por entrega

### Primera entrega: 06/10

Debe quedar demostrable el nucleo del simulador:

- carga y validacion basica de hasta 10 procesos;
- MVT, 100K para SO, 450K para usuario y Best-Fit;
- asignacion, liberacion y reutilizacion basica de memoria;
- estados, colas y limite de multiprogramacion 5;
- SRTF, apropiacion y cambios de contexto basicos;
- visualizacion de CPU, memoria, colas, estados y eventos importantes;
- integracion de todos los modulos.

No implementar como requisito de esta entrega las estadisticas completas,
robustez exhaustiva, ejecutable definitivo ni documentacion final.

### Segunda entrega: 17/11

Debe completarse:

- tiempo de espera por proceso;
- tiempo de retorno por proceso;
- promedios y rendimiento;
- informe estadistico;
- validaciones y casos limite principales;
- robustez de memoria, admision y SRTF;
- integracion definitiva, HOWTO, ejecutable y paquete final.

Desde el 01/11 se aplica `feature freeze`: solo se corrigen bugs, problemas
de integracion o bloqueos de entrega.

## Flujo de trabajo y ramas

Usar ramas pequenas y enfocadas:

```text
feature/hu01-carga-procesos
feature/hu02-memoria-bestfit
feature/hu03-admision-estados
feature/hu04-srtf-simulacion
feature/final01-estadisticas
```

Reglas:

- No trabajar directamente sobre `main` salvo cambios de documentacion muy
  simples y acordados.
- Una rama debe resolver una tarjeta o un bug concreto.
- Los commits deben ser pequenos y describir el cambio en imperativo, por
  ejemplo: `Implementar asignacion Best-Fit`.
- Antes de integrar, actualizar la rama con los cambios relevantes de `main` y
  resolver conflictos entendiendo ambos lados; nunca sobrescribir cambios de
  otro integrante sin acuerdo.
- Toda integracion debe incluir prueba manual o automatizada del flujo que
  modifica.
- Los bugs encontrados por QA se corrigen en el modulo responsable y vuelven a
  `TESTING` antes de marcarse como terminados.

## Calidad y testing

Cada cambio debe verificarse en el nivel apropiado:

- pruebas unitarias para carga, Best-Fit, liberacion, limites y estadisticas;
- pruebas de integracion para admision, memoria y planificador;
- una simulacion completa de principio a fin para cambios transversales;
- ejecucion en Linux y, cuando este disponible, Windows;
- rutas relativas y archivos CSV externos, nunca rutas personales.

Como minimo deben cubrirse estos escenarios:

- 1 proceso y 10 procesos validos;
- intento de cargar mas de 10 procesos;
- memoria exacta, memoria insuficiente y memoria llena;
- liberacion y reutilizacion de huecos;
- varios huecos para verificar Best-Fit;
- limite de multiprogramacion 5;
- procesos suspendidos que ingresan cuando se libera memoria;
- llegada durante ejecucion, apropiacion, empate y CPU ociosa;
- finalizacion con actualizacion de memoria, colas y estadisticas.

No marcar una funcionalidad como terminada si solo funciona en el caso feliz.

## Presentacion y experiencia de uso

- Los errores para el usuario deben ser claros, breves y accionables.
- La simulacion avanza automaticamente por eventos relevantes; no requiere
  confirmar cada unidad de tiempo.
- No debe ocultarse toda la ejecucion ni imprimirse una salida ilegible sin
  separacion entre eventos.
- En cada actualizacion relevante mostrar, segun corresponda, tiempo actual,
  CPU, `LISTO`, `LISTO_SUSPENDIDO`, estados y memoria.
- Evitar colores, caracteres o dependencias que rompan una consola comun,
  salvo que se verifique compatibilidad.

## Documentacion y entregables

`README.md` debe mantenerse alineado con el estado real e incluir, cuando
existan:

- requisitos de Python y dependencias;
- comando de ejecucion;
- formato del CSV y ejemplo;
- estructura del proyecto;
- instrucciones para ejecutar tests;
- comportamiento esperado y limitaciones conocidas.

El paquete final debe contener codigo fuente, ejecutable, HOWTO, CSV de ejemplo
y dependencias necesarias. Antes de entregarlo, extraer el ZIP en una carpeta
nueva y ejecutar el programa desde cero.

## Decisiones que requieren acuerdo

Consultar al responsable de integracion antes de cambiar:

- el modelo de `Proceso` o los nombres de estados;
- la politica de desempate de SRTF;
- el formato del CSV;
- la representacion de direcciones y huecos de memoria;
- el contrato entre admision, memoria y planificador;
- la estructura de salida que utiliza la demostracion.

Si una implementacion necesita una excepcion, priorizar el comportamiento
correcto y documentar la decision en el PR, issue o commit correspondiente.

## Responsables de referencia

- Programador 1: carga, presentacion y estadisticas.
- Programador 2: memoria MVT y Best-Fit.
- Programador 3: estados, colas y admision.
- Programador 4: SRTF, simulacion e integracion.
- Personas 5, 6 y 7: testing, documentacion, evidencias y video; trabajan como
  equipo de soporte durante las etapas correspondientes.

La responsabilidad indica quien lidera el cambio, no impide que otro integrante
ayude o revise.
