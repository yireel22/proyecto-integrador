#librerias
import queue
import time
import threading
from enum import Enum
from collections import deque
import os



# Enumeraciones
class Estado(Enum):
    LISTO = "Listo"
    EJECUTANDO = "Ejecutando"
    ESPERANDO = "Esperando"
    TERMINADO = "Terminado"


class CausaTerminacion(Enum):
    NORMAL = "Finalización normal"
    FORZADA = "Terminado por usuario"
    ERROR = "Error en ejecución"
    INTERBLOQUEO = "Interbloqueo detectado"
    SIN_MEMORIA = "Memoria insuficiente"


# Estructura PCB
class PCB:
    def __init__(self, pid, nombre, prioridad=0):
        self.pid = pid
        self.nombre = nombre
        self.estado = Estado.LISTO
        self.prioridad = prioridad
        self.recursos_asignados = {
            "CPU": False,
            "memoria": 0
        }
        self.tiempo_restante = 0
        self.tiempo_creacion = time.time()
        self.mensajes = queue.Queue()
        self.causa_terminacion = None
        self.historial = []

    def registrar_evento(self, evento):
        self.historial.append(f"[{time.ctime()}] {evento}")

    def __str__(self):
        recursos = ", ".join([f"{k}:{v}" for k, v in self.recursos_asignados.items() if v])
        estado = f"{self.estado.value}"
        if self.estado == Estado.TERMINADO and self.causa_terminacion:
            estado += f" ({self.causa_terminacion.value})"
        return f"PID {self.pid}: {self.nombre} ({estado}) | Prioridad: {self.prioridad} | Tiempo: {self.tiempo_restante} | Recursos: [{recursos}]"


# Recurso del sistema
class Recurso:
    def __init__(self, tipo, cantidad_total):
        self.tipo = tipo
        self.cantidad_total = cantidad_total
        self.cantidad_disponible = cantidad_total
        self.procesos_esperando = queue.Queue()

    def asignar(self, proceso, cantidad):
        if self.cantidad_disponible >= cantidad:
            self.cantidad_disponible -= cantidad
            proceso.recursos_asignados[self.tipo] += cantidad
            proceso.registrar_evento(f"Asignado {cantidad} de {self.tipo}")
            return True
        proceso.estado = Estado.ESPERANDO
        self.procesos_esperando.put((proceso, cantidad))
        proceso.registrar_evento(f"Esperando {cantidad} de {self.tipo}")
        return False

    def liberar(self, proceso, cantidad):
        self.cantidad_disponible += cantidad
        proceso.recursos_asignados[self.tipo] -= cantidad
        proceso.registrar_evento(f"Liberado {cantidad} de {self.tipo}")

        # Intentar asignar a procesos en espera
        if not self.procesos_esperando.empty():
            prox_proceso, prox_cantidad = self.procesos_esperando.get()
            if self.asignar(prox_proceso, prox_cantidad):
                prox_proceso.estado = Estado.LISTO
                return prox_proceso
        return None


# Memoria compartida para productor-consumidor
class MemoriaCompartida:
    def __init__(self, capacidad=5):
        self.buffer = []
        self.capacidad = capacidad
        self.mutex = threading.Semaphore(1)
        self.lleno = threading.Semaphore(0)
        self.vacio = threading.Semaphore(capacidad)

    def escribir(self, dato, proceso):
        self.vacio.acquire()
        self.mutex.acquire()

        self.buffer.append(dato)
        proceso.registrar_evento(f"Productor escribió: {dato}")
        print(f"Productor {proceso.pid} escribió: {dato}")

        self.mutex.release()
        self.lleno.release()

    def leer(self, proceso):
        self.lleno.acquire()
        self.mutex.acquire()

        dato = self.buffer.pop(0)
        proceso.registrar_evento(f"Consumidor leyó: {dato}")
        print(f"Consumidor {proceso.pid} leyó: {dato}")

        self.mutex.release()
        self.vacio.release()
        return dato


# Gestor de Procesos completo
#no se por que algoritmo y quantum tienen una advertencia... revisar despues
class GestorProcesos:
    def __init__(self, algoritmo="FCFS", quantum=3):
        self.procesos = {}
        self.cola_listos = deque()
        self.recursos = {
            "CPU": Recurso("CPU", 1),
            "memoria": Recurso("memoria", 4096)  # 4GB
        }
        self.pid_counter = 1
        self.proceso_ejecutando = None
        self.algoritmo = algoritmo.upper()  # Asegurar mayúsculas
        self.quantum = quantum
        self.contador_quantum = 0
        self.memoria_compartida = MemoriaCompartida()
        self.reloj = 0
        self.log_sistema = queue.Queue()
        self.eventos = threading.Event()
        self.running = True

    def log_evento(self, mensaje):
        entrada = f"[{time.ctime()}] {mensaje}"
        self.log_sistema.put(entrada)
        print(entrada)

    def crear_proceso(self, nombre, tiempo_ejecucion, prioridad=0, memoria_necesaria=512):
        pid = self.pid_counter
        self.pid_counter += 1

        pcb = PCB(pid, nombre, prioridad)
        pcb.tiempo_restante = tiempo_ejecucion

        if not self.recursos["memoria"].asignar(pcb, memoria_necesaria):
            self.log_evento(f"Error: Memoria insuficiente para crear proceso {nombre}")
            pcb.causa_terminacion = CausaTerminacion.SIN_MEMORIA
            pcb.estado = Estado.TERMINADO
            self.procesos[pid] = pcb
            return None

        self.procesos[pid] = pcb
        self.agregar_a_cola_listos(pcb)
        self.log_evento(f"Proceso creado: {pcb}")
        return pid

    def agregar_a_cola_listos(self, proceso):
        if self.algoritmo == "SJF":
            # Insertar ordenado por tiempo restante (menor primero)
            i = 0
            while i < len(self.cola_listos):
                if proceso.tiempo_restante < self.cola_listos[i].tiempo_restante:
                    break
                i += 1
            self.cola_listos.insert(i, proceso)
        elif self.algoritmo == "PRIORIDADES":
            # Insertar ordenado por prioridad (mayor primero)
            i = 0
            while i < len(self.cola_listos):
                if proceso.prioridad > self.cola_listos[i].prioridad:
                    break
                i += 1
            self.cola_listos.insert(i, proceso)
        else:  # FCFS y Round Robin
            self.cola_listos.append(proceso)

        proceso.estado = Estado.LISTO
        proceso.registrar_evento("Agregado a cola de listos")

    def planificar(self):
        if self.proceso_ejecutando is None and self.cola_listos:
            siguiente = self.cola_listos.popleft()

            if self.recursos["CPU"].asignar(siguiente, 1):
                siguiente.estado = Estado.EJECUTANDO
                self.proceso_ejecutando = siguiente
                self.contador_quantum = 0
                self.log_evento(f"Proceso {siguiente.pid} en ejecución")
            else:
                self.agregar_a_cola_listos(siguiente)

    def ejecutar_ciclo(self):
        self.reloj += 1
        self.log_evento(f"\n--- Ciclo {self.reloj} (Algoritmo: {self.algoritmo}) ---")

        if self.proceso_ejecutando:
            self.proceso_ejecutando.tiempo_restante -= 1
            self.contador_quantum += 1

            self.log_evento(
                f"Proceso {self.proceso_ejecutando.pid} ejecutando... Tiempo restante: {self.proceso_ejecutando.tiempo_restante}")

            # Verificar si el proceso terminó
            if self.proceso_ejecutando.tiempo_restante <= 0:
                self.terminar_proceso(self.proceso_ejecutando.pid, CausaTerminacion.NORMAL)
            # Round Robin: Verificar quantum solo si estamos usando RR
            elif self.algoritmo == "RR" and self.contador_quantum >= self.quantum:
                self.log_evento(f"Quantum agotado para proceso {self.proceso_ejecutando.pid}")
                self.suspender_proceso(self.proceso_ejecutando.pid)

        self.planificar()
        self.detectar_interbloqueos()
        self.mostrar_estado()

    def suspender_proceso(self, pid):
        if pid in self.procesos:
            proceso = self.procesos[pid]
            if proceso.estado == Estado.EJECUTANDO:
                proceso.estado = Estado.LISTO
                self.recursos["CPU"].liberar(proceso, 1)
                self.agregar_a_cola_listos(proceso)
                self.proceso_ejecutando = None
                proceso.registrar_evento("Proceso suspendido")
                self.log_evento(f"Proceso {pid} suspendido")
                self.planificar()

    def reanudar_proceso(self, pid):
        if pid in self.procesos:
            proceso = self.procesos[pid]
            if proceso.estado == Estado.ESPERANDO:
                proceso.estado = Estado.LISTO
                self.agregar_a_cola_listos(proceso)
                proceso.registrar_evento("Proceso reanudado")
                self.log_evento(f"Proceso {pid} reanudado")
                return True
        return False

    def terminar_proceso(self, pid, causa=CausaTerminacion.FORZADA):
        if pid in self.procesos:
            proceso = self.procesos[pid]

            # Liberar todos los recursos
            if proceso.recursos_asignados["CPU"] > 0:
                self.recursos["CPU"].liberar(proceso, 1)
            if proceso.recursos_asignados["memoria"] > 0:
                self.recursos["memoria"].liberar(proceso, proceso.recursos_asignados["memoria"])

            proceso.estado = Estado.TERMINADO
            proceso.causa_terminacion = causa
            proceso.registrar_evento(f"Proceso terminado. Causa: {causa.value}")
            self.log_evento(f"Proceso {pid} terminado. Causa: {causa.value}")

            if self.proceso_ejecutando and self.proceso_ejecutando.pid == pid:
                self.proceso_ejecutando = None
                self.planificar()
            return True
        return False

    def detectar_interbloqueos(self):
        # Detección simple: procesos esperando recursos en ciclo
        grafo = {}
        for pid, proceso in self.procesos.items():
            if proceso.estado == Estado.ESPERANDO:
                recursos_necesarios = []
                if proceso.recursos_asignados["CPU"] == 0:
                    recursos_necesarios.append("CPU")
                grafo[pid] = recursos_necesarios

        # Si hay ciclos en el grafo, hay interbloqueo
        if grafo:  # Implementación simplificada
            for pid in list(self.procesos.keys()):
                if self.procesos[pid].estado == Estado.ESPERANDO:
                    self.log_evento(f"Posible interbloqueo detectado en proceso {pid}")
                    self.terminar_proceso(pid, CausaTerminacion.INTERBLOQUEO)
                    break

    # Comunicación entre procesos
    def enviar_mensaje(self, pid_emisor, pid_receptor, mensaje):
        if pid_receptor in self.procesos:
            self.procesos[pid_receptor].mensajes.put(mensaje)
            self.log_evento(f"Mensaje enviado de {pid_emisor} a {pid_receptor}: {mensaje}")
            return True
        return False

    def recibir_mensaje(self, pid):
        if pid in self.procesos:
            try:
                mensaje = self.procesos[pid].mensajes.get_nowait()
                self.log_evento(f"Proceso {pid} recibió mensaje: {mensaje}")
                return mensaje
            except queue.Empty:
                self.log_evento(f"Proceso {pid} no tiene mensajes")
                return None
        return None

    # Productor-Consumidor
    def productor(self, pid, items):
        proceso = self.procesos.get(pid)
        if proceso:
            for i in range(items):
                dato = f"Dato-{i}-de-{pid}"
                self.memoria_compartida.escribir(dato, proceso)
                time.sleep(0.5)
            self.log_evento(f"Productor {pid} terminó")

    def consumidor(self, pid, items):
        proceso = self.procesos.get(pid)
        if proceso:
            for _ in range(items):
                dato = self.memoria_compartida.leer(proceso)
                time.sleep(0.7)
            self.log_evento(f"Consumidor {pid} terminó")

    # Visualización del estado
    def mostrar_estado(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n=== Estado del Sistema (Ciclo {self.reloj}) ===")
        print(f"Algoritmo: {self.algoritmo}", end="")
        if self.algoritmo == "RR":
            print(f" (Quantum: {self.quantum})")
        else:
            print()

        print("\nProceso en ejecución:")
        print(f"  {self.proceso_ejecutando}" if self.proceso_ejecutando else "  Ninguno")

        print("\nCola de listos:")
        for proceso in self.cola_listos:
            print(f"  {proceso}")
        if not self.cola_listos:
            print("  Vacía")

        print("\nProcesos bloqueados:")
        bloqueados = [p for p in self.procesos.values() if p.estado == Estado.ESPERANDO]
        for proceso in bloqueados:
            print(f"  {proceso}")
        if not bloqueados:
            print("  Ninguno")

        print("\nRecursos disponibles:")
        for nombre, recurso in self.recursos.items():
            print(f"  {nombre}: {recurso.cantidad_disponible}/{recurso.cantidad_total}")

    # Interfaz de usuario
    def menu_principal(self):
        while self.running:
            print("\n=== Menú Principal ===")
            print(f"Algoritmo actual: {self.algoritmo}", end="")
            if self.algoritmo == "RR":
                print(f" (Quantum: {self.quantum})")
            else:
                print()
            print("1. Crear proceso")
            print("2. Listar procesos")
            print("3. Suspender proceso")
            print("4. Reanudar proceso")
            print("5. Terminar proceso")
            print("6. Ejecutar ciclo")
            print("7. Ejecutar 5 ciclos automáticos")
            print("8. Demostración Productor-Consumidor")
            print("9. Ver historial de proceso")
            print("10. Cambiar algoritmo de planificación")
            print("0. Salir")
            print("G. presentacion de participantes")

            opcion = input("Seleccione una opción: ")

            try:
                if opcion == "1":
                    self.crear_proceso_interactivo()
                elif opcion == "2":
                    self.mostrar_estado()
                elif opcion == "3":
                    pid = int(input("PID del proceso a suspender: "))
                    self.suspender_proceso(pid)
                elif opcion == "4":
                    pid = int(input("PID del proceso a reanudar: "))
                    self.reanudar_proceso(pid)
                elif opcion == "5":
                    pid = int(input("PID del proceso a terminar: "))
                    self.terminar_proceso(pid)
                elif opcion == "6":
                    self.ejecutar_ciclo()
                elif opcion == "7":
                    for _ in range(5):
                        if not self.running:
                            break
                        self.ejecutar_ciclo()
                        time.sleep(1)
                elif opcion == "8":
                    self.demostracion_productor_consumidor()
                elif opcion == "9":
                    pid = int(input("PID del proceso a consultar: "))
                    self.mostrar_historial(pid)
                elif opcion == "10":
                    self.cambiar_algoritmo()
                elif opcion == "0":
                    self.running = False
                elif opcion == "g":
                    print("\nMuchas gracias por utilizar nuestro software de simulación de gestor de procesos")
                    print("Integrantes del equipo:")
                    print("- Andrade Nieto Isaac Yireel")
                    print("- Cabrera Gabriel Cenyaze Daylaan")
                    print("- Estrada Olvera Frank")
                    print("- Huerta Hernández Dilan Dariel")
                    opcion = input("precione ENTER para regresar al menu.")
                else:
                    print("Opción no válida")
            except ValueError:
                print("Entrada inválida. Ingrese un número.")

    def cambiar_algoritmo(self):
        print("\nAlgoritmos disponibles:")
        print("1. FCFS (First Come, First Served)")
        print("2. SJF (Shortest Job First)")
        print("3. RR (Round Robin)")
        print("4. Prioridades")

        opcion = input("Seleccione el algoritmo: ")

        if opcion == "1":
            self.algoritmo = "FCFS"
            print("Algoritmo cambiado a FCFS")
        elif opcion == "2":
            self.algoritmo = "SJF"
            print("Algoritmo cambiado a SJF")
        elif opcion == "3":
            self.algoritmo = "RR"
            self.quantum = int(input("Ingrese el quantum para Round Robin (3): ") or 3)
            print(f"Algoritmo cambiado a Round Robin con quantum {self.quantum}")
        elif opcion == "4":
            self.algoritmo = "PRIORIDADES"
            print("Algoritmo cambiado a Prioridades")
        else:
            print("Opción no válida")

        # Reorganizar la cola de listos con el nuevo algoritmo
        procesos_a_reorganizar = list(self.cola_listos)
        self.cola_listos = deque()
        for proceso in procesos_a_reorganizar:
            self.agregar_a_cola_listos(proceso)

    def crear_proceso_interactivo(self):
        nombre = input("Nombre del proceso: ")
        tiempo = int(input("Tiempo de ejecución: "))
        prioridad = int(input("Prioridad (0=normal): "))
        memoria = int(input("Memoria requerida (MB): "))
        self.crear_proceso(nombre, tiempo, prioridad, memoria)

    def mostrar_historial(self, pid):
        if pid in self.procesos:
            print(f"\nHistorial del proceso {pid}:")
            for evento in self.procesos[pid].historial:
                print(f"  {evento}")
        else:
            print("PID no válido")

    def demostracion_productor_consumidor(self):
        prod = self.crear_proceso("Productor", 10, 1, 256)
        cons = self.crear_proceso("Consumidor", 10, 1, 256)

        # Hilos para ejecutar concurrentemente
        hilo_prod = threading.Thread(target=self.productor, args=(prod, 5))
        hilo_cons = threading.Thread(target=self.consumidor, args=(cons, 5))

        hilo_prod.start()
        hilo_cons.start()

        # Ejecutar ciclos mientras trabajan
        for _ in range(15):
            if not self.running:
                break
            self.ejecutar_ciclo()
            time.sleep(1)

        hilo_prod.join()
        hilo_cons.join()


# Punto de entrada
if __name__ == "__main__":
    print("=== Simulador de Gestor de Procesos ===")
    print("Algoritmos disponibles: FCFS, SJF, RR, Prioridades")
    algoritmo = input("Seleccione algoritmo (FCFS): ").upper() or "FCFS"
    quantum = 3
    if algoritmo == "RR":
        quantum = int(input("Quantum para Round Robin (3): ") or "3")

    gestor = GestorProcesos(algoritmo=algoritmo, quantum=quantum)

    # Crear algunos procesos de ejemplo
    gestor.crear_proceso("Navegador", 6, 1, 1024)
    gestor.crear_proceso("Editor", 4, 2, 512)
    gestor.crear_proceso("Servidor", 8, 0, 2048)

    # Iniciar interfaz
    gestor.menu_principal()