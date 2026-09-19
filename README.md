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
