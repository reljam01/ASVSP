from pyspark.sql import SparkSession

from pyspark.sql.functions import avg, month, year, row_number, col
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
df_m = df_selected.withColumn("month", month(col("day")))
df_yearmonth = df_m.withColumn("year", year(col("day")))

windowSpec = Window.partitionBy("year","month").orderBy("day")
df_ranked = df_yearmonth.withColumn("rank", row_number().over(windowSpec))

df_first_day = df_ranked.filter(col("rank") == 1)
df_avg_first = df_first_day.groupBy("year", "month").agg(avg("energy_sum").alias("daily_average"))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_avg_first.write.jdbc(url=jdbc_url, table="energy_first_day", mode="overwrite", properties=connection_properties)

