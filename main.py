#!/usr/bin/env python3
"""Punto de entrada del Sistema de Gestión de Incidencias."""

from dotenv import load_dotenv
load_dotenv()

from incidencias.cli import menu_principal

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n¡Hasta luego!")
