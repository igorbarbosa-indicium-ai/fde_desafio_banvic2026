import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor

INCOMING_DIR = Path("/data-src/incoming")
EXTRACTED_DIR = INCOMING_DIR / "extracted"
PROCESSED_DIR = INCOMING_DIR / "processed"


def has_pending_zip() -> bool:
    return any(INCOMING_DIR.glob("*.zip"))


def unpack_latest_zip() -> dict[str, str]:
    from app.extraction import extract_zip

    archives = sorted(INCOMING_DIR.glob("*.zip"), key=lambda path: path.stat().st_mtime)
    if not archives:
        raise FileNotFoundError(f"No ZIP file found in {INCOMING_DIR}")

    archive = archives[-1]
    destination = EXTRACTED_DIR / archive.stem
    extracted_files = extract_zip(archive, destination)
    csv_files = sorted(path for path in extracted_files if path.suffix.lower() == ".csv")
    if not csv_files:
        raise ValueError(f"No CSV files found in {archive.name}")

    tap_files = [
        {"entity": re.sub(r"[^a-zA-Z0-9_]", "_", path.stem), "path": str(path)}
        for path in csv_files
    ]
    return {"tap_files": json.dumps(tap_files), "archive": str(archive)}


def mark_archive_processed(**context) -> None:
    result = context["ti"].xcom_pull(task_ids="unpack_zip")
    archive = Path(result["archive"])
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(archive), str(PROCESSED_DIR / archive.name))


with DAG(
    dag_id="daily_csv_to_postgres",
    description="Unpack new CSV archives and load them into the PostgreSQL warehouse.",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["elt", "meltano"],
) as dag:
    wait_for_archive = PythonSensor(
        task_id="wait_for_archive",
        python_callable=has_pending_zip,
        poke_interval=3600,
        timeout=24 * 60 * 60,
        mode="reschedule",
    )

    unpack_zip = PythonOperator(
        task_id="unpack_zip",
        python_callable=unpack_latest_zip,
    )

    run_meltano = BashOperator(
        task_id="meltano_csv_to_postgres",
        bash_command="meltano run tap-csv target-postgres",
        cwd="/opt/elt",
        env={"TAP_CSV_FILES": "{{ ti.xcom_pull(task_ids='unpack_zip')['tap_files'] }}"},
        append_env=True,
    )

    archive_processed = PythonOperator(
        task_id="archive_processed_zip",
        python_callable=mark_archive_processed,
    )

    wait_for_archive >> unpack_zip >> run_meltano >> archive_processed