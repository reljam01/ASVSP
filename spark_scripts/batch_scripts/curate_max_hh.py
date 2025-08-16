from pyspark.sql import SparkSession

from pyspark.sql.functions import max, avg
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find max half-hourly consumption by day type") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Select 
df_selected = df.select("day_type","energy_max")
windowSpec = Window.partitionBy("day_type")

df_max = df_selected.withColumn("max_by_weather", max("energy_max").over(windowSpec))

df_max = df_max.groupBy("day_type").agg(avg("max_by_weather").alias("max_energy_by_weather_type"))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_max.write.jdbc(url=jdbc_url, table="energy_max_by_weather", mode="overwrite", properties=connection_properties)

