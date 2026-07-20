import os
import sys

# Agregar la raíz del proyecto al sys.path para importación de módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.wsgi import application

app = application
