from pyspark.sql import SparkSession

from pyspark.sql.functions import sum, col, row_number
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Get top 10 households by consumption") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Calculate total energy spent per household
df_selected = df.select("LCLid","energy_sum")
df_summed = df_selected.groupBy("LCLid").agg(sum("energy_sum").alias("total_energy"))
windowSpec = Window.orderBy(col("total_energy").desc())

# Rank and find top 10 households
df_ranked = df_summed.withColumn("rank", row_number().over(windowSpec))
top_10_households = df_ranked.filter(col("rank") <= 10)

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

top_10_households.write.jdbc(url=jdbc_url, table="top_ten_households", mode="overwrite", properties=connection_properties)

