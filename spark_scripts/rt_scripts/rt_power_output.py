from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, lead, avg
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("PowerOutputStreamer") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "my_topic") \
    .option("maxOffsetsPerTrigger", 100) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
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
    .select("data.TimeStamp", "data.RotorSpeed", "data.GeneratorSpeed", "data.GeneratorTemperature", "data.WindSpeed", "data.MaxWindHeute", "data.PowerOutput")

parsed_df = parsed_df.select("TimeStamp", "PowerOutput")

minute_df = parsed_df.withWatermark("TimeStamp", "2 minutes") \

#Window functions on streaming data frames need to be time based!
minute_df = minute_df.withColumn("window", window("TimeStamp", "2 minutes"))
agg_df = minute_df.groupBy("window").agg(avg("PowerOutput").alias("averagePower"))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

def write_latest_to_postgres(batch_df, epoch_id):
    from pyspark.sql.functions import col

    # Get the latest 15 records
    latest_df = batch_df \
        .withColumn("window_start", col("window.start")) \
        .withColumn("window_end", col("window.end")) \
        .drop("window") \
        .orderBy(col("window_start").desc()).limit(15)

    # Write to PostgreSQL with truncate + overwrite
    latest_df.write \
        .option("truncate", "true") \
        .jdbc(url=jdbc_url, table="power_output_rt", mode="append", properties=connection_properties)

agg_df.writeStream \
    .foreachBatch(write_latest_to_postgres) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoints_po") \
    .start() \
    .awaitTermination()
