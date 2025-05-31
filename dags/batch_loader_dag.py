from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {
    'start_date': datetime(2025, 1, 1),
    'retries': 0,
}

with DAG(
    'batch_loader',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    upload_csvs = BashOperator(
        task_id='upload_csvs_to_hdfs',
        bash_command='bash /opt/airflow/scripts/batch_loader.sh',
        dag=dag,
        provide_context=False,
    )
