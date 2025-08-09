from pyspark.sql import SparkSession
from pyspark.sql.functions import max, dayofmonth, month, min, col, lag, when
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("KafkaParquetLoader") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Path to the Parquet files on HDFS
his_path = "hdfs://namenode:9000/user/hadoop/transformed/london"
rt_path = "hdfs://namenode:9000/user/hadoop/realtime/london"

his_df = spark.read.parquet(his_path)
rt_df = spark.read.parquet(rt_path)

his_sel = his_df.select("day", "temperatureMax")
rt_sel = rt_df.select("data.TimeStamp", "data.GeneratorTemperature")

maxTs = rt_sel.select(max("data.TimeStamp")).collect()[0][0]

rt_newest = rt_sel.filter(rt_sel["data.TimeStamp"] == max_ts)

ref_day = dayofmonth(lit(maxTs))
ref_month = month(lit(maxTs))
his_filt = his_sel.filter((dayofmonth("day") == ref_day) & (month("day") == ref_month))
rt_filt = rt_sel.filter((dayofmonth("data.TimeStamp") == ref_day) & (month("data.TimeStamp") == ref_month))

hisTemp = his_filt.select(min("temperatureMax")).collect()[0][0]

rt_diff = rt_filt.withColumn("tempDiff", col("data.GeneratorTemperature") - hisTemp) 
rt_diff = rt_diff.withColumn("tempHigh", col("tempDiff") > 30)

w = Window.orderBy("data.TimeStamp")
rt_diff = rt_diff.withColumn("tempPrev", lag("tempHigh").over(w))

rt_diff = rt_diff.withColumn("tempHighEnd", when((col("tempHigh") != col("tempPrev")), 1).otherwise(0))

rt_diff = rt_diff.filter(rt_diff["tempHighEnd"] == 1)

jdbc_url = "jdbc:postgresql://postgres_curated:5432/mydatabase"
connection_properties = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}

rt_diff.write.jdbc(url=jdbc_url, table="latest_anomalies", mode="overwrite", properties=connection_properties)
