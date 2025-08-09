from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, lag
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("KafkaParquetLoader") \
    .getOrCreate()

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "my_topic") \
    .option("startingOffsets", "latest") \
    .option("groupId", "2") \
    .load()

schema = StructType() \
    .add("TimeStamp",TimestampType()) \
    .add("RotorSpeed",FloatType()) \
    .add("GeneratorSpeed",FloatType()) \
    .add("GeneratorTemperature",FloatType()) \
    .add("WindSpeed",FloatType()) \
    .add("PowerOutput",FloatType()) \
    .add("SpeiseSpannung",FloatType()) \
    .add("StatusAnlage",IntegerType()) \
    .add("MaxWindHeute",FloatType()) \
    .add("PitchDeg",FloatType()) \

parsed_df = df.selectExpr("CAST(value AS STRING) as json_string") \
    .select(from_json(col("json_string"), schema).alias("data")) \
    .select("data.TimeStamp", "data.PowerOutput")

minute_df = parsed_df.withWatermark("data.Timestamp", "2 minutes") \
    .groupBy(window("data.Timestamp", "1 minute")) \
    .agg({"data.PowerOutput":"avg"}) \
    .withColumnRenamed("avg(data.PowerOutput)", "averagePower")

w = Window.orderBy("window.start")
delta_df = minute_df \
    .withColumn("prevAveragePower", lag("averagePower").over(w)) \
    .withColumn("delta", col("averagePower") - col("prevAveragePower"))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

def write_latest_to_postgres(batch_df, epoch_id):
    from pyspark.sql.functions import col

    # Get the latest 15 records
    latest_df = batch_df.orderBy(col("timestamp").desc()).limit(15)

    # Write to PostgreSQL with truncate + overwrite
    latest_df.write \
        .option("truncate", "true") \
        .jdbc(url=jdbc_url, table="power_output_rt", mode="overwrite", properties=connection_properties)

delta_df.writeStream \
    .foreachBatch(write_latest_to_postgres) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoints_po") \
    .start() \
    .awaitTermination()
