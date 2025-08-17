from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, max as spark_max, min as spark_min, expr
from pyspark.sql.window import Window
from pyspark.sql import Row
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType, DoubleType
from datetime import timedelta
spark = SparkSession.builder \
    .appName("WindPercentileCalculator") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

schema = StructType() \
    .add("TimeStamp",TimestampType
()) \
    .add("RotorSpeed",FloatType()) \
    .add("GeneratorSpeed",FloatType()) \
    .add("GeneratorTemperature",FloatType()) \
    .add("WindSpeed",FloatType()) \
    .add("PowerOutput",FloatType()) \
    .add("MaxWindHeute",FloatType()) \
    .add("year",IntegerType()) \
    .add("month",IntegerType()) \
    .add("day",IntegerType()) \
    .add("hour",IntegerType()) \

# Path to the Parquet files on HDFS
his_path = "hdfs://namenode:9000/user/hadoop/transformed/london"
rt_path = "hdfs://namenode:9000/user/hadoop/realtime/london"

his_df = spark.read.parquet(his_path)
rt_df = spark.read.schema(schema).parquet(rt_path)

his_sel = his_df.select("day", "windSpeed")
rt_sel = rt_df.select("TimeStamp", "WindSpeed")

latest_ts = rt_sel.selectExpr("max(TimeStamp)").collect()[0][0]

start_ts_expr = expr(f"timestamp('{latest_ts}') - interval 30 seconds")

rt_recent = rt_sel.filter(col("TimeStamp") >= start_ts_expr)

avg_ws = rt_recent.select(avg("WindSpeed").alias("avgWindSpeed")).collect()[0][0]

percentiles = [0.0, 0.25, 0.5, 0.75, 1.0]
quantiles = his_sel.approxQuantile("windSpeed", percentiles, 0.05)

rt_percentile = percentiles[0]
for i in range(len(quantiles) - 1):
    if quantiles[i] <= avg_ws < quantiles[i + 1]:
        rt_percentile = percentiles[i + 1]
        break
if avg_ws >= quantiles[-1]:
    rt_percentile = percentiles[-1]

result = spark.createDataFrame([
    Row(
        startTimestamp=str(latest_ts - timedelta(seconds=30)),
        endTimestamp=str(latest_ts),
        avgWindSpeed=round(avg_ws, 2),
        percentile=rt_percentile
    )
])

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

result.write.jdbc(url=jdbc_url, table="wind_percentiles", mode="append", properties=connection_properties)
