from pyspark.sql import SparkSession

from pyspark.sql.functions import sum, col, lag
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find day by day and cumulative consumption") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Select 
df_selected = df.select("day","energy_sum")

df_sum = df.groupBy("day").agg(sum("energy_sum").alias("daily_consumption"))

windowSpec = Window.orderBy("day")

# Get day by day consumption
df_sum_dbd = df_sum.withColumn("consumption_difference", col("daily_consumption") - lag("daily_consumption", 1).over(windowSpec))

# Get cumulative consumption
df_cumsum = df_sum_dbd.withColumn("cumulative_consumption", sum("daily_consumption").over(windowSpec))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_cumsum.write.jdbc(url=jdbc_url, table="energy_day_by_day_cumulative", mode="overwrite", properties=connection_properties)

