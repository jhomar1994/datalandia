# Presentación ejecutiva P3

Versión lista para exposición de **15 minutos**, incluidas doce diapositivas y una demo de tres minutos.

- [PowerPoint editable](output/Lumina_P3_15min.pptx).
- [PDF de respaldo](output/Lumina_P3_15min.pdf).
- [Guion y tiempos](guion_ejecutivo_15min.md): notas incluidas también en el PPTX.
- [Speech literal para cuatro integrantes](speech_4_integrantes_15min.md): texto listo para decir, relevos, acciones de demo y cierre condicional.
- [Preparación de la demo](demo_15min.md): CLI existentes separados, un worker y cierre verificado.

La presentación sigue la portada, paleta, fondo, tipografía y lenguaje de paneles de la plantilla
aportada por el usuario. Conserva diagramas y tablas editables. El original no fue modificado.
Fuentes: Space Grotesk, Roboto Mono y las fuentes de la portada original. El PDF conserva la apariencia
con fuentes incrustadas para equipos donde no estén instaladas.

Se revisaron las doce páginas renderizadas con Keynote, sin afirmar compatibilidad probada en PowerPoint
ni Google Slides. Los validadores estructurales y de geometría no encontraron defectos.
El runtime de Artifact Tool/Spaces no estuvo disponible; se adaptó directamente una copia OOXML de la plantilla.
El PPTX no es una presentación nativa de Google Slides, aunque puede importarse para su edición.

La estimación anual es preliminar. Gasto facturado y créditos: NO VERIFICADO.
Los resultados medidos corresponden a las ejecuciones citadas en las notas, no a totales actuales.
La distribución de aportes individuales debe confirmarse con el equipo.

## Preparación local de mensajes

`preparar_eventos_exposicion.py` genera un warmup y 62 mensajes sin publicar ni crear recursos.
Se comprobó que los mensajes contienen sesenta válidos y dos inválidos según el contrato compartido.
Para repetir la exposición, usar una carpeta nueva --out y mantener el límite del controlador.

`build_executive.py` conserva el código de reproducción del PPTX. Requiere la plantilla original
disponible localmente y usa la biblioteca estándar de Python:

```bash
python3 presentation/build_executive.py --template "/ruta/a/la/plantilla.pptx"
```

La plantilla original y los archivos auxiliares de Keynote no se publican. En `output/`
solo se versionan el PPTX final y el PDF de respaldo (aproximadamente 3,5 MiB en conjunto).
La exportación PDF y revisión visual
se realizaron en Keynote. `guion_slides.md` es el borrador previo, no la versión final.
