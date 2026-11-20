# Revisión de observaciones P2 y correcciones P3

## 1. Trazabilidad y repositorio

La observación tiene sentido si el informe omitió el enlace y los pasos reproducibles:
una captura no permite auditar transformaciones. Tener un repositorio no demuestra que la entrega lo enlazara.

Repositorio identificado: https://github.com/jhomar1994/datalandia, público al verificarlo.
Se organizaron pipelines, contratos, SQL, Terraform, API, consumidor, pruebas y guion.
Antes de entregar, publicar los cambios y colocar en slides e informe el enlace a un commit concreto.
Los cambios locales todavía no equivalen a código publicado. Datos y archivos privados están excluidos.
El README documenta las fuentes y el preparador genera un manifiesto con hashes.

## 2. Tamaño y cobertura

Tiene sentido cuestionar una sola zona para sustentar un escenario masivo. Distinguir volumen de las fuentes,
procesamiento local y volumen realmente ejecutado en Dataflow.

P3 preparó 100.000 viajes y once nodos. Para limitar costos se probaron 10.000 viajes en Dataflow:
8.459 válidos, 1.541 rechazados y 255 zonas de origen válidas. Un worker real acredita la ejecución
cloud, pero no escalabilidad horizontal ni rendimiento a gran volumen. El exportador admite el archivo
completo; la prueba de carga requiere presupuesto separado. Las asociaciones entre territorios son simuladas.

## 3. Jobs detenidos y continuidad

Tiene sentido respecto de la ausencia de automatización y evidencia funcional. Un batch terminado en `DONE`
es correcto por diseño. Un streaming detenido después de una prueba puede responder al presupuesto;
no acredita una operación continua de producción.

P3 incorpora controlador reproducible, límite de tiempo, cierre verificable y una demo que publica datos
y verifica su disponibilidad en una API. Mostrar el job corriendo y los resultados antes de detenerlo.
El cierre posterior no invalida la ruta funcional demostrada, pero tampoco resuelve por sí solo el requisito 24/7.

El workflow actual verifica conteos; no relanza jobs ni administra recuperación automática.
Para producción faltan orquestación del ciclo de vida, alertas, recuperación, CI/CD,
estado Terraform compartido y prueba de capacidad. Declararlos como próximos pasos.

Ver `docs/evidencias/demo_final.json` y `demo/README.md` para resultados y comandos.
