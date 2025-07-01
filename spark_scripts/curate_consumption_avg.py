from pyspark.sql import SparkSession

from pyspark.sql.functions import avg, date_format
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find moving daily average by month of household consumption") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

df_selected = df.select("day","energy_sum")
df_average_daily = df_selected.groupBy("day").agg(avg("energy_sum").alias("energy_avg"))

df_month = df_average_daily.withColumn("year_month", date_format("day", "yyyy-MM"))
df_average_monthly = df_month.groupBy("year_month").agg(avg("energy_avg").alias("daily_avg"))

windowSpec = Window.orderBy("year_month").rowsBetween(-2,0)
df_average_monthly = df_average_monthly.withColumn("3_month_average",avg("daily_avg").over(windowSpec))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_average_monthly.write.jdbc(url=jdbc_url, table="moving_3month_avg_consumption", mode="overwrite", properties=connection_properties)

