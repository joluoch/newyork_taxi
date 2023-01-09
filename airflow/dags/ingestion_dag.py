import os
import logging

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from datetime import datetime
from google.cloud import storage
#from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateExternalTableOperator
import pyarrow.csv as pv
import pyarrow.parquet as pq

PROJECT_ID = 'freshthinker'
BUCKET = 'dtc_data_lake_freshthinker'

AIRFLOW_HOME = os.environ.get("AIRFLOW_HOME", "/opt/airflow/")
# dataset_file = "yellow_tripdata_2021-01.parquet"
# dataset_url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{dataset_file}"
#path_to_local_home = os.environ.get("AIRFLOW_HOME", "/opt/airflow/")
# parquet_file = dataset_file
# BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", 'trips_data_all')


# NOTE: takes 20 mins, at an upload speed of 800kbps. Faster if your internet has a better upload speed
def upload_to_gcs(bucket, object_name, local_file):
    """
    Ref: https://cloud.google.com/storage/docs/uploading-objects#storage-upload-object-python
    :param bucket: GCS bucket name
    :param object_name: target path & file-name
    :param local_file: source path & file-name
    :return:
    """
    # WORKAROUND to prevent timeout for files > 6 MB on 800 kbps upload speed.
    # (Ref: https://github.com/googleapis/python-storage/issues/74)
    storage.blob._MAX_MULTIPART_SIZE = 5 * 1024 * 1024  # 5 MB
    storage.blob._DEFAULT_CHUNKSIZE = 5 * 1024 * 1024  # 5 MB
    # End of Workaround

    client = storage.Client()
    bucket = client.bucket(bucket)

    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_file)


default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
    "depends_on_past": False,
    "retries": 1,
}

URL_PREFIX = 'https://d37ci6vzurychx.cloudfront.net/trip-data' 

# YELLOW_URL_TEMPLATE = URL_PREFIX + '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.parquet'
# YELLOW_TAXI_PARQUET_FILE_TEMPLATE = AIRFLOW_HOME + '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.parquet'
# YELLOW_TAXI_GCS_PATH_TEMPLATE = "raw/yellow_tripdata/{{ execution_date.strftime(\'%Y\') }}/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.parquet"
#TABLE_NAME_TEMPLATE = 'yellow_taxi_{{ execution_date.strftime(\'%Y_%m\') }}'
YELLOW_URL_TEMPLATE = URL_PREFIX + '/yellow_tripdata_2021-01.parquet'
YELLOW_TAXI_PARQUET_FILE_TEMPLATE = AIRFLOW_HOME + '/yellow_tripdata_2021-01.parquet'
YELLOW_TAXI_GCS_PATH_TEMPLATE = "raw/yellow_tripdata/yellow_tripdata_2021-01.parquet"
#https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2021-01.parquet

GREEN_URL_TEMPLATE = URL_PREFIX + '/green_tripdata_2021-01.parquet'
GREEN_TAXI_PARQUET_FILE_TEMPLATE = AIRFLOW_HOME + '/green_tripdata_2021-01.parquet'
GREEN_TAXI_GCS_PATH_TEMPLATE = "raw/green_tripdata/green_tripdata_2021-01.parquet"

FHV_URL_TEMPLATE = URL_PREFIX + '/fhv_tripdata_2021-01.parquet'
FHV_TAXI_PARQUET_FILE_TEMPLATE = AIRFLOW_HOME + '/fhv_tripdata_2021-01.parquet'
FHV_TAXI_GCS_PATH_TEMPLATE = "raw/FHV/fhv_tripdata_2021-01.parquet"
#https://d37ci6vzurychx.cloudfront.net/trip-data/fhv_tripdata_2021-01.parquet
with DAG(
    dag_id="yellow_taxi_data",
    schedule_interval="0 6 2 * *",
    default_args=default_args,
    catchup=True,
    max_active_runs=1,
    tags=['dtc-de'],
) as yellow_taxi_data:

    download_dataset_task = BashOperator(
        task_id="download_dataset_task",
        bash_command=f"curl -sSLf {FHV_URL_TEMPLATE} > {FHV_TAXI_PARQUET_FILE_TEMPLATE}"
    )

    local_to_gcs_task = PythonOperator(
        task_id="local_to_gcs_task",
        python_callable=upload_to_gcs,
        op_kwargs={
            "bucket": BUCKET,
            "object_name": FHV_TAXI_GCS_PATH_TEMPLATE,
            "local_file": FHV_TAXI_PARQUET_FILE_TEMPLATE,
        },
    )

    rm_task = BashOperator(
        task_id="rm_task",
        bash_command=f"rm{FHV_TAXI_PARQUET_FILE_TEMPLATE}"
    )

    # bigquery_external_table_task = BigQueryCreateExternalTableOperator(
    #     task_id="bigquery_external_table_task",
    #     table_resource={
    #         "tableReference": {
    #             "projectId": PROJECT_ID,
    #             "datasetId": BIGQUERY_DATASET,
    #             "tableId": "external_table",
    #         },
    #         "externalDataConfiguration": {
    #             "sourceFormat": "PARQUET",
    #             "sourceUris": [f"gs://{BUCKET}/raw/{parquet_file}"],
    #         },
    #     },
    # )
    download_dataset_task >> local_to_gcs_task >> rm_task