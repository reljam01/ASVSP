from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, abs, window, mean, stddev
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("SpeedDifferenceStreamer") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "my_topic") \
    .option("maxOffsetsPerTrigger", 100) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .option("groupId", "4") \
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
    .select("data.TimeStamp", "data.RotorSpeed", "data.GeneratorSpeed")

diff_df = parsed_df.withColumn("speedDiff", abs(col("RotorSpeed") - col("GeneratorSpeed")))

diff_df = diff_df.withWatermark("TimeStamp", "2 minutes")

stats_df = diff_df.groupBy(window("TimeStamp", "2 minutes").alias("timeWindow")) \
    .agg(mean("speedDiff").alias("avgDiff"), stddev("speedDiff").alias("devDiff")) \
    .withColumn("window_start", col("timeWindow.start")) \
    .withColumn("window_end", col("timeWindow.end")) \
    .drop("timeWindow")

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

def write_to_postgres(microbatch_df, epoch_id):
    microbatch_df.write \
        .jdbc(url=jdbc_url, table="speed_outliers_rt", mode="overwrite", properties=connection_properties)

stats_df.writeStream \
    .foreachBatch(write_to_postgres) \
    .outputMode("complete") \
    .option("checkpointLocation", "/tmp/checkpoints_speed") \
    .trigger(processingTime="2 minutes") \
    .start() \
    .awaitTermination()
