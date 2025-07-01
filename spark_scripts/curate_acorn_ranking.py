from pyspark.sql import SparkSession

from pyspark.sql.functions import max, dense_rank, col
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Rank ACORN groups by max halfhourly consumption") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Select 
df_selected = df.select("Acorn_grouped","energy_max")

df_max = df_selected.groupBy("Acorn_grouped").agg(max("energy_max").alias("max_consumption"))

windowSpec = Window.orderBy(col("max_consumption").desc())
df_ranked = df_max.withColumn("rank", dense_rank().over(windowSpec))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_ranked.write.jdbc(url=jdbc_url, table="top_affluence_consumers_hh", mode="overwrite", properties=connection_properties)

