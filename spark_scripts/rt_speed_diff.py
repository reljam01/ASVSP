rom pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, abs, window, mean, stddev
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

diff_df = parsed_df.withColumn("speedDiff", abs(col("data.RotorSpeed") - col("data.GeneratorSpeed")))

windowSpec = Window.orderBy("data.TimeStamp").rangeBetween(-3600, 0)

time_df = diff_df.withColumn("avgDiff", mean("speedDiff").over(windowSpec)) \
    .withColumn("devDiff", stddev("speedDiff").over(windowSpec))

outlier_df = time_df.withColumn("isOutlier", (col("speedDiff") > (col("avgDiff") + 3*col("devDiff"))).cast("boolean"))

outlier_df = outlier_df.filter(col("isOutlier") == True)

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

def write_to_postgres(microbatch_df, epoch_id):
    microbatch_df.write \
        .jdbc(url=jdbc_url, table="speed_outliers_rt", mode="append", properties=connection_properties)

result.writeStream \
    .foreachBatch(write_to_postgres) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/checkpoints_overspeed") \
    .start() \
    .awaitTermination()
