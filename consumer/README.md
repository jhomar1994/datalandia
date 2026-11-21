# Consumidor de monitoreo

El HTML vigente vive en `api/static/index.html`, servido por FastAPI en `/` y desplegado en Cloud Run.
`consumer/index.html` conserva una copia idéntica para revisión/respaldo; actualizarla al cambiar el original.
Se conservó el diseño compartido. Única corrección funcional: null no se convierte a cero en JavaScript.

- Sin parámetros: consulta siete endpoints del mismo origen cada cinco segundos, incluido `/batch/ultimo`.
- `?every=10`: intervalo personalizado, mínimo dos segundos.
- `?api=https://...`: base alternativa; requiere autorización/CORS en ese servidor. No se habilita CORS abierto.
- `?demo=1`: plan B con datos simulados y aviso explícito, sin consultar la API.

Gráfico por minuto de processed_at real y tarjeta de último evento con reloj del servidor.
La tabla por zona mantiene la última ventana histórica Gold (2024); no representa la hora actual.
El badge verde refleja acceso correcto a la API, no el estado del job Dataflow.
El pipeline no manda duplicados válidos a cuarentena, aunque el texto original del diseño los mencione.

Acceso autenticado y contrato detallados en `api/README.md`. El archivo puede abrirse localmente
con ?demo=1 como respaldo sin API. No se ha publicado GitHub Pages.
