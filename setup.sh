#!/bin/bash
echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo ""
echo "=== Cargando datos de ejemplo ==="
python seed.py

echo ""
echo "=== Que deseas iniciar? ==="
echo "1) Interfaz web (navegador)"
echo "2) Interfaz CLI (terminal)"
echo ""
read -p "Opcion [1]: " opcion

if [ "$opcion" = "2" ]; then
    python main.py
else
    echo ""
    echo "=== Iniciando servidor web en http://localhost:5000 ==="
    echo ""
    python web.py
fi
