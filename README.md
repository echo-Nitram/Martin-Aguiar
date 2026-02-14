# Sistema de Gestión de Incidencias - Soporte Técnico

Sistema para registrar, gestionar y dar seguimiento a incidencias de soporte técnico. Construido con Python y SQLite.

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación y uso

### 1. Clonar el repositorio

```bash
git clone https://github.com/echo-Nitram/Martin-Aguiar.git
cd Martin-Aguiar
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. (Opcional) Cargar datos de ejemplo

```bash
python seed.py
```

Esto crea 3 clientes, 3 técnicos y 6 incidencias de ejemplo para que puedas explorar el sistema.

### 4. Iniciar el sistema

```bash
python main.py
```

## Funcionalidades

| Módulo | Descripción |
|--------|-------------|
| **Incidencias** | Crear, listar, ver detalle, cambiar estado, asignar técnico, agregar notas, eliminar |
| **Clientes** | Registrar, listar, editar y eliminar clientes |
| **Técnicos** | Registrar, listar, editar y desactivar técnicos |
| **Reportes** | Resumen general, incidencias por técnico, por cliente y por categoría |

### Estados de una incidencia

| Estado | Descripción |
|--------|-------------|
| `abierta` | Recién creada, sin atender |
| `en_progreso` | Un técnico está trabajando en ella |
| `en_espera` | Pausada (esperando repuesto, respuesta del cliente, etc.) |
| `resuelta` | Problema solucionado |
| `cerrada` | Caso finalizado |

### Prioridades

`baja` · `media` · `alta` · `critica`

### Categorías

`hardware` · `software` · `red` · `email` · `seguridad` · `otro`

## Ejecutar tests

```bash
python -m unittest tests.test_sistema -v
```

## Estructura del proyecto

```
├── main.py                 # Punto de entrada
├── seed.py                 # Carga datos de ejemplo
├── requirements.txt        # Dependencias
├── incidencias/
│   ├── database.py         # Conexión SQLite y esquema de tablas
│   ├── modelos.py          # Operaciones CRUD
│   ├── reportes.py         # Estadísticas y reportes
│   └── cli.py              # Interfaz interactiva por menús
└── tests/
    └── test_sistema.py     # Tests unitarios
```
