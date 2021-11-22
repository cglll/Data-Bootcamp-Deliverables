from pyspark.ml.feature import RegexTokenizer
from pyspark.sql import SparkSession
from pyspark.sql.functions import array_contains, when


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Test_spark")\
               .config("spark.hadoop.fs.s3a.multiobjectdelete.enable","false")\
               .master("local[2]").getOrCreate()
    df = spark.read.option("header", "true")\
                .csv("s3://spark-test-samp/movie_review.csv")

    # use regex to get an array column called words which will contain all the
    #  words without numbers and without symbols 
    # Ex: "I didn't think about <br> 10 <br>" will end up as
    # ["I", "didnt", "think", "about", "br", "br"]
    tokenizer = RegexTokenizer(minTokenLength=2,
                                inputCol="review_str",
                                outputCol="words",
                                pattern="\W|[1-9_]")
    df = tokenizer.transform(df)

    # The following lines of code search of each row containing the word good 
    # and asigns a 1 if found else a 0. These values are assigned to a new 
    # column as instructed for the capstone project
    pos_col = array_contains(df["words"], "good")
    df = df.withColumn("positivity", when(pos_col == "true", 1).otherwise(0))
    
    df.select("cid", "positivity").write.mode("overwrite")\
      .parquet("s3://spark-test-samp/positivity.parquet")
    spark.stop()