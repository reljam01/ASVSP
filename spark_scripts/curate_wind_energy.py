from pyspark.sql import SparkSession

from pyspark.sql.functions import sum,row_number, col, when, coalesce, lit, regexp_replace
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find latest windy/not average consumption") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Select 
df_selected = df.select("day","windSpeed","energy_sum")

# Windiness defined as:
# below 3.5 knots - calm
# above 3.5 knots - windy
df_temp = df_selected.withColumn(
    "wind_category",
    when(col("windSpeed") < 3.5, "Calm")
    .when(col("windSpeed") >= 3.5, "Windy")
    .otherwise("Unknown"))

df_grouped = df_temp \
    .groupBy("day", "wind_category") \
    .agg(sum("energy_sum").alias("total_daily"))

windowSpec = Window.partitionBy("wind_category").orderBy(col("day").desc())
df_rownum = df_grouped.withColumn("rownum", row_number().over(windowSpec))

df_last_day = df_rownum.filter(col("rownum") == 1)

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_last_day.write.jdbc(url=jdbc_url, table="latest_energy_by_wind", mode="overwrite", properties=connection_properties)
