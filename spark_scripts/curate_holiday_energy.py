from pyspark.sql import SparkSession

from pyspark.sql.functions import sum, col, lag, first
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find change of consumption each holiday") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Select 
df_selected = df.select("day","holiday_name","energy_sum")

df_grouped = df_selected.groupBy("day").agg(sum("energy_sum").alias("total_energy"), first("holiday_name").alias("holiday_name"))

windowSpec = Window.orderBy("day")
df_change = df_grouped.withColumn("prev_energy", lag("total_energy").over(windowSpec))
df_change = df_change.withColumn("holiday_change", col("total_energy") - col("prev_energy"))

df_holidays = df_change.filter(col("holiday_name").isNotNull())

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_holidays.write.jdbc(url=jdbc_url, table="holiday_energy_change", mode="overwrite", properties=connection_properties)

