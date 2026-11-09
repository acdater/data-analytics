import argparse
from dataclasses import replace
import json
import resource
import sys
import time
from arcadia.common.config import ROOT, load_config
from arcadia.common.db import engine
from arcadia.generator.simulate import generate
from arcadia.ingestion.load import load
from arcadia.ingestion.validate import validate


def main():
    parser = argparse.ArgumentParser(description="Generate and validate synthetic Dungeon Rush data")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    generation = sub.add_parser("generate")
    generation.add_argument("--profile", choices=["development", "portfolio"], default="development")
    generation.add_argument("--batch-size", type=int, default=5000)
    generation.add_argument("--replace", action="store_true", help="Atomically replace Arcadia data only")
    generation.add_argument("--seed", type=int)
    sub.add_parser("validate")
    args = parser.parse_args()
    started = time.perf_counter()
    db = engine()
    raw = db.raw_connection()
    connection = raw.driver_connection
    try:
        if args.command == "init":
            connection.execute((ROOT / "database/schema/001_schema.sql").read_text())
            result = {"schema": "arcadia", "status": "ready"}
        elif args.command == "generate":
            config = load_config(args.profile)
            if args.seed is not None:
                config = replace(config, seed=args.seed)
            result = load(connection, config, generate(config), args.batch_size, args.replace)
            validation_started = time.perf_counter()
            result["generation_seconds"] = round(validation_started-started, 3)
            result["validation"] = validate(connection)
            result["validation_seconds"] = round(time.perf_counter()-validation_started, 3)
            if not result["validation"]["passed"]:
                raise ValueError(f"Validation failed; transaction rolled back: {result['validation']['checks']}")
        else:
            result = validate(connection)
            if not result["passed"]:
                print(json.dumps(result, indent=2))
                raise SystemExit(1)
        connection.commit()
        result["elapsed_seconds"] = round(time.perf_counter()-started, 3)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_mib"] = round(rss/(1024*1024 if sys.platform == "darwin" else 1024), 2)
        print(json.dumps(result, indent=2))
    finally:
        connection.rollback()
        raw.close()
        db.dispose()

if __name__ == "__main__":
    main()
