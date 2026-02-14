#!/bin/bash
echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo ""
echo "=== Cargando datos de ejemplo ==="
python seed.py

echo ""
echo "=== Listo! Iniciando el sistema ==="
echo ""
python main.py
