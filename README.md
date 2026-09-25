# KernelFlow

### Operating Systems Process & Memory Management Simulator

KernelFlow is a console-based Operating Systems simulator developed in Python to explore and implement core concepts of **process scheduling, memory management, process lifecycle, and multiprogramming**.

The project simulates how an operating system admits processes, allocates memory, schedules CPU execution, manages process states, and tracks system activity over time.

> 🚧 **Status:** In Development

---

## 🎯 Project Goals

KernelFlow was designed to simulate the complete lifecycle of a process, from its arrival into the system until its termination.

The simulator focuses on:

- Process admission
- Process state management
- Dynamic memory allocation
- CPU scheduling
- Multiprogramming
- Process suspension
- System event visualization
- Performance statistics

---

## ⚙️ Core Features

### Process Management

Processes are loaded from a file containing:

- Process ID
- Process size
- Arrival time
- CPU burst time

The simulator supports a maximum of **10 processes** per execution.

---

### Process States

KernelFlow manages the following process states:

```text
NEW
READY
READY / SUSPENDED
RUNNING
TERMINATED
```

---

# KernelFlow (Español)

### Simulador de Gestión de Procesos y Memoria de Sistemas Operativos

KernelFlow es un simulador de Sistemas Operativos basado en consola, desarrollado en Python 3 para **sistema operativo Linux**, diseñado para explorar e implementar conceptos centrales de **planificación de procesos, administración de memoria, ciclo de vida de procesos y multiprogramación**.

El proyecto simula cómo un sistema operativo admite procesos, asigna memoria dinámica (MVT con Best-Fit), planifica la ejecución de CPU (SRTF apropiativo), gestiona los estados de los procesos y registra la actividad del sistema a lo largo del tiempo.

> 🚧 **Estado:** En desarrollo

---

## 🎯 Objetivos del Proyecto

KernelFlow fue diseñado para simular el ciclo de vida completo de un proceso, desde su arribo al sistema hasta su finalización.

El simulador se enfoca en:

- Admisión de procesos
- Gestión de estados de procesos
- Asignación dinámica de memoria (MVT - Best-Fit)
- Planificación de CPU (SRTF apropiativo)
- Multiprogramación (grado máximo 5)
- Suspensión de procesos (`LISTO_SUSPENDIDO`)
- Visualización de eventos del sistema
- Estadísticas de rendimiento

---

## ⚙️ Características Principales

### Gestión de Procesos

Los procesos se cargan desde un archivo CSV que contiene:

- ID del proceso (`id`)
- Tamaño del proceso en KB (`tamanio`)
- Tiempo de arribo (`tiempo_arribo`)
- Tiempo de irrupción de CPU (`tiempo_irrupcion`)

El simulador admite un máximo de **10 procesos** por ejecución.

Ejemplo de archivo CSV (`data/procesos_demo.csv`), con el orden `id,tamanio,tiempo_arribo,tiempo_irrupcion` sin encabezado:

```csv
P1,120,0,8
P2,150,1,4
P3,100,2,9
```

---

### Estados de los Procesos

KernelFlow gestiona los siguientes estados de proceso:

```text
NUEVO
LISTO
LISTO_SUSPENDIDO
EJECUCION
TERMINADO
```

---

## 🧪 Ejecución de Pruebas

Para ejecutar las pruebas unitarias en Linux:

```bash
python3 -m unittest discover -s tests -v
```

