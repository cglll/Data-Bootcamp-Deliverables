from datetime import timedelta
from airflow import DAG
import airflow.utils.dates
from custom_modules.s3_to_postgres import S3ToPostgresOperator
from cryptography.fernet import Fernet
import os

# fernet_key = Fernet.generate_key()
# os.environ["AIRFLOW__CORE__FERNET_KEY"] = "Y0ZCeE0wdFJZVFphTkVveE5IaFJjRGhrWmpCamJ6RlJhak5vZVZwclIxaz0="

default_args = {
    'owner': 'geovanni.velazquez',
    'depends_on_past': False,
    'start_date': airflow.utils.dates.days_ago(1),
    'retry_delay': timedelta(minutes=5)
}

dag = DAG('dag_insert_data_postgres', 
          default_args=default_args,
          schedule_interval='@once')

process_data = S3ToPostgresOperator(task_id='dag_s3_to_postgres',
                                    schema='debootcamp',
                                    table='products',
                                    s3_bucket='de-bootcamp-airflow-data',
                                    s3_key='sample.csv',
                                    postgres_conn_id='postgres_default',
                                    aws_conn_id='aws_default',
                                    dag=dag)
