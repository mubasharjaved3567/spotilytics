import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

LOG_DIR             = Path("logs")
RAW_REPORT_PATH     = LOG_DIR / "validation_raw.json"
CLEANED_REPORT_PATH = LOG_DIR / "validation_cleaned.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)


def _check(name: str, result: bool) -> dict:
    return {"check": name, "passed": bool(result)}


def validate_raw(csv_path: Path) -> dict:
    print("🔍 Validating raw data...")
    logger.info("Starting raw validation on %s", csv_path)

    pdf = pd.read_csv(csv_path)
    if "Unnamed: 0" in pdf.columns:
        pdf = pdf.drop(columns=["Unnamed: 0"])

    checks = [
        _check("required_columns_present", all(c in pdf.columns for c in [
            "track_id", "track_name", "artist_name", "genre",
            "popularity", "year", "danceability", "energy",
            "loudness", "tempo", "valence", "acousticness",
            "speechiness", "instrumentalness", "liveness", "duration_ms",
        ])),
        _check("row_count_above_1m",         len(pdf) >= 1_000_000),
        _check("track_id_not_null",          pdf["track_id"].notna().all()),
        _check("track_id_unique",            pdf["track_id"].is_unique),
        _check("artist_name_not_null",       pdf["artist_name"].notna().all()),
        _check("track_name_not_null",        pdf["track_name"].notna().all()),
        _check("popularity_range_0_100",     pdf["popularity"].between(0, 100).all()),
        _check("year_range_2000_2023",       pdf["year"].between(2000, 2023).all()),
        _check("danceability_range_0_1",     pdf["danceability"].between(0, 1).all()),
        _check("energy_range_0_1",           pdf["energy"].between(0, 1).all()),
        _check("valence_range_0_1",          pdf["valence"].between(0, 1).all()),
        _check("acousticness_range_0_1",     pdf["acousticness"].between(0, 1).all()),
        _check("speechiness_range_0_1",      pdf["speechiness"].between(0, 1).all()),
        _check("instrumentalness_range_0_1", pdf["instrumentalness"].between(0, 1).all()),
        _check("liveness_range_0_1",         pdf["liveness"].between(0, 1).all()),
        _check("tempo_positive",             (pdf["tempo"] > 0).all()),
        _check("loudness_negative",          (pdf["loudness"] < 0).all()),
        _check("duration_ms_above_30s",      (pdf["duration_ms"] > 30_000).all()),
    ]

    return _write_report(checks, RAW_REPORT_PATH, stage="raw", strict=False)


def validate_cleaned(df) -> dict:
    print("🔍 Validating cleaned data...")
    logger.info("Starting cleaned validation")

    total       = df.count()
    null_counts = {
        c: df.filter(df[c].isNull()).count()
        for c in ["track_id", "artist_name", "track_name", "genre", "popularity"]
    }
    dup_count = total - df.dropDuplicates(["track_id"]).count()

    stats = df.selectExpr(
        "min(popularity)        as min_pop",
        "max(popularity)        as max_pop",
        "min(year)              as min_year",
        "max(year)              as max_year",
        "min(danceability)      as min_dance",
        "max(danceability)      as max_dance",
        "min(energy)            as min_energy",
        "max(energy)            as max_energy",
        "min(tempo)             as min_tempo",
        "max(loudness)          as max_loud",
        "min(duration_ms)       as min_dur",
        "count(genre_group)     as genre_group_count",
        "count(popularity_tier) as tier_count",
    ).collect()[0]

    checks = [
        _check("row_count_above_1m",             total >= 1_000_000),
        _check("no_duplicate_track_ids",          dup_count == 0),
        _check("track_id_not_null",              null_counts["track_id"] == 0),
        _check("artist_name_not_null",           null_counts["artist_name"] == 0),
        _check("track_name_not_null",            null_counts["track_name"] == 0),
        _check("genre_not_null",                 null_counts["genre"] == 0),
        _check("popularity_not_null",            null_counts["popularity"] == 0),
        _check("popularity_range_0_100",         0 <= stats["min_pop"] and stats["max_pop"] <= 100),
        _check("year_range_2000_2023",           2000 <= stats["min_year"] and stats["max_year"] <= 2023),
        _check("danceability_range_0_1",         0 <= stats["min_dance"] and stats["max_dance"] <= 1),
        _check("energy_range_0_1",               0 <= stats["min_energy"] and stats["max_energy"] <= 1),
        _check("tempo_positive",                 stats["min_tempo"] > 0),
        _check("loudness_negative",              stats["max_loud"] < 0),
        _check("duration_ms_above_30s",          stats["min_dur"] > 30_000),
        _check("genre_group_column_present",     stats["genre_group_count"] == total),
        _check("popularity_tier_column_present", stats["tier_count"] == total),
    ]

    return _write_report(checks, CLEANED_REPORT_PATH, stage="cleaned", strict=True)


def _write_report(checks: list, path: Path, stage: str, strict: bool) -> dict:
    passed = [c for c in checks if c["passed"]]
    failed = [c for c in checks if not c["passed"]]

    report = {
        "stage":     stage,
        "timestamp": datetime.now().isoformat(),
        "total":     len(checks),
        "passed":    len(passed),
        "failed":    len(failed),
        "pass_rate": f"{len(passed)/len(checks)*100:.1f}%",
        "checks":    checks,
    }
    path.write_text(json.dumps(report, indent=2))

    print(f"\n{'─'*48}")
    print(f"  Validation — {stage.upper()}")
    print(f"  {report['passed']}/{report['total']} passed  ({report['pass_rate']})")
    print(f"{'─'*48}")
    for c in checks:
        print(f"  {'✅' if c['passed'] else '❌'}  {c['check']}")
    print(f"{'─'*48}\n")

    if strict and failed:
        raise ValueError(
            f"Cleaned data failed {len(failed)} check(s): "
            + ", ".join(c["check"] for c in failed)
        )

    logger.info("Validation [%s]: %d/%d passed", stage, len(passed), len(checks))
    return report