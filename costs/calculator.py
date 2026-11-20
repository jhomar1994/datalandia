"""Estimación parametrizada de primer año; no sustituye Cloud Billing.

Tarifas de lista USD us-central1 consultadas 2026-11-20. Sin free tier ni créditos.
SECU y otros consumos son supuestos de planificación, no mediciones de capacidad.
"""
import argparse
import json


def estimate(stream_hours_month, fx):
    # Worker: 2 vCPU, 7,5 GiB. Disco presupuestado a 0,05 USD/GiB-mes
    # como reserva (no tarifa verificada). SECU: supuesto 2 unidades-hora/h.
    items = {
        'dataflow_batch_cpu_memory': 10 * (0.056 + 3.75 * 0.003557),
        'dataflow_stream_cpu_memory': stream_hours_month * (2 * 0.069 + 7.5 * 0.003557),
        'streaming_engine_planning': stream_hours_month * 2 * 0.089,
        'worker_disks_reserve': 30 * 0.05 * (10 + stream_hours_month) / 730,
        'bigquery_queries': 0.1 * 6.25,
        'bigquery_storage': 10 * 0.023,
        'bigquery_stream_inserts_reserve': 0.5,
        'pubsub_publish_subscribe': 2 / 1024 * 40,
        'gcs_storage_operations_reserve': 2.0,
        'cloud_run_requests_compute_reserve': 1.0,
        'build_registry_logging_workflows_reserve': 2.0,
    }
    subtotal = sum(items.values())
    monthly = subtotal * 1.3
    return {'stream_hours_month': stream_hours_month, 'items_usd_month': {k:round(v,4) for k,v in items.items()},
            'contingency_fraction':0.3, 'usd_month':round(monthly,2), 'usd_year':round(monthly*12,2),
            'pen_year':round(monthly*12*fx,2)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pen-per-usd',type=float,default=4.0,help='Supuesto editable, no cotización de mercado')
    args=p.parse_args()
    if args.pen_per_usd <= 0:
        p.error('El tipo de cambio debe ser positivo')
    result={'date':'2026-11-20','region':'us-central1','fx_assumption_pen_per_usd':args.pen_per_usd,
            'actual_bill':'NO VERIFICADO','credits_free_tier_applied':False,
            'assumptions':{'batch_hours_month':10,'query_tib_month':0.1,'average_bq_gib':10,
                           'pubsub_throughput_gib_month':2,'secu_per_stream_hour':2,
                           'secu_sizing_verified':False,'retention':'Mantener almacenamiento medio de 10 GiB; requiere política de purga para crecimiento continuo'},
            'on_demand':estimate(10,args.pen_per_usd),'continuous':estimate(730,args.pen_per_usd)}
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
