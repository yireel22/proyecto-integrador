# Simulador de Gestor de Procesos

## Descripción del Proyecto
Este proyecto es un simulador de gestor de procesos que implementa diferentes algoritmos de planificación de procesos en un sistema operativo. El simulador permite crear, ejecutar, suspender y terminar procesos, además de gestionar recursos del sistema y comunicación entre procesos.

## Características principales
- Implementación de algoritmos de planificación: FCFS, SJF, Round Robin y Prioridades
- Gestión de recursos del sistema (CPU y memoria)
- Comunicación entre procesos mediante mensajes
- Simulación de productor-consumidor con memoria compartida
- Detección básica de interbloqueos
- Interfaz de usuario interactiva

## Información académica
- **Materia:** Sistemas Operativos
- **Universidad:** Universidad Autónoma de Tamaulipas
- **Semestre:** 6to Semestre
- **Profesor:** Muñoz Quintero Dante Adolfo

## Integrantes del equipo
- Andrade Nieto Isaac Yireel
-
-
- García Salas Yahir Misael
- Cruz Hernández Kevin Efrén

## Requisitos del sistema
- Python 3.x
- Librerías estándar de Python (queue, threading, enum, collections, os, time)

## Instrucciones de uso
1. Ejecutar el archivo principal con Python: `python simulador_procesos.py`
2. Seleccionar el algoritmo de planificación deseado
3. Utilizar el menú interactivo para gestionar los procesos
4. Opción 'G' en el menú para ver información de los integrantes

## Algoritmos implementados
1. **FCFS (First Come, First Served):** Ejecuta los procesos en orden de llegada
2. **SJF (Shortest Job First):** Prioriza los procesos con menor tiempo de ejecución restante
3. **Round Robin:** Ejecuta procesos por tiempos fijos (quantum) en orden circular
4. **Prioridades:** Ejecuta primero los procesos con mayor prioridad

## Ejemplos de uso
- Crear procesos con diferentes prioridades y tiempos de ejecución
- Observar cómo se comportan los diferentes algoritmos de planificación
- Probar la comunicación entre procesos
- Ejecutar la demostración de productor-consumidor

## Notas adicionales
Este proyecto fue desarrollado como parte de los requisitos de la materia de Sistemas Operativos y tiene fines educativos.

¡Gracias por utilizar nuestro simulador de gestor de procesos!
