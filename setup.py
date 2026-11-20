"""Paquete mínimo para distribuir las reglas propias a los workers de Beam."""
from setuptools import find_packages, setup

setup(
    name="datalandia-pipelines",
    version="0.1.0",
    packages=find_packages(include=["pipelines", "pipelines.cloud", "schemas"]),
    package_data={"schemas": ["bigquery/*.json"]},
    python_requires=">=3.12",
)
