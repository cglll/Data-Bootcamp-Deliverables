from datetime import timedelta
from airflow import DAG
import airflow.utils.dates

# Append custom modules to path. If this is not done logs will not show up
# possibly due to a timeout
import sys

sys.path.append("/opt/airflow/dags/repo/custom_modules")

from airflow.providers.amazon.aws.operators.emr_containers import \
    EMRContainerOperator
from s3_to_postgres import S3ToPostgresOperator
from postgres_to_s3 import PostgresToS3Operator
from airflow.operators.python import PythonOperator

# [START EMRContainer operator variables]
virtual_cluster_id = '{{conn.aws_default.extra_dejson["virtual_cluster_id"]}}'
JOB_ROLE_ARN = "arn:aws:iam::855157247171:role/EMRContainers-JobExecutionRole"
spark_image = "855157247171.dkr.ecr.us-east-2.amazonaws.com/emr6.3_custom_repo"
# [END EMRContainerOperator variables]

# [START EMRContainerOperator config]
JOB_DRIVER_ARG = {
    "sparkSubmitJobDriver": {
        "entryPoint": "s3://spark-test-samp/classify_reviews.py",
        "sparkSubmitParameters": "--conf spark.executors.instances=2"
                                 " --conf spark.executors.memory=2G"
                                 " --conf spark.executor.cores=2"
                                 " --conf spark.driver.cores=1"
    }
}

CONFIGURATION_OVERRIDES_ARG = {
    "applicationConfiguration": [
        {
            "classification": "spark-defaults",
            "properties": {
                "spark.dynamicAllocation.enabled": "false",
                "spark.kubernetes.executor.deleteOnTermination": "true",
                "spark.kubernetes.container.image": spark_image,
                "spark.hadoop.fs.s3a.multiobjectdelete.enable": "false"
            }
        }
    ],
    "monitoringConfiguration": {
        "cloudWatchMonitoringConfiguration": {
            "logGroupName": "/emr-on-eks/eksworkshop-eksctl",
            "logStreamNamePrefix": "pi"
        },
        "s3MonitoringConfiguration": {
            "logUri": "s3://spark-test-samp"
        }
    }
}


# [END EMRContainerOperator config]

def get_bucket_name():
    """
    Reads the bucket names in S3.

    Gets the raw and staging layer buckets' full name and assigns them
        to a dictionary.

    Returns:
        buckets: dict
          Dictionary with the name of the raw and staging layer buckets.
    """
    from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
    s3 = AwsBaseHook(aws_conn_id="aws_default", client_type="s3")
    response = s3.conn.list_buckets()
    bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
    raw_name = ""
    staging_name = ""
    for i in bucket_names:
        if i.startswith("raw-layer"):
            raw_name = i
        if i.startswith("staging-layer"):
            staging_name = i
    buckets = {"raw": raw_name, "staging": staging_name}
    return buckets

# DAG Start
# ----------------------------------------------------------------------------
default_args = {
    'owner': 'geovanni.velazquez',
    'depends_on_past': False,
    'start_date': airflow.utils.dates.days_ago(1),
    'retry_delay': timedelta(minutes=5)
}

dag = DAG('dag_insert_data_postgres',
          default_args=default_args,
          schedule_interval='@once',
          catchup=False,
          tags=['s3_postgres'])

with dag:
    get_bucket_names = PythonOperator(task_id="get_s3_bucket_names",
                                      python_callable=get_bucket_name,
                                      dag=dag)

    # Save raw data to postgres from the user_purchase.csv file. Afterwards
    # the same data is extracted from postgres and sent to the staging layer
    # bucket created with terraform.
    process_data = S3ToPostgresOperator(task_id='s3_to_postgres',
                                        schema='debootcamp',
                                        table='products',
                                        s3_key='user_purchase.csv',
                                        postgres_conn_id='postgres_default',
                                        aws_conn_id='aws_default',
                                        dag=dag
                                        )

    pg_to_staging = PostgresToS3Operator(task_id='postgres_to_staging_layer',
                                         schema='debootcamp',
                                         table='products',
                                         s3_bucket='de-bootcamp-airflow-data',
                                         s3_key='sample.csv',
                                         postgres_conn_id='postgres_default',
                                         aws_conn_id='aws_default',
                                         dag=dag
                                         )

    # Classifies the movie_reviews.csv file by looking for the word "good".
    # Assigns a 1 if the word is found else a 0. Saves file with cid and
    # class (called the "positivity" column) columns only.
    reviews_job = EMRContainerOperator(
        task_id="movie_reviews_classification",
        virtual_cluster_id=virtual_cluster_id,
        execution_role_arn=JOB_ROLE_ARN,
        configuration_overrides=CONFIGURATION_OVERRIDES_ARG,
        release_label="emr-6.3.0-latest",
        job_driver=JOB_DRIVER_ARG,
        name="movie_reviews.py"
    )

    # fan out after getting the names of the buckets created with terraform
    get_bucket_names >> [process_data, reviews_job]

    process_data >> pg_to_staging
