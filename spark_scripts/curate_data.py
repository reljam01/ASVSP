from pyspark.sql import SparkSession

from pyspark.sql.functions import avg

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Read Parquet from HDFS") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
hdfs_path = "hdfs://namenode:9000/user/hadoop/transformed"

# Read the Parquet files into a DataFrame
df = spark.read.parquet(hdfs_path)

# Show the DataFrame
df.show(n=5)

# Print schema to understand structure
df.printSchema()

# Display summary statistics
df.describe().show()

df.count()

# Get column names
df.columns

# Find the average annual consumption
avg_df = df.select(avg("annual_consume").alias("average_consumption"))

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

avg_df.write.jdbc(url=jdbc_url, table="test", mode="overwrite", properties=connection_properties)

