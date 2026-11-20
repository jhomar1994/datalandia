import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project: str = "proyecto-datalandia"
    dataset: str = "lumina_demo"
    region: str = "us-central1"
    max_bytes_billed: int = 128 * 1024**2
    session_minutes: int = 120
    cache_ttl: float = 4
    latency_target: float = 60
    sensor_parameter: str = "temperature"

    @classmethod
    def from_env(cls):
        result = cls(
            project=os.getenv("LUMINA_PROJECT_ID", "proyecto-datalandia"),
            dataset=os.getenv("LUMINA_DATASET", "lumina_demo"),
            region=os.getenv("LUMINA_REGION", "us-central1"),
            max_bytes_billed=int(os.getenv("LUMINA_MAX_BYTES_BILLED", str(128 * 1024**2))),
            session_minutes=int(os.getenv("VENTANA_SESION_MIN", "120")),
            cache_ttl=float(os.getenv("CACHE_TTL_S", "4")),
            latency_target=float(os.getenv("LATENCIA_META_S", "60")),
            sensor_parameter=os.getenv("PARAMETRO_SENSOR", "temperature"),
        )
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", result.project):
            raise ValueError("Project ID inválido")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", result.dataset):
            raise ValueError("Dataset inválido")
        if not 16 * 1024**2 <= result.max_bytes_billed <= 512 * 1024**2:
            raise ValueError("Límite de consulta fuera del presupuesto de la demo")
        if not 1 <= result.session_minutes <= 1440 or not 0 <= result.cache_ttl <= 60 or not 0 < result.latency_target <= 3600:
            raise ValueError("Configuración de monitoreo fuera de rango")
        return result
