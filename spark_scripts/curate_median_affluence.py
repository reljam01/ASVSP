from pyspark.sql import SparkSession

from pyspark.sql.functions import avg, when, col, row_number, count, floor
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find median daily consumption by affluence group") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

df_selected = df.select("LCLid","Acorn_grouped","energy_sum")
df_grouped = df_selected.groupBy("LCLid","Acorn_grouped").agg(avg("energy_sum").alias("household_avg"))

windowSpec = Window.partitionBy("Acorn_grouped").orderBy("household_avg")
df_rownum = df_grouped.withColumn("row_num",row_number().over(windowSpec)).withColumn("row_count",count("household_avg").over(Window.partitionBy("Acorn_grouped")))

df_median = df_rownum.withColumn("median_energy",when( \
    (col("row_num") == (floor(col("row_count") / 2) + 1)) | \
    (col("row_num") == floor((col("row_count") + 1) / 2)), col("household_avg")).otherwise(None))

df_median_filt = df_median.filter(df_median["median_energy"].isNotNull())

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_median_filt.write.jdbc(url=jdbc_url, table="median_energy_by_affluence", mode="overwrite", properties=connection_properties)

