from pyspark.sql import SparkSession

from pyspark.sql.types import StructType, StructField, LongType, StringType, IntegerType

from pyspark.sql.functions import input_file_name, regexp_extract

# Initialize the Spark session inside the Docker container
spark = SparkSession.builder \
    .appName("CSV Loader") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .getOrCreate()

# Define schema of electrical consumption data
electrical_schema = StructType([
    StructField("net_mgr", LongType(), True),
    StructField("purchase_area", StringType(), True),
    StructField("street", StringType(), True),
    StructField("zip_from", StringType(), True),
    StructField("zip_to", StringType(), True),
    StructField("city", StringType(), True),
    StructField("num_conn", IntegerType(), True),
    StructField("delivery_perc", IntegerType(), True),
    StructField("active_perc", IntegerType(), True),
    StructField("type_perc", IntegerType(), True),
    StructField("type_conn", StringType(), True),
    StructField("annual_consume", IntegerType(), True)
])

# Read data about electrical consumption from csv-s
df_electrical = spark.read.schema(electrical_schema).csv("hdfs://namenode:9000/user/hadoop/raw/Electricity/*.csv")

# Extract filename details
df_electrical = df_electrical.withColumn("file_name", regexp_extract(input_file_name(), ".*/(.*).csv", 1))  # Get file name without path & extension
df_electrical = df_electrical.withColumn("source", regexp_extract(df_electrical["file_name"], "^([^_]*)", 1))  # Extract source before first '_'
df_electrical = df_electrical.withColumn("year", regexp_extract(df_electrical["file_name"], "([0-9]{4})$", 1).cast(IntegerType()))  # Extract last 4 digits as year

# Drop the temporary filename column
df_electrical = df_electrical.drop("file_name")

df_electrical.write.mode("overwrite").parquet("hdfs://namenode:9000/user/hadoop/transformed/")
