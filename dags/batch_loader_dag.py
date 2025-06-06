import subprocess
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def execute_load_script():
    try:
        subprocess.run(['/opt/airflow/scripts/batch_loader.sh'], check=True)
        print(f"Batch Loader Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error trying to load batch data (batch_loader.sh): {e}")
        raise

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025,6,6),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'run_load_script_on_airflow_start',
    default_args=default_args,
    description='Run batch_loader.sh daily, after Airflow starts',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    # Task to run the load.sh script
    run_load_script_task = PythonOperator(
        task_id='run_load_script',
        python_callable=execute_load_script,
    )

    # Run the batch_loader.sh script immediately once the DAG starts
    run_load_script_task
