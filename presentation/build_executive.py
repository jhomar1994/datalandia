"""Adapta una copia OOXML de la plantilla, preservando temas y elementos nativos.

No requiere python-pptx. El render de revisión se hace con Keynote.
No inicia servicios ni realiza llamadas GCP.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as E
from copy import deepcopy
import argparse,json,re

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--template',type=Path,required=True,help='Plantilla PPTX original disponible localmente; no se incluye en el repositorio.')
args=parser.parse_args()
SOURCE=args.template.expanduser().resolve()
if not SOURCE.is_file():parser.error('La plantilla indicada no existe.')
OUT=ROOT/'presentation/output/Lumina_P3_15min.pptx'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
for key,value in [('a',A),('p',P),('r',R)]:E.register_namespace(key,value)
E.register_namespace('',CT)
NS={'a':A,'p':P,'r':R}
BLUE='0E63F0';CYAN='00E1FF';INK='4E4B4C';MUTED='6B6869';WHITE='FFFFFF';GRAY='E4E4E4'
EMU=914400
FONT='Space Grotesk'

def el(parent,tag,attrib=None,**attrs):
    pref,name=tag.split(':');node=E.SubElement(parent,'{'+NS[pref]+'}'+name,attrib or {})
    node.attrib.update({k:str(v) for k,v in attrs.items()});return node

def xml(node):return E.tostring(node,encoding='utf-8',xml_declaration=True)

def set_pos(node,x,y,w,h):
    xf=node.find('p:spPr/a:xfrm',NS)
    for tag,attrs in [('off',{'x':round(x*EMU),'y':round(y*EMU)}),('ext',{'cx':round(w*EMU),'cy':round(h*EMU)})]:
        item=xf.find('a:'+tag,NS)
        item.attrib.update({k:str(v) for k,v in attrs.items()})

class Slide:
    def __init__(self,idx,title,kicker):
        self.idx=idx;self.root=deepcopy(base);self.tree=self.root.find('p:cSld/p:spTree',NS);self.ident=500
        for item in list(self.tree)[2:]:self.tree.remove(item)
        self.text(.6,.40,11.9,.35,kicker.upper(),13,BLUE,True)
        self.text(.6,.84,12.05,.76,title,32,INK,True)
        self.text(12.0,7.05,.7,.22,f'{idx:02d} / 12',10,MUTED,False,align='r')
    def shape(self,x,y,w,h,fill=None,geometry='rect',line=None):
        self.ident+=1;s=el(self.tree,'p:sp');nv=el(s,'p:nvSpPr');el(nv,'p:cNvPr',id=self.ident,name=f'Lumina {self.idx}-{self.ident}');el(nv,'p:cNvSpPr');el(nv,'p:nvPr')
        sp=el(s,'p:spPr');xf=el(sp,'a:xfrm');el(xf,'a:off',x=round(x*EMU),y=round(y*EMU));el(xf,'a:ext',cx=round(w*EMU),cy=round(h*EMU))
        g=el(sp,'a:prstGeom',prst=geometry);el(g,'a:avLst')
        if fill:el(el(sp,'a:solidFill'),'a:srgbClr',val=fill)
        else:el(sp,'a:noFill')
        ln=el(sp,'a:ln',w=12700)
        if line:el(el(ln,'a:solidFill'),'a:srgbClr',val=line)
        else:el(ln,'a:noFill')
        return s
    def text(self,x,y,w,h,text,size=20,color=INK,bold=False,align='l',fill=None,geometry='rect',font=FONT):
        s=self.shape(x,y,w,h,fill,geometry);body=el(s,'p:txBody');bp=el(body,'a:bodyPr',wrap='square',anchor='t',lIns=0,rIns=0,tIns=0,bIns=0);el(bp,'a:noAutofit');el(body,'a:lstStyle')
        for line in text.split('\n'):
            para=el(body,'a:p');pp=el(para,'a:pPr',algn=align);el(el(pp,'a:lnSpc'),'a:spcPct',val=112000);el(el(pp,'a:spcAft'),'a:spcPts',val=300)
            run=el(para,'a:r');rp=el(run,'a:rPr',lang='es-PE',sz=round(size*100),b='1' if bold else '0');el(el(rp,'a:solidFill'),'a:srgbClr',val=color);el(rp,'a:latin',typeface=font);el(rp,'a:ea',typeface=font);el(rp,'a:cs',typeface=font);el(run,'a:t').text=line
            el(para,'a:endParaRPr',sz=round(size*100))
        return s
    def card(self,x,y,w,h,title,body,accent=None,size=20):
        self.shape(x,y,w,h,WHITE,'roundRect')
        self.shape(x+.22,y+.24,.40,.40,CYAN,'ellipse')
        self.text(x+.27,y+.28,.30,.30,accent or '',15,INK,True,align='ctr')
        self.text(x+.80,y+.25,w-1.02,.64,title,21,INK,True)
        self.text(x+.25,y+1.05,w-.50,h-1.25,body,size,INK)
    def footer(self,text):self.text(.6,6.91,11.1,.30,text,10.5,MUTED)
    def arrow(self,x1,y1,x2,y2):
        self.ident+=1;c=el(self.tree,'p:cxnSp');nv=el(c,'p:nvCxnSpPr');el(nv,'p:cNvPr',id=self.ident,name=f'Flujo {self.ident}');el(nv,'p:cNvCxnSpPr');el(nv,'p:nvPr')
        sp=el(c,'p:spPr');attrs={}
        if x2<x1:attrs['flipH']='1'
        if y2<y1:attrs['flipV']='1'
        xf=el(sp,'a:xfrm',attrs);el(xf,'a:off',x=round(min(x1,x2)*EMU),y=round(min(y1,y2)*EMU));el(xf,'a:ext',cx=round(abs(x2-x1)*EMU),cy=round(abs(y2-y1)*EMU))
        el(el(sp,'a:prstGeom',prst='line'),'a:avLst');ln=el(sp,'a:ln',w=25400);el(el(ln,'a:solidFill'),'a:srgbClr',val=INK);el(ln,'a:tailEnd',type='triangle',w='sm',len='sm')
    def box(self,x,y,w,h,title,sub,fill=INK):
        self.shape(x,y,w,h,fill,'roundRect');color=INK if fill==CYAN else WHITE
        self.text(x+.12,y+.15,w-.24,.50,title,18,color,True,align='ctr')
        self.text(x+.12,y+.64,w-.24,h-.70,sub,14,color,False,align='ctr')
    def table(self,x,y,width,heights,colwidths,rows,font=18):
        self.ident+=1;gf=el(self.tree,'p:graphicFrame');nv=el(gf,'p:nvGraphicFramePr');el(nv,'p:cNvPr',id=self.ident,name='Tabla editable');el(nv,'p:cNvGraphicFramePr');el(nv,'p:nvPr')
        xf=el(gf,'p:xfrm');el(xf,'a:off',x=round(x*EMU),y=round(y*EMU));el(xf,'a:ext',cx=round(width*EMU),cy=round(sum(heights)*EMU))
        graphic=el(gf,'a:graphic');gd=el(graphic,'a:graphicData',uri=A+'/table');tbl=el(gd,'a:tbl');pr=el(tbl,'a:tblPr',firstRow='1',bandRow='0');el(pr,'a:tableStyleId').text='{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}'
        grid=el(tbl,'a:tblGrid')
        for w in colwidths:el(grid,'a:gridCol',w=round(w*EMU))
        for ri,row in enumerate(rows):
            tr=el(tbl,'a:tr',h=round(heights[ri]*EMU))
            for value in row:
                tc=el(tr,'a:tc');body=el(tc,'a:txBody');bp=el(body,'a:bodyPr');el(bp,'a:noAutofit');el(body,'a:lstStyle')
                for line in str(value).split('\n'):
                    para=el(body,'a:p');pp=el(para,'a:pPr');el(pp,'a:buNone');run=el(para,'a:r');rp=el(run,'a:rPr',sz=font*100,b='1' if ri==0 else '0',lang='es-PE');el(el(rp,'a:solidFill'),'a:srgbClr',val=WHITE if ri==0 else INK);el(rp,'a:latin',typeface=FONT);el(run,'a:t').text=line
                tcp=el(tc,'a:tcPr',marL=91440,marR=91440,marT=68580,marB=45720,anchor='ctr')
                el(el(tcp,'a:solidFill'),'a:srgbClr',val=BLUE if ri==0 else (WHITE if ri%2 else 'D4F8FF'))
                for side in ['lnL','lnR','lnT','lnB']:
                    ln=el(tcp,'a:'+side,w=6350);el(el(ln,'a:solidFill'),'a:srgbClr',val=GRAY)
    def metric(self,x,y,w,value,label,detail):
        self.shape(x,y,w,1.5,WHITE,'roundRect');self.text(x+.22,y+.16,w-.44,.60,value,35,BLUE,True)
        self.text(x+.22,y+.82,w-.44,.35,label,18,INK,True)
        self.text(x+.22,y+1.19,w-.44,.25,detail,12,MUTED)

with ZipFile(SOURCE) as z:parts={n:z.read(n) for n in z.namelist()}
base=E.fromstring(parts['ppt/slides/slide6.xml'])
cover=E.fromstring(parts['ppt/slides/slide1.xml'])
for t in cover.findall('.//a:t',NS):
    if t.text=='Deep':t.text='Big Data'
    if t.text=='Learning':t.text='Lumina'
# Añadir un descriptor dentro del área libre de la portada.
cover_builder=Slide(1,'','');cover_builder.root=cover;cover_builder.tree=cover.find('p:cSld/p:spTree',NS)
cover_builder.text(.82,1.40,8.0,.75,'Monitoreo operativo en GCP',30,WHITE,True)
cover_builder.text(.82,2.18,8.0,.40,'Exposición de datos y demo end-to-end',20,WHITE)
cover_builder.text(8.30,6.65,4.2,.28,'Proyecto P3  /  20 noviembre 2026',13,WHITE,align='r')
slides=[cover];notes=[]
notes.append(('Lumina: resumen y equipo',30,'Presentar al equipo de la plantilla: Christian Cajusol, Hugo Ángeles, Jhomar Yurivilca y Francisco Meza. Explicar que es un prototipo académico de movilidad. Iniciar el controlador de streaming al comenzar la exposición desde una segunda terminal, siguiendo el guion de preparación. No ejecutar demo_e2e.py anticipadamente: ese script termina solo y podría cerrarse antes de la demo.','Plantilla del usuario; README.md; demo/README.md.'))

s=Slide(2,'Alcance de la implementación','01  Resumen ejecutivo')
s.card(.6,1.95,3.88,3.95,'Problema','Viajes y sensores llegan\nen formatos y tiempos\ndistintos. La operación\nnecesita una consulta\nconsolidada y trazable.','1')
s.card(4.73,1.95,3.88,3.95,'Implementación','Migración del flujo local\na GCP con ingesta,\nvalidación, capas Silver\ny Gold, API y tablero\nde monitoreo.','2')
s.card(8.86,1.95,3.88,3.95,'Uso operativo','Identificar actividad\npor zona y revisar\nlecturas anómalas,\ncon trazabilidad de\neventos y rechazos.','3')
s.text(.85,6.18,11.7,.48,'Prototipo funcional bajo demanda. Impacto económico aún no medido.',20,BLUE,True)
s.footer('Caso académico: la homologación territorial y temporal es simulada.')
slides.append(s.root);notes.append(('Resumen ejecutivo',60,'El objetivo es exponer datos procesados hacia una aplicación consumidora. La migración cubre el flujo de procesamiento y exposición, no una migración corporativa completa. El operador puede revisar zonas activas, calidad y el último evento. El beneficio de negocio es propuesto: no atribuir ahorros ni causalidad al prototipo.','README.md; docs/pipelines_p3.md; api/README.md.'))

s=Slide(3,'Situación actual y correcciones de P2','02  Estado del proyecto')
s.shape(.6,1.95,5.90,3.95,INK,'roundRect');s.text(.90,2.22,5.3,.5,'Observaciones P2',24,WHITE,True)
s.text(.90,3.05,5.25,2.7,'Capturas sin reproducción clara\n\nCobertura cloud limitada\n\nJobs sin ciclo operativo verificable',21,WHITE)
s.shape(6.78,1.95,5.95,3.95,WHITE,'roundRect');s.text(7.08,2.22,5.3,.5,'Evidencia P3',24,BLUE,True)
s.text(7.08,3.05,5.25,2.7,'Código modular, Terraform y pruebas\n\n255 zonas batch y 11 de sensores\n\nControlador con límite y cierre',21,INK)
s.text(.85,6.18,11.6,.50,'Pendientes: publicar el commit final y probar escala y continuidad.',20,BLUE,True)
s.footer('Cobertura observada en muestras. Un worker no demuestra escalabilidad horizontal.')
slides.append(s.root);notes.append(('Situación actual',60,'Responder a cada observación sin exagerar. La trazabilidad mejora con código, contratos, guías y evidencias. El repositorio público existe, pero el commit final debe publicarse antes de entregar. La prueba batch real usó 10.000 entradas y produjo viajes válidos en 255 zonas. Los sensores cubren once zonas. Un batch DONE es correcto; detener streaming después de una prueba es control de costos, pero no operación 24/7.','docs/revision_observaciones_p2.md; docs/evidencias/demo_final.json; docs/evidencias/actualizacion_tablero.json.'))

s=Slide(4,'Criterios de éxito y performance','03  KPI de la demostración')
s.table(.6,1.90,12.12,[.55,.83,.83,.83,.83],[2.7,4.45,2.2,2.77],[
 ['KPI','Fórmula','Meta demo','Medido'],
 ['Contabilidad batch','(válidos + rechazos) / entradas','100 %','100 %'],
 ['Disponibilidad del evento','t primera respuesta API − t publicación','≤ 60 s*','1,35 s*'],
 ['Reproceso seguro','Δ filas tras repetir MERGE serial','0','0'],
 ['Cierre de cómputo','Jobs activos / máquinas virtuales','0 / 0','0 / 0']],18)
s.text(.85,6.00,11.6,.62,'* Un evento de control con el worker preparado. No es p95 ni SLA.',20,BLUE,True)
s.footer('Fuentes: evidencia batch y prueba streaming del 20/11/2026. Metas propuestas para la demo.')
slides.append(s.root);notes.append(('KPI',75,'Contabilidad: (8.459 + 1.541) / 10.000 = 100%. La tasa de aceptación 84,59% es un resultado de muestra, no una meta. La disponibilidad 1,35 s corresponde a un único evento con worker ya listo en el job lumina-p3-stream-20261120110633. No confundir con el KPI promedio del tablero ni incluirlo como percentil. La repetición serial del MERGE mantiene 8.459 viajes. El cierre verificado quedó en cero jobs y VMs. Las metas son de demo y no un SLA contractual.','docs/evidencias/demo_final.json; docs/evidencias/actualizacion_tablero.json; tests/test_bigquery_merge.py.'))

s=Slide(5,'Productos tecnológicos','04  Plataforma seleccionada')
s.card(.6,1.95,3.88,4.55,'Ingesta','Cloud Storage\nArchivos y catálogos\n\nPub/Sub\nMensajes de sensores','1',20)
s.card(4.73,1.95,3.88,4.55,'Procesamiento','Apache Beam / Dataflow\nValidación batch y streaming\n\nBigQuery\nSilver, cuarentena y Gold','2',19)
s.card(8.86,1.95,3.88,4.55,'Exposición y control','FastAPI / Cloud Run\nAPI privada y tablero\n\nTerraform / Workflows\nInfraestructura y verificación','3',18)
s.footer('Proyecto proyecto-datalandia. Región us-central1. Workflows verifica conteos, no relanza jobs.')
slides.append(s.root);notes.append(('Tecnologías',45,'Explicar responsabilidades sin enumerar todos los servicios GCP. Terraform aprovisiona. El controlador Python opera Dataflow y cierra workers. Workflows comprueba conteos. Cloud Run sirve la API y el HTML desde el mismo origen, con autenticación IAM. No se usa Dataproc, Composer ni Kubernetes propio.','infra/terraform/; pipelines/cloud/pipeline_beam.py; api/app/; workflows/verificar.yaml.'))

s=Slide(6,'Dependencias, supuestos y fuera de alcance','05  Condiciones de la solución')
items=[('Fuentes reales','TLC 2024, AoT 2018\ny contexto histórico 2017.'),('Homologación simulada','Zonas y desplazamiento\nde fechas sin equivalencia\ngeográfica real.'),('Acceso y red','Internet, ADC e IAM.\nWorkers privados en\nus-central1.'),('Límite de la prueba','Un worker por job.\nSin benchmark masivo\nni prueba de alta carga.'),('Fuera de alcance','Sensores físicos, forecast,\nagente Vertex y alta\ndisponibilidad 24/7.'),('Operación','Vigilancia local y cierre.\nEl arranque del worker\ntarda varios minutos.')]
for i,(title,body) in enumerate(items):
 x=.6+(i%3)*4.13;y=1.95+(i//3)*2.35
 s.shape(x,y,3.88,2.10,WHITE,'roundRect');s.text(x+.23,y+.20,3.42,.40,title,21,BLUE,True);s.text(x+.23,y+.72,3.42,1.30,body,18)
s.footer('No se atribuyen resultados productivos ni equivalencias territoriales reales a este ejercicio académico.')
slides.append(s.root);notes.append(('Dependencias y alcance',60,'Las fuentes son reales pero su unión entre ciudades es simulada. Los eventos se desplazan al calendario 2024, mientras processed_at conserva tiempo real. El tablero usa processed_at para el gráfico y event_ts para la ventana histórica de zonas. Dependemos de internet e identidades GCP. El controlador local debe seguir abierto para vigilar el cierre. La partición de sensores es event_ts y no se migró sin autorización. No prometer forecast, Vertex, sensores físicos ni 24/7.','README.md; api/README.md; docs/evidencias/actualizacion_tablero.json.'))

s=Slide(7,'Arquitectura final y unidades de consumo','06  Diseño desplegado en GCP')
s.text(.62,1.72,6.5,.35,'BATCH',14,BLUE,True);s.text(.62,3.83,6.5,.35,'STREAMING',14,BLUE,True)
s.box(.6,2.15,1.85,1.40,'Storage','Viajes TLC\ny catálogos')
s.box(3.0,2.15,1.85,1.40,'Dataflow','Batch\n1 vCPU')
s.box(5.4,2.15,1.85,1.40,'Staging','MERGE serial\ny cuarentena',CYAN)
s.box(.6,4.25,1.85,1.40,'Publicador','Laptop\nReplay AoT')
s.box(3.0,4.25,1.85,1.40,'Pub/Sub','Topic y\nsuscripción')
s.box(5.4,4.25,1.85,1.40,'Dataflow','Streaming\n2 vCPU')
s.box(8.0,2.60,1.85,2.45,'BigQuery','Silver y Gold\nDeduplicación\nVistas por zona',CYAN)
s.box(10.5,2.60,2.2,1.40,'Cloud Run','FastAPI privada')
s.box(10.5,4.20,2.2,1.40,'Tablero','Gráfico por minuto\ny último evento')
for y in [2.85,4.95]:
 s.arrow(2.45,y,2.93,y);s.arrow(4.85,y,5.33,y);s.arrow(7.25,y,7.93,y)
s.arrow(9.85,3.2,10.43,3.2);s.arrow(11.6,4.0,11.6,4.13)
s.text(.65,5.85,12.0,.78,'Un worker por job, disco de 30 GB y sin IP pública\nCloud Run: 0 a 1 instancia, 0,25 vCPU y 256 MiB',18,INK)
s.footer('Terraform aprovisiona recursos e IAM. Workflows verifica conteos. El controlador local gestiona el ciclo de demo.')
slides.append(s.root);notes.append(('Arquitectura',90,'Leer dos rutas que convergen en BigQuery. En batch se cargan archivos desde Storage y se consolida por MERGE transaccional serial. Streaming recibe replay por Pub/Sub y aplica validación antes de STREAMING_INSERTS. Silver conserva copias, Gold deduplica y excluye IDs conflictivos. La API usa vistas Gold y tablas recientes con máximo de 128 MiB por consulta y caché compartida. El navegador accede a la API desplegada en GCP mediante un proxy autenticado local: localhost no significa que el backend esté corriendo en la laptop. Vincular cada recurso con las horas y volúmenes de la estimación anual.','infra/terraform/; sql/bigquery/; api/README.md; costs/calculator.py.'))

s=Slide(8,'Estimación de consumo del primer año','07  Calculadora preliminar')
s.table(.6,1.90,12.12,[.60,.82,.82],[4.0,2.5,2.65,2.97],[['Escenario','Streaming / mes','USD / mes','USD / año'],['Bajo demanda','10 h','13,77','165,27'],['Continuo','730 h','336,44','4.037,31']],21)
s.text(.85,4.45,11.7,1.12,'Supuestos comunes: 10 h de batch al mes, 0,1 TiB de consultas,\n10 GiB medios en BigQuery y 2 GiB de tráfico Pub/Sub al mes.',19)
s.shape(.6,5.77,12.12,.75,CYAN,'roundRect');s.text(.85,5.94,11.6,.42,'Demo: presupuesto S/50. Gasto facturado: NO VERIFICADO.',22,INK,True)
s.footer('Modelo con reservas y 30 % de contingencia. SECU sin calibrar. Sin descuentos, impuestos ni créditos.')
slides.append(s.root);notes.append(('Calculadora',90,'Estimación de planificación, no cotización ni factura. El escenario bajo demanda reserva diez horas mensuales de streaming y diez de batch. El continuo modela 730 horas de streaming con el mismo worker, sin garantizar capacidad o SLA. Ambos asumen 0,1 TiB de consultas, 10 GiB medios BigQuery, 2 GiB Pub/Sub, dos SECU por hora de streaming como supuesto NO VERIFICADO, reservas por discos, Storage, inserts, Cloud Run, build, imágenes y logging. El modelo aplica 30% de contingencia. Los importes anuales se calculan antes de redondear mensual, por eso pueden diferir unos centavos de 12 por el mensual mostrado. El tipo de cambio de S/4 por USD del archivo es supuesto, no cotización. La retención debe revisarse para sostener almacenamiento medio. El gasto real de Cloud Billing sigue NO VERIFICADO. No afirmar que S/50 cubre operación anual.','costs/calculator.py; costs/estimate.json; costs/README.md. Tarifas consultadas 20/11/2026: https://cloud.google.com/dataflow/pricing ; https://cloud.google.com/bigquery/pricing ; https://cloud.google.com/pubsub/pricing ; https://cloud.google.com/run/pricing .'))

s=Slide(9,'Demostración end-to-end','08  Tres minutos para ver el flujo')
for i,(t,b) in enumerate([('Publicar','Ráfaga de IDs nuevos\ny dos inválidos.\nWorker ya preparado.'),('Observar','Barras por minuto,\núltimo evento y\nrechazos en el tablero.'),('Verificar y cerrar','Contrastar API y Gold.\nSolicitar drain y\ncomprobar cero VMs.')]):s.card(.6+4.13*i,1.95,3.88,3.45,t,b,str(i+1),20)
s.shape(.6,5.69,12.12,.76,INK,'roundRect');s.text(.85,5.87,11.6,.40,'http://127.0.0.1:8080/     API en GCP mediante proxy autenticado',18,WHITE,font='Roboto Mono')
s.footer('Respaldo: ?demo=1 muestra datos simulados y lo declara. No sustituye la evidencia de ejecución real.')
slides.append(s.root);notes.append(('Demo en vivo',180,'Preparación: seguir presentation/demo_15min.md. Al comenzar la exposición, otro integrante inicia scripts/run_dataflow.py en una terminal con límite de 15 minutos y archivo de stop nuevo. Publica el warmup preparado y comprueba su ID en la API antes de este bloque. No lanzar un segundo job. Minuto 0: mostrar job y su worker. Publicar los 62 mensajes preparados a un evento por segundo mientras el tablero se actualiza cada cinco segundos. Minuto 1: observar barras azules/naranjas y último ID, explicar ahora del servidor. Minuto 2: mostrar /eventos/ultimo y /eventos/por-minuto?min=15 en Swagger, y la cuarentena. Solicitar drain al terminar, continuar con resultados mientras cierra, verificar cero jobs/VMs al final. Si no está listo a tiempo, usar evidencia real guardada y declarar cualquier uso de modo simulado. El modo preparar/publicar/cerrar integrado en demo_e2e.py aún no está implementado: este guion utiliza los CLI existentes por separado.','demo/README.md; scripts/run_dataflow.py; pipelines/cloud/publicar_eventos.py; api/README.md; presentation/demo_15min.md.'))

s=Slide(10,'Evidencias de funcionamiento','09  Resultados observados')
s.metric(.6,1.95,3.88,'10.000','Entradas batch','8.459 válidas y 1.541 rechazadas')
s.metric(4.73,1.95,3.88,'257','Mensajes streaming','Incluye replay, controles e inválidos')
s.metric(8.86,1.95,3.88,'18','Pruebas de contrato','API, validación, caché y casos vacíos')
s.shape(.6,3.78,7.45,2.65,WHITE,'roundRect');s.text(.88,4.02,6.88,.45,'Movimiento verificado en Chrome',23,BLUE,True)
s.text(.88,4.76,6.88,1.35,'Aceptadas: 185 a 215 en la ráfaga\nBarras azules y naranjas actualizadas\nÚltimo evento: cambio de valor e ID',20)
s.shape(8.33,3.78,4.40,2.65,CYAN,'roundRect');s.text(8.60,4.05,3.86,.66,'Cierre verificado',25,INK,True)
s.text(8.60,4.90,3.86,1.10,'Job DRAINED\n0 jobs activos / 0 VMs',22,INK,True)
s.footer('Conteos de pruebas concretas, no totales actuales. La homologación sigue siendo simulada.')
slides.append(s.root);notes.append(('Evidencias',60,'Las cifras pertenecen a ejecuciones documentadas y no deben compararse como si fueran una sola carga. Batch: 10.000 entradas y 255 zonas de origen válidas. Streaming: 257 mensajes incluyen 220 de replay, cinco controles, treinta eventos nuevos y dos fixtures inválidos. Muchos IDs históricos ya existían: no son 257 nuevas lecturas únicas. Durante la ráfaga el KPI pasó de 185 a 215. Dieciocho pruebas de API y contratos, más dos integraciones SQL de BigQuery documentadas aparte. Se revisó visualmente el modo real y el simulado en Chrome. El cierre quedó DRAINED y cero workers/VMs en el corte observado.','docs/evidencias/demo_final.json; docs/evidencias/actualizacion_tablero.json; tests/README.md.'))

s=Slide(11,'Conclusiones','10  Factibilidad y límites')
s.card(.6,1.95,3.88,4.4,'Integración funcional','El dato recorre ingesta,\nvalidación, BigQuery,\nAPI y aplicación\nconsumidora en GCP.','1',21)
s.card(4.73,1.95,3.88,4.4,'Calidad auditable','Contratos, cuarentena,\nMERGE y deduplicación\npermiten explicar cada\nresultado y reintento.','2',21)
s.card(8.86,1.95,3.88,4.4,'Operación acotada','La ejecución bajo demanda\ny el cierre limitan consumo.\nEscala, recuperación y\nservicio 24/7 requieren\notra validación.','3',20)
s.footer('La demostración prueba factibilidad técnica del prototipo. No mide retorno económico ni capacidad de producción.')
slides.append(s.root);notes.append(('Conclusiones',60,'Cerrar el argumento: se logró la exposición y el consumidor con una ruta real de extremo a extremo. La calidad y la idempotencia son decisiones centrales para confiar en los agregados. El presupuesto condicionó una prueba funcional de un worker. Detener el cómputo después de demostrarlo es una decisión operativa defendible, pero no reemplaza observabilidad y recuperación en producción. No prometer ahorros, SLA ni horizontalidad no medidos.','docs/evidencias/actualizacion_tablero.json; docs/revision_observaciones_p2.md.'))

s=Slide(12,'Next steps y entrega del repositorio','11  Prioridades de cierre y evolución')
for i,(title,body) in enumerate([('Antes de entregar','Publicar el commit final y evidencias.\nEnsayar demo, turnos y control de gasto.'),('Siguiente iteración','Separar preparación, publicación y cierre.\nMedir carga, consultas, costos y retención.'),('Evolución operativa','Alertas, recuperación y CI/CD.\nEstado Terraform compartido y prueba de capacidad.')]):
 y=1.9+i*1.28;s.shape(.6,y,12.12,1.04,WHITE,'roundRect');s.text(.86,y+.18,3.14,.66,title,23,BLUE,True);s.text(4.15,y+.13,8.20,.84,body,17)
s.text(.85,6.03,11.7,.42,'github.com/jhomar1994/datalandia',25,BLUE,True)
s.footer('Rama de trabajo: feat/p3-entrega-final. Atribución individual: confirmar con el equipo antes de sustentar.')
slides.append(s.root);notes.append(('Next steps',90,'Primero cerrar el entregable, sin afirmar que el código local ya está publicado. Compartir el enlace al commit final cuando se haga push. Distribuir la exposición entre los cuatro integrantes y confirmar aportes reales: no inventar autorías ni responsabilidades. La separación preparar/publicar/cerrar es una mejora pendiente del controlador integrado. Para producción hacen falta capacidad, retención por processed_at, alertas, recuperación automática y backend de estado compartido. Retomar el presupuesto y una cotización con mediciones. Finalizar comprobando que Dataflow y las VMs quedaron en cero.','README.md; docs/revision_observaciones_p2.md; costs/README.md; https://github.com/jhomar1994/datalandia.'))

assert len(slides)==len(notes)==12
assert sum(n[1] for n in notes)==900
# Construir notas con la estructura nativa de la plantilla.
notes_base=E.fromstring(parts['ppt/notesSlides/notesSlide1.xml'])
for n in list(parts):
    if re.match(r'ppt/(slides|notesSlides)/(?:_rels/)?(?:slide|notesSlide)\d+\.xml(?:\.rels)?$',n):del parts[n]
for i,root in enumerate(slides,1):
    parts[f'ppt/slides/slide{i}.xml']=xml(root)
    rels=E.Element('{'+REL+'}Relationships')
    E.SubElement(rels,'{'+REL+'}Relationship',Id='rId1',Type=R+'/slideLayout',Target='../slideLayouts/slideLayout2.xml' if i==1 else '../slideLayouts/slideLayout1.xml')
    E.SubElement(rels,'{'+REL+'}Relationship',Id='rId2',Type=R+'/notesSlide',Target=f'../notesSlides/notesSlide{i}.xml')
    if i==1:
        E.SubElement(rels,'{'+REL+'}Relationship',Id='rId3',Type=R+'/image',Target='../media/image10.png')
        E.SubElement(rels,'{'+REL+'}Relationship',Id='rId4',Type=R+'/image',Target='../media/image3.png')
    parts[f'ppt/slides/_rels/slide{i}.xml.rels']=xml(rels)
    nr=deepcopy(notes_base);body=nr.find('.//p:sp/p:txBody',NS)
    for node in list(body)[2:]:body.remove(node)
    title,seconds,script,sources=notes[i-1]
    for text in [f'{i:02d}. {title} — Tiempo: {seconds//60}:{seconds%60:02d}',script,'Fuentes: '+sources]:
        pa=el(body,'a:p');run=el(pa,'a:r');rp=el(run,'a:rPr',lang='es-PE',sz=1200);el(rp,'a:latin',typeface='Arial');el(run,'a:t').text=text
    parts[f'ppt/notesSlides/notesSlide{i}.xml']=xml(nr)
    rr=E.Element('{'+REL+'}Relationships');E.SubElement(rr,'{'+REL+'}Relationship',Id='rId1',Type=R+'/notesMaster',Target='../notesMasters/notesMaster1.xml');E.SubElement(rr,'{'+REL+'}Relationship',Id='rId2',Type=R+'/slide',Target=f'../slides/slide{i}.xml')
    parts[f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels']=xml(rr)
pr=E.fromstring(parts['ppt/presentation.xml']);lst=pr.find('p:sldIdLst',NS);lst.clear()
for i in range(1,13):E.SubElement(lst,'{'+P+'}sldId',{'id':str(255+i),'{'+R+'}id':'rIdLumina'+str(i)})
for tag in ['custShowLst','sectionLst']:
    for item in pr.findall('p:'+tag,NS):pr.remove(item)
parts['ppt/presentation.xml']=xml(pr)
rels=E.fromstring(parts['ppt/_rels/presentation.xml.rels'])
for item in list(rels):
    if item.get('Type','').endswith('/slide'):rels.remove(item)
for i in range(1,13):E.SubElement(rels,'{'+REL+'}Relationship',Id='rIdLumina'+str(i),Type=R+'/slide',Target=f'slides/slide{i}.xml')
parts['ppt/_rels/presentation.xml.rels']=xml(rels)
ct=E.fromstring(parts['[Content_Types].xml'])
for item in list(ct):
    if re.match(r'/ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml$',item.get('PartName','')):ct.remove(item)
for i in range(1,13):
    for path,kind in [('slides/slide','slide'),('notesSlides/notesSlide','notesSlide')]:E.SubElement(ct,'{'+CT+'}Override',PartName=f'/ppt/{path}{i}.xml',ContentType=f'application/vnd.openxmlformats-officedocument.presentationml.{kind}+xml')
parts['[Content_Types].xml']=xml(ct)
core=E.fromstring(parts.get('docProps/core.xml', b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"/>'));dc='{http://purl.org/dc/elements/1.1/}'
for tag,val in [('title','Lumina: presentación ejecutiva P3'),('subject','Big Data en GCP, exposición de datos y demo end-to-end'),('creator','Equipo Lumina'),('description','12 diapositivas y notas para una exposición de 15 minutos. Basada en la plantilla aportada por el usuario.')]:
    node=core.find(dc+tag)
    if node is None:node=E.SubElement(core,dc+tag)
    node.text=val
parts['docProps/core.xml']=xml(core)
ct=E.fromstring(parts['[Content_Types].xml'])
if not any(x.get('PartName')=='/docProps/core.xml' for x in ct):
    E.SubElement(ct,'{'+CT+'}Override',PartName='/docProps/core.xml',ContentType='application/vnd.openxmlformats-package.core-properties+xml')
parts['[Content_Types].xml']=xml(ct)
rr=E.fromstring(parts['_rels/.rels'])
if not any(x.get('Type','').endswith('/metadata/core-properties') for x in rr):
    E.SubElement(rr,'{'+REL+'}Relationship',Id='rIdCoreLumina',Type='http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties',Target='docProps/core.xml')
parts['_rels/.rels']=xml(rr)
# Evitar que una miniatura vieja muestre el tema anterior.
parts.pop('docProps/thumbnail.jpeg',None)
# Conservar únicamente partes alcanzables: descarta imágenes y material del tema anterior.
import posixpath
from urllib.parse import unquote
reachable={'[Content_Types].xml'}
queue=['']
while queue:
    part=queue.pop()
    if part:
        if part in reachable:continue
        reachable.add(part)
        relpath=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
    else:relpath='_rels/.rels'
    if relpath not in parts:continue
    reachable.add(relpath)
    for rel in E.fromstring(parts[relpath]):
        if rel.get('TargetMode')=='External':continue
        target=unquote(rel.get('Target','')).split('#')[0]
        resolved=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(part),target))
        if resolved in parts and resolved not in reachable:queue.append(resolved)
parts={n:v for n,v in parts.items() if n in reachable}
ct=E.fromstring(parts['[Content_Types].xml'])
for item in list(ct):
    if item.tag.endswith('Override') and item.get('PartName','').lstrip('/') not in parts:ct.remove(item)
parts['[Content_Types].xml']=xml(ct)
OUT.parent.mkdir(exist_ok=True)
with ZipFile(OUT,'w',ZIP_DEFLATED) as z:
    for n,data in parts.items():z.writestr(n,data)
# Guion complementario editable y plan de tiempos.
lines=['# Lumina P3: guion ejecutivo de 15 minutos','','12 diapositivas. Tiempo total: 15:00, incluida demo de 3:00.','La atribución de aportes individuales debe confirmarse con el equipo.','']
elapsed=0
for i,(title,seconds,script,sources) in enumerate(notes,1):
    start=f'{elapsed//60:02d}:{elapsed%60:02d}';elapsed+=seconds;end=f'{elapsed//60:02d}:{elapsed%60:02d}'
    lines.extend([f'## {i}. {title} ({start}–{end})','',script,'',f'Fuentes: {sources}',''])
(ROOT/'presentation/guion_ejecutivo_15min.md').write_text('\n'.join(lines))
(ROOT/'referencias_locales/presentacion/content.json').write_text(json.dumps([{'slide':i,'title':n[0],'seconds':n[1]} for i,n in enumerate(notes,1)],indent=2,ensure_ascii=False))
print(OUT)
