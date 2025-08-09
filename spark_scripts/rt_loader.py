from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType

spark = SparkSession.builder \
    .appName("KafkaParquetLoader") \
    .getOrCreate()

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "my_topic") \
    .option("startingOffsets", "latest") \
    .option("groupId", "1") \
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

parsed_df.writeStream \
    .format("parquet") \
    .option("path", "hdfs://namenode:9000/user/hadoop/realtime/london/") \
    .option("checkpointLocation", "hdfs://namenode:9000/user/hadoop/realtime/checkpoints/" \
    .outputMode("append") \
    .trigger(processingTime="30 seconds") \
    .start() \
    .awaitTermination()
