from pyspark.sql import SparkSession
from pyspark.sql.functions import col, max, min, lag, when, dayofmonth, month
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, TimestampType, FloatType, IntegerType

spark = SparkSession.builder \
    .appName("TempAnomalyCalculator") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

schema = StructType() \
    .add("TimeStamp",TimestampType()) \
    .add("RotorSpeed",FloatType()) \
    .add("GeneratorSpeed",FloatType()) \
    .add("GeneratorTemperature",FloatType()) \
    .add("WindSpeed",FloatType()) \
    .add("PowerOutput",FloatType()) \
    .add("MaxWindHeute",FloatType()) \
    .add("year",IntegerType()) \
    .add("month",IntegerType()) \
    .add("day",IntegerType()) \
    .add("hour",IntegerType()) \

# Path to the Parquet files on HDFS
his_path = "hdfs://namenode:9000/user/hadoop/transformed/london"
rt_path = "hdfs://namenode:9000/user/hadoop/realtime/london"

his_df = spark.read.parquet(his_path)
rt_df = spark.read.schema(schema).parquet(rt_path)

his_sel = his_df.select("day", "temperatureMax")

latest_partition = rt_df.select("year", "month", "day") \
    .distinct() \
    .orderBy("year", "month", "day", ascending=False) \
    .limit(1) \
    .collect()[0]

ref_year = latest_partition["year"]
ref_month = latest_partition["month"]
ref_day = latest_partition["day"]

rt_filt = rt_df.filter(
(col("year") == ref_year) &
(col("month") == ref_month) &
(col("day") == ref_day)
)

maxTs = rt_filt.select(max("TimeStamp")).first()[0]
rt_newest = rt_filt.filter(col("TimeStamp") == maxTs)

his_filt = his_sel.filter((month("day") == ref_month) & (dayofmonth("day") == ref_day))
hisTemp = his_filt.select(min("temperatureMax")).first()[0]

rt_diff = rt_filt.withColumn("tempDiff", col("GeneratorTemperature") - hisTemp)
rt_diff = rt_diff.withColumn("tempHigh", col("tempDiff") > 30)

w = Window.orderBy("TimeStamp")

rt_diff = rt_diff.withColumn("tempPrev", lag("tempHigh").over(w))

rt_diff = rt_diff.withColumn("anomalyStart",when((col("tempPrev") == 0) & (col("tempHigh") == 1), 1).otherwise(0))

rt_diff = rt_diff.withColumn("anomalyEnd",when((col("tempPrev") == 1) & (col("tempHigh") == 0), 1).otherwise(0))

rt_diff = rt_diff.withColumn("anomalyType", when(col("anomalyStart") == 1, "Begin").when(col("anomalyEnd") == 1, "End").otherwise(None))

rt_diff = rt_diff.filter(col("anomalyType").isNotNull())

rt_diff = rt_diff.select("TimeStamp", "PowerOutput", "GeneratorTemperature", "anomalyType")

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
"user": "admin",
"password": "admin",
"driver": "org.postgresql.Driver"
}

rt_diff.write.jdbc(url=jdbc_url, table="latest_temp_anomalies", mode="overwrite", properties=connection_properties)
