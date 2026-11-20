"""Publica replay histórico con destino explícito y concurrencia acotada."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="proyecto-datalandia")
    parser.add_argument("--topic", default="lumina-eventos")
    parser.add_argument("--input", type=Path, default=ROOT / "data/p3/input/sensores.jsonl")
    parser.add_argument("--limit", type=int, default=11000)
    parser.add_argument("--rate", type=float, default=20, help="Eventos por segundo")
    parser.add_argument("--errores", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Valida y cuenta sin publicar")
    parser.add_argument("--output", type=Path, help="Guarda el replay con published_at; requiere --dry-run")
    args = parser.parse_args()
    if args.limit < 1 or args.rate <= 0:
        parser.error("limit y rate deben ser positivos")
    if args.output and not args.dry_run:
        parser.error("--output requiere --dry-run")
    replay = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        replay = args.output.open("x")
    client = None
    pending = []
    if not args.dry_run:
        from google.cloud import pubsub_v1
        client = pubsub_v1.PublisherClient()
        topic = client.topic_path(args.project, args.topic)
    count = 0
    last = None
    start = time.monotonic()
    try:
        with args.input.open() as source:
            for line in source:
                if count >= args.limit:
                    break
                event = json.loads(line)
                if not isinstance(event, dict) or not event.get("event_id"):
                    raise ValueError("Evento sin identificador")
                event["published_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                last = event
                if replay:
                    replay.write(json.dumps(event) + "\n")
                if client:
                    pending.append(client.publish(topic, json.dumps(event).encode(), event_id=event["event_id"]))
                    if len(pending) >= 100:
                        for future in pending:
                            future.result(timeout=60)
                        pending.clear()
                count += 1
                if client:
                    time.sleep(max(0, start + count / args.rate - time.monotonic()))
        if args.errores:
            if last is None:
                raise ValueError("No hay eventos de base para inyectar el error")
            event = dict(last, event_id="demo_error_valor", value="error")
            if replay:
                replay.write(json.dumps(event) + "\n")
            if client:
                pending.append(client.publish(topic, json.dumps(event).encode(), event_id=event["event_id"]))
            count += 1
        for future in pending:
            future.result(timeout=60)
    finally:
        if replay:
            replay.close()
        if client:
            client.stop()
    print(json.dumps({
        "project": args.project, "topic": args.topic, "events": count,
        "published": not args.dry_run, "rate": args.rate,
    }))


if __name__ == "__main__":
    main()
