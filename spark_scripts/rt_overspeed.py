from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, lag, when, sum, monotonically_increasing
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
    .select("data.TimeStamp", "data.GeneratorSpeed")

speed_df = parsed_df.withColumn("isOverspeed", (col("data.GeneratorSpeed") > 40).cast("int"))

window_df = speed_df.withColumn("timeWindow", window("data.TimeStamp", "15 minutes"))

window_spec = Window.orderBy("data.TimeStamp")
speed_df = speed_df.withColumn("speedLag", lag("isOverspeed").over(window_spec))

speed_df = speed_df.withColumn("overspeedChange", when(col("speedLag") != col("isOverspeed"), 1).otherwise(0))

speed_df = speed_df.withColumn("group_id", sum("overspeedChange").over(window_spec))

overspeed_groups = speed_df.filter(col("isOverspeed") == 1) \
    .groupBy("group_id", "timeWindow") \
    .agg(expr("count(*) as duration")) \
    .filter(col("duration") >= 10)

total_seconds = speed_df.groupBy("time_window").agg(expr("count(*) as total"))
overspeed_seconds = overspeed_groups.groupBy("time_window").agg(expr("sum(duration) as overspeed_duration"))
result = total_seconds.join(overspeed_seconds, "timeWindow", "left") \
    .fillna(0) \
    .withColumn("overspeed_percent", (col("overspeed_duration") / col("total")) * 100)

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

def write_to_postgres(microbatch_df, epoch_id):
    microbatch_df.write \
        .jdbc(url=jdbc_url, table="overspeed_output_rt", mode="append", properties=connection_properties)

result.writeStream \
    .foreachBatch(write_to_postgres) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoints_overspeed") \
    .start() \
    .awaitTermination()
