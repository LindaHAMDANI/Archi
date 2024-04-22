# Import Python dependencies needed for the workflow
from urllib import request
from minio import Minio, S3Error
from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import pendulum
import os
import urllib.error


def download_parquet(**kwargs):
    # folder_path: str = r'..\..\data\raw'
    # Construct the relative path to the folder
    url: str = "https://d37ci6vzurychx.cloudfront.net/trip-data/"
    filename: str = "yellow_tripdata"
    extension: str = ".parquet"

    month: str = pendulum.now().subtract(months=2).format('YYYY-MM')
    try:
        request.urlretrieve(f"{url}{filename}_{month}{extension}", f"yellow_tripdata_{month}.parquet")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to download the parquet file : {str(e)}") from e


# Python Function
def upload_file(**kwargs):
    ###############################################
    # Upload generated file to Minio

    client = Minio(
        "minio:9001",
        secure=False,
        access_key="minio",
        secret_key="minio123"
    )
    bucket: str = 'rawnyc'

    month: str = pendulum.now().subtract(months=2).format('YYYY-MM')
    print(client.list_buckets())

    client.fput_object(
        bucket_name=bucket,
        object_name=f"yellow_tripdata_{month}.parquet",
        file_path=f"yellow_tripdata_{month}.parquet"
    )
    # On supprime le fichié récement téléchargés, pour éviter la redondance. On suppose qu'en arrivant ici, l'ajout est
    # bien réalisé
    os.remove(os.path.join("./", "yellow_tripdata_" + month + ".parquet"))


###############################################
with DAG(dag_id='Grab NYC Data to Minio',
         start_date=days_ago(1),
         schedule_interval="0 0 1 * *", # Expression cron pour exécuter tous les premiers du mois à minuit
         tags=['minio/read/write'],
         ) as dag:
    ###############################################
    # Create a task to call your processing function
    t1 = PythonOperator(
        task_id='download_parquet',
        provide_context=True,
        python_callable=download_parquet
    )
    t2 = PythonOperator(
        task_id='upload_file_task',
        provide_context=True,
        python_callable=upload_file
    )
###############################################  

###############################################
# first upload the file, then read the other file.
t1 >> t2
###############################################
