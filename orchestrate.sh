#!/bin/bash

MY_DIR="$(dirname "$(realpath "$0")")"
"$MY_DIR/batch_loader.sh"

echo "###############################"
echo "Finished loading data into HDFS"
echo "###############################"
sleep 1

CONTAINER_NAME="spark-master"
if ! docker ps --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
    echo "Container is not running. Starting it..."
    docker start "$CONTAINER_NAME"
fi

echo "######################################"
echo "Spark is active, executing batch analysis..."
echo "######################################"

docker exec -it "$CONTAINER_NAME" /bin/bash -c "spark-submit /opt/spark/spark_scripts/transform_batch.py"

echo "##################################"
echo "Transformed batch data! Curating.."
echo "##################################"
sleep 1

for script in "$MY_DIR"/spark_scripts/batch_scripts/*.py; do
    if [ -f "$script" ]; then
        script_name=$(basename "$script")
        echo "Running script: $script_name"
        docker exec -it "$CONTAINER_NAME" /bin/bash -c "spark-submit --packages org.postgresql:postgresql:42.6.0 /opt/spark/spark_scripts/batch_scripts/$script_name"
        sleep 1
    fi
done

echo "Running detached RT scripts (listeners from Kafka)"
echo "$MY_DIR my dir"

for script in "$MY_DIR"/spark_scripts/rt_scripts/*.py; do
    if [ -f "$script" ]; then
        script_name=$(basename "$script")
        echo "Running script: $script_name"
        docker exec -d "$CONTAINER_NAME" /bin/bash -c "spark-submit --packages org.postgresql:postgresql:42.6.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1 --executor-memory 2G --executor-cores 2 --num-executors 2 --driver-memory 2G /opt/spark/spark_scripts/rt_scripts/$script_name > /tmp/$script_name.log 2>&1"
        sleep 60
    fi
done

HDFS_DIR="/user/hadoop/realtime"
HDFS_CONTAINER="namenode"
HDFS_CMD="hdfs dfs -ls $HDFS_DIR"

check_hdfs_directory() {
    file_count=$(docker exec "$HDFS_CONTAINER" $HDFS_CMD | wc -l)

    if [ "$file_count" -gt 1 ]; then
        return 0
    else
        return 1
    fi
}

echo "Waiting for the directory $HDFS_DIR to contain files..."
while ! check_hdfs_directory; do
    echo "Realtime data not yet available. Checking again in 10 seconds..."
    sleep 10
done

sleep 3

echo "Running micro-batch scripts periodically"
while true; do
    echo "Running micro-batch at: $(date)"
    docker exec -it "$CONTAINER_NAME" /bin/bash -c "spark-submit --packages org.postgresql:postgresql:42.6.0 /opt/spark/spark_scripts/microbatch_scripts/mv_temp_micro.py"
    docker exec -it "$CONTAINER_NAME" /bin/bash -c "spark-submit --packages org.postgresql:postgresql:42.6.0 /opt/spark/spark_scripts/microbatch_scripts/mv_wind_micro.py"
    sleep 15
done
