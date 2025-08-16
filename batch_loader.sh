#!/bin/bash

HDFS_CONTAINER="namenode"
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
BATCH_DIR="$SCRIPT_DIR/batch/london"
HDFS_BASE_DIR="/user/hadoop/raw"

echo "Waiting for HDFS..."
until docker exec "$HDFS_CONTAINER" hdfs dfsadmin -report &>/dev/null; do
    sleep 2
done
echo "Copying batch data to HDFS"

echo "BATCH DIR IS: $BATCH_DIR"

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
