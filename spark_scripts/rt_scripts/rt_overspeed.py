from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, lag, when, sum, expr, count
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("OverspeedStreamer") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "my_topic") \
    .option("maxOffsetsPerTrigger", 100) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .option("groupId", "3") \
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
    .select("data.TimeStamp", "data.GeneratorSpeed", "data.RotorSpeed")

speed_df = parsed_df.withWatermark("TimeStamp", "4 minutes").withColumn("isOverspeed", ((col("GeneratorSpeed") > 10) | (col("RotorSpeed") > 10)))

speed_df = speed_df.withColumn("timeWindow", window("TimeStamp", "2 minutes"))

result = speed_df.groupBy("timeWindow") \
    .agg(
        count("*").alias("total"),
        sum(when(col("isOverspeed") == 1, 1).otherwise(0)).alias("overspeed_duration")
    ) \
    .withColumn("overspeed_percent", (col("overspeed_duration") / col("total")) * 100)

# Flatten the window struct
flattened_result = result \
    .withColumn("window_start", col("timeWindow.start")) \
    .withColumn("window_end", col("timeWindow.end")) \
    .drop("timeWindow", "total")

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

def write_to_postgres(microbatch_df, epoch_id):
    microbatch_df.write \
        .jdbc(url=jdbc_url, table="overspeed_output_rt", mode="append", properties=connection_properties)

flattened_result.writeStream \
    .foreachBatch(write_to_postgres) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoints_overspeed") \
    .trigger(processingTime="2 minutes") \
    .start() \
    .awaitTermination()
