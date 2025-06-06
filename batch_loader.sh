#!/bin/bash

HDFS_CONTAINER="namenode"
BATCH_DIR="/opt/airflow/batch"
HDFS_BASE_DIR="/user/hadoop/raw"

echo "Waiting for HDFS..."
until docker exec "$HDFS_CONTAINER" hdfs dfsadmin -report &>/dev/null; do
    sleep 2
done
echo "Copying batch data to HDFS"

find "$BATCH_DIR" -type f | while read -r filepath; do
    rel_path="${filepath#$BATCH_DIR/}"
    hdfs_path="$HDFS_BASE_DIR/$rel_path"
    hdfs_dir=$(dirname "$hdfs_path")
    filename=$(basename "$filepath")

    echo "Copying and uploading $filename to $hdfs_path"
    docker exec "$HDFS_CONTAINER" hdfs dfs -mkdir -p "$hdfs_dir"
    docker cp "$filepath" "$HDFS_CONTAINER:/tmp/"
    docker exec "$HDFS_CONTAINER" hdfs dfs -put -f "/tmp/$(basename $filepath)" "$hdfs_path"
done

echo "Done uploading batch data"
