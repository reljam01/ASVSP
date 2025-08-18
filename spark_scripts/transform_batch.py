from pyspark.sql import SparkSession

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, DoubleType, DateType, TimestampType

from pyspark.sql.functions import to_date

# Initialize the Spark session inside the Docker container
spark = SparkSession.builder \
    .appName("CSV Loader") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Define schemas of electrical consumption data
electrical_schema = StructType([
    StructField("LCLid", StringType(), True),
    StructField("day", DateType(), True),
    StructField("energy_median", FloatType(), True),
    StructField("energy_mean", DoubleType(), True),
    StructField("energy_max", DoubleType(), True),
    StructField("energy_count", IntegerType(), True),
    StructField("energy_std", DoubleType(), True),
    StructField("energy_sum", DoubleType(), True),
    StructField("energy_min", DoubleType(), True)
])

# Only load useful columns of weather data
weather_schema = StructType([
    StructField("temperatureMax", FloatType(), True),
    StructField("temperatureMaxTime", TimestampType(), True),
    StructField("windBearing", IntegerType(), True),
    StructField("icon", StringType(), True),
    StructField("dewPoint", FloatType(), True),
    StructField("temperatureMinTime", TimestampType(), True),
    StructField("cloudCover", FloatType(), True),
    StructField("windSpeed", FloatType(), True),
])

# Household information
household_schema = StructType([
    StructField("LCLid", StringType(), True),
    StructField("stdorToU", StringType(), True),
    StructField("Acorn", StringType(), True),
    StructField("Acorn_grouped", StringType(), True),
    StructField("file", StringType(), True)
])

#Holidays
holidays_schema = StructType([
    StructField("Bank holidays", DateType(), True),
    StructField("Type", StringType(), True)
])

# Read data about electrical consumption from csv-s
df_electrical = spark.read.schema(electrical_schema).csv("hdfs://namenode:9000/user/hadoop/raw/daily_dataset.csv")
df_weather = spark.read.schema(weather_schema).csv("hdfs://namenode:9000/user/hadoop/raw/weather_daily_darksky.csv")
df_household = spark.read.schema(household_schema).csv("hdfs://namenode:9000/user/hadoop/raw/informations_households.csv")
df_holidays = spark.read.schema(holidays_schema).csv("hdfs://namenode:9000/user/hadoop/raw/uk_bank_holidays.csv")

# One max temperature per day, so we can just use the date
df_weather = df_weather.select("temperatureMax", "temperatureMaxTime", "icon", "windSpeed")
df_weather_date = df_weather.withColumn("day", to_date(df_weather["temperatureMaxTime"]))

df_el_w = df_electrical.join(df_weather_date, on="day", how="inner")
df_el_w_renamed = df_el_w.withColumnRenamed("icon", "day_type")
df_el_wh = df_el_w_renamed.join(df_household, on="LCLid", how="inner")
df_holidays_renamed1 = df_holidays.withColumnRenamed("Bank holidays", "day")
df_holidays_renamed2 = df_holidays_renamed1.withColumnRenamed("Type", "holiday_name")
df_joined = df_el_wh.join(df_holidays_renamed2, on="day", how="left")

df_joined.write.mode("overwrite").parquet("hdfs://namenode:9000/user/hadoop/transformed/london/")
