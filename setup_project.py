import os
import json

# 1. Definir las carpetas del proyecto
directories = [
    "data/raw",
    "data/silver",
    "data/gold",
    "notebooks"
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"[CARPETA] Creada o verificada: {directory}")

# 2. Estructura JSON básica para un Jupyter Notebook vacío pero válido
empty_notebook = {
 "cells": [],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 2
}

print("\n¡Estructura de proyecto 'datalandia' lista para trabajar!")