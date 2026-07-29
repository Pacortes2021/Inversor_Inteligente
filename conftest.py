import os
import sys

# Agregar la raíz del proyecto a sys.path para que los módulos en backend puedan ser importados en los tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
