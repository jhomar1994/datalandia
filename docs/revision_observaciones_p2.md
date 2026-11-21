# Revisión de observaciones P2 y correcciones P3

## 1. Trazabilidad y repositorio

La observación tiene sentido si el informe omitió el enlace y los pasos reproducibles:
una captura no permite auditar transformaciones. Tener un repositorio no demuestra que la entrega lo enlazara.

Repositorio identificado: https://github.com/jhomar1994/datalandia, público al verificarlo.
Se organizaron pipelines, contratos, SQL, Terraform, API, consumidor, pruebas y guion.
La entrega se publica en `feat/p3-entrega-final`; el informe identifica el commit exacto auditado.
Datos y archivos privados están excluidos. Las evidencias pequeñas de resultados se versionan.
El README documenta las fuentes y el preparador genera un manifiesto con hashes.

## 2. Tamaño y cobertura

Tiene sentido cuestionar una sola zona para sustentar un escenario masivo. Distinguir volumen de las fuentes,
procesamiento local y volumen realmente ejecutado en Dataflow.

La prueba principal del 21/11/2026 procesó **1.000.000 de viajes reales en Dataflow**:
937.453 válidos, 62.547 rechazados y 255 zonas válidas de origen. Se observaron dos VMs
`n1-standard-1` del job. Duró 324,595 s (3.080,8 entradas/s brutas, con arranque y cargas).
El controlador registró 352 s y verificó cero jobs/VMs al cierre. La entrada tenía 260 códigos
de origen; la diferencia de cobertura responde a validación. Ver [evidencia](evidencias/batch_1m.json).

Frente a las 10.000 entradas anteriores, se probó cien veces el volumen. La observación de
muestra reducida se mitiga con evidencia de mayor volumen y recursos distribuidos; faltan
comparaciones controladas de uno/dos workers, cargas representativas y objetivos de servicio
para acreditar escalabilidad productiva. Las asociaciones entre territorios siguen simuladas.

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
