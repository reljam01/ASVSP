from pyspark.sql import SparkSession
from pyspark.sql.functions import desc, approxQuantile, len, first
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("KafkaParquetLoader") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
his_path = "hdfs://namenode:9000/user/hadoop/transformed/london"
rt_path = "hdfs://namenode:9000/user/hadoop/realtime/london"

his_df = spark.read.parquet(his_path)
rt_df = spark.read.parquet(rt_path)

his_sel = his_df.select("day", "windSpeed")
rt_sel = rt_df.select("data.TimeStamp", "data.WindSpeed")

maxTs = rt_sel.select(max("data.TimeStamp")).collect()[0][0]

rt_newest = rt_sel.filter(rt_sel["data.TimeStamp"] == max_ts)

percentiles = [0.0, 0.25, 0.5, 0.75, 1.0]
quantiles = his_sel.approxQuantile("windSpeed", percentiles, 0.05)

rt_percentile = None
for i in range(len(quantiles) - 1):
    if quantiles[i] <= rt_newest.select("data.WindSpeed").first()[0]
        rt_percentile = percentiles[i+1]
        break

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

rt_percentile.write.jdbc(url=jdbc_url, table="wind_percentiles", mode="overwrite", properties=connection_properties)
