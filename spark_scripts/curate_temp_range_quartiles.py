from pyspark.sql import SparkSession

from pyspark.sql.functions import when, col, ntile
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Find quartiles by temperature") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed/london"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Select 
df_selected = df.select("temperatureMax","energy_sum")

# Temperature groups used:
# below 10 Celsius - Cold
# below 17 Celsius - Mild
# below 23 Celsius - Warm
# above 23 Celsius - Hot
df_temp = df_selected.withColumn(
    "temp_category",
    when(col("temperatureMax") < 10, "Cold")
    .when((col("temperatureMax") >= 10) & (col("temperatureMax") < 17), "Mild")
    .when((col("temperatureMax") >= 17) & (col("temperatureMax") < 23), "Warm")
    .when(col("temperatureMax") >= 23, "Hot")
    .otherwise("Unknown"))

windowSpec = Window.partitionBy("temp_category").orderBy("energy_sum")
df_quartiles = df_temp.withColumn("quartile", ntile(4).over(windowSpec))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

df_quartiles.write.jdbc(url=jdbc_url, table="energy_by_temp_quartiles", mode="overwrite", properties=connection_properties)

