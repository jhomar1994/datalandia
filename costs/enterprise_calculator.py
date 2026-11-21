"""Proyección empresarial anual en us-central1 a tarifas de lista USD.

No despliega recursos. Sin free tier, créditos, impuestos ni descuentos.
Los volúmenes, tiempos, amplificación de Streaming Engine y SECU son supuestos.
"""
import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

GIB = 1024**3
TIB = 1024**4
RATES = dict(batch_cpu_h=0.056, stream_cpu_h=0.069, memory_gib_h=0.003557,
             disk_gib_h=0.000054, batch_shuffle_gib=0.011, engine_processed_gib=0.018,
             secu_h=0.089, bq_query_tib=6.25, bq_storage_gib_h=0.000031507,
             bq_insert_200mib=0.01, pubsub_tib=40, gcs_gib_h=0.000027397,
             gcs_a_1000=0.005, gcs_b_1000=0.0004, run_cpu_s=0.000024,
             run_memory_gib_s=0.0000025, run_million_requests=0.40,
             logging_gib=0.50, build_minute=0.006, registry_gib_h=0.000136986,
             workflow_1000=0.01, scheduler_job_31days=0.10,
             gcs_dual_component_gib_h=0.000030137, gcs_dual_replication_gib=0.02,
             gcs_dual_a_1000=0.01)


@dataclass(frozen=True)
class Assumptions:
    days: int = 365
    devices: int = 500
    interval_seconds: int = 15
    event_bytes: int = 1024
    batch_records_day: int = 20000
    batch_record_bytes: int = 1024
    batch_workers: int = 2
    batch_hours_day: float = 0.5
    stream_workers: int = 1
    stream_jobs: int = 1
    pubsub_subscriptions: int = 1
    raw_dual_region: bool = False
    engine_model: str = 'processed'
    engine_volume_multiplier: float = 3
    secu_per_hour: float = 2
    bq_bytes_factor: float = 1.05
    bq_retention_days: int = 90
    gold_gib_month: float = 2
    reference_gib: float = 5
    raw_retention_days: int = 365
    temp_gcs_average_gib: float = 20
    dashboard_users: int = 5
    dashboard_hours_day: int = 8
    dashboard_days_month: int = 22
    refresh_seconds: int = 30
    stream_query_mib: float = 64
    batch_query_mib: float = 10
    other_query_tib_month: float = 2
    api_average_seconds: float = 0.5
    logging_gib_month: float = 20
    monitoring_network_reserve_month: float = 10
    margin: float = 0.25
    fx_pen_per_usd: float = 4


def mean_retained_days(retention, days):
    r = min(retention, days)
    return r - r * r / (2 * days)


def estimate(a):
    hours = a.days * 24
    events = a.devices * a.days * 86400 / a.interval_seconds
    stream_gib = events * a.event_bytes / GIB
    batch_gib = a.batch_records_day * a.days * a.batch_record_bytes / GIB
    batch_worker_hours = a.batch_workers * a.batch_hours_day * a.days
    # Jobs independientes activos-activos conservan dos recepciones en Silver.
    # Las réplicas zonales internas de BigQuery no se facturan como dos tablas.
    bq_average = ((stream_gib * a.stream_jobs + batch_gib) * a.bq_bytes_factor / a.days
                  * mean_retained_days(a.bq_retention_days, a.days)
                  + a.gold_gib_month * 12 / 2 + a.reference_gib
                  + batch_gib / a.days * mean_retained_days(7, a.days))
    gcs_average = batch_gib / a.days * mean_retained_days(a.raw_retention_days, a.days) + a.temp_gcs_average_gib
    cycles_month = a.dashboard_users * a.dashboard_hours_day * 3600 / a.refresh_seconds * a.dashboard_days_month
    requests_month = cycles_month * 7
    # Conservador: no se descuenta caché de BQ ni coincidencia de caché entre usuarios.
    query_tib_month = cycles_month * (a.stream_query_mib + a.batch_query_mib) / 1024**2 + a.other_query_tib_month
    api_seconds_month = requests_month * a.api_average_seconds
    engine = a.stream_jobs * (stream_gib * a.engine_volume_multiplier * RATES['engine_processed_gib']
              if a.engine_model == 'processed' else hours * a.secu_per_hour * RATES['secu_h'])
    raw_average = gcs_average - a.temp_gcs_average_gib
    raw_rate = 2 * RATES['gcs_dual_component_gib_h'] if a.raw_dual_region else RATES['gcs_gib_h']
    gcs_cost = (raw_average * raw_rate + a.temp_gcs_average_gib * RATES['gcs_gib_h']) * hours
    gcs_cost += batch_gib * RATES['gcs_dual_replication_gib'] if a.raw_dual_region else 0
    # Presupuesto conservador: las 50.000 operaciones A/mes usan la tarifa dual.
    a_rate = RATES['gcs_dual_a_1000'] if a.raw_dual_region else RATES['gcs_a_1000']
    gcs_cost += 12 * (50000 / 1000 * a_rate + 200000 / 1000 * RATES['gcs_b_1000'])
    items = {
        'Dataflow streaming CPU y memoria': a.stream_jobs * a.stream_workers * hours * (2 * RATES['stream_cpu_h'] + 7.5 * RATES['memory_gib_h']),
        'Streaming Engine': engine,
        'Dataflow batch CPU y memoria': batch_worker_hours * (RATES['batch_cpu_h'] + 3.75 * RATES['memory_gib_h']),
        'Discos Dataflow y shuffle batch': (a.stream_jobs * a.stream_workers * hours + batch_worker_hours) * 30 * RATES['disk_gib_h'] + batch_gib * 2 * RATES['batch_shuffle_gib'],
        'BigQuery consultas': query_tib_month * 12 * RATES['bq_query_tib'],
        'BigQuery almacenamiento': bq_average * hours * RATES['bq_storage_gib_h'],
        'BigQuery streaming inserts': a.stream_jobs * stream_gib * a.bq_bytes_factor * GIB / (200 * 1024**2) * RATES['bq_insert_200mib'],
        'Pub/Sub publicacion y entrega': stream_gib * (1 + a.pubsub_subscriptions) / 1024 * RATES['pubsub_tib'],
        'Cloud Storage datos y operaciones': gcs_cost,
        'Cloud Run API y consumidor': 12 * (api_seconds_month * (0.25 * RATES['run_cpu_s'] + 0.25 * RATES['run_memory_gib_s']) + requests_month / 1000000 * RATES['run_million_requests']),
        'Cloud Logging': 12 * a.logging_gib_month * RATES['logging_gib'],
        'Cloud Build y Artifact Registry': 12 * 100 * RATES['build_minute'] + 5 * hours * RATES['registry_gib_h'],
        'Workflows y Scheduler': 12 * 30 * RATES['workflow_1000'] + 3 * a.days / 31 * RATES['scheduler_job_31days'],
        'Reserva de Monitoring y red': 12 * a.monitoring_network_reserve_month,
    }
    subtotal = sum(items.values())
    return dict(assumptions=asdict(a),
                usage=dict(stream_events_year=events, batch_records_year=a.batch_records_day*a.days,
                           stream_ingress_gib_year=stream_gib, batch_ingress_gib_year=batch_gib,
                           batch_worker_hours_year=batch_worker_hours, stream_worker_hours_year=a.stream_jobs*a.stream_workers*hours,
                           bq_average_gib_year=bq_average, gcs_average_gib_year=gcs_average,
                           query_tib_month=query_tib_month, api_requests_month=requests_month,
                           api_instance_hours_month=api_seconds_month/3600),
                items_usd_year={k:round(v,2) for k,v in items.items()},
                subtotal_usd_year=round(subtotal,2), contingency_usd_year=round(subtotal*a.margin,2),
                budget_usd_year=round(subtotal*(1+a.margin),2),
                budget_usd_month_average=round(subtotal*(1+a.margin)/12,2),
                budget_pen_year=round(subtotal*(1+a.margin)*a.fx_pen_per_usd,2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--pen-per-usd',type=float,default=4)
    args=parser.parse_args()
    if args.pen_per_usd<=0:parser.error('El tipo de cambio supuesto debe ser positivo')
    a=Assumptions(fx_pen_per_usd=args.pen_per_usd)
    scenarios={
        'base':a,
        'dos_workers_streaming':replace(a,stream_workers=2),
        'secu_dos_unidades_hora':replace(a,engine_model='secu'),
        'dos_workers_y_cuatro_secu_hora':replace(a,stream_workers=2,engine_model='secu',secu_per_hour=4),
        'refresco_cinco_segundos':replace(a,refresh_seconds=5),
        'redundancia_zonal_y_archivo_dual':replace(a,stream_jobs=2,pubsub_subscriptions=2,
            raw_dual_region=True,logging_gib_month=40,monitoring_network_reserve_month=15),
    }
    result=dict(region='us-central1', rate_date='2026-11-20', currency='USD',
                official_calculator_saved_quote=False, free_tier_applied=False,
                actual_billing='NO VERIFICADO', rates=RATES,
                scenarios={name:estimate(config) for name,config in scenarios.items()})
    output=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if args.output:args.output.write_text(output)
    print(output,end='')


if __name__=='__main__':main()
