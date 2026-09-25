### Historia de usuario

```
Como usuario del simulador,
quiero cargar procesos desde un archivo,
para utilizar esos procesos durante la simulación.
```

### Criterios de aceptación

```
- Leer ID.
- Leer tamaño.
- Leer tiempo de arribo.
- Leer tiempo de irrupción.
- Permitir máximo 10 procesos.
- Cada proceso comienza como NUEVO.
```

La consigna exige esos cuatro datos y establece un máximo de diez procesos.

‌

### Para esta entrega alcanza con

```
Archivo válido → funciona
Archivo claramente inválido → no rompe el programa
Más de 10 procesos → no permite
```

Los casos límite exhaustivos quedan para noviembre.

### Archivos

```
proceso.py
carga.py
```

### Rama

```
feature/hu01-carga-procesos
```