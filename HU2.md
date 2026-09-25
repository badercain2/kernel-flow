Título para Trello

```
HU-02 | Asignar memoria utilizando MVT y Best-Fit | PROGRAMADOR 2
```

### Historia de usuario

```
Como sistema operativo simulado,
quiero asignar memoria mediante MVT y Best-Fit,
para alojar correctamente los procesos.
```

### Este TPI usa **MVT sobre 450K de usuario + Best-Fit**.

### Para la entrega final dejamos

```
[ ] Casos muy complejos de fragmentación
[ ] Pruebas exhaustivas con muchos huecos
[ ] Robustez ante muchas secuencias de asignación/liberación
[ ] Validación exhaustiva de todas las direcciones
```

Pero para el 06/10 sí tiene que funcionar:

```
Asignar
   ↓
Liberar
   ↓
Reutilizar memoria
```

### Archivo

```
memoria.py
```

### Rama

```
feature/hu02-memoria-bestfit
```