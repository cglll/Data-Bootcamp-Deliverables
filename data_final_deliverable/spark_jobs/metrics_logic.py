from pyspark.sql import SparkSession
from pyspark.sql.functions import round
from pyspark.sql.functions import lit
from datetime import datetime


# Spark job which uses the user_purchase and positivity files to calculate the 
# user behavior metrics logic of the capstone project.
if __name__ == "__main__":
    spark = SparkSession.builder.appName("Test_spark")\
                        .master("local[2]").getOrCreate()
    classes_df = spark.read.option("header", "true")\
                    .parquet("s3://staging-layer20211122002502098700000005/"
                             "positivity.parquet")

    user_df = spark.read.option("header", "true")\
                .csv("s3://staging-layer20211122002502098700000005/"
                     "user_purchase.csv")

    # get the amount spent per customer id and join with the review_score and
    # review_count columns
    analysis_df = user_df.withColumn("amount_spent",
                                    user_df["Quantity"] * user_df["UnitPrice"])\
                        .groupby("CustomerID").sum()\
                        .select("CustomerID", round("sum(amount_spent)", 2))\
                        .withColumnRenamed("round(sum(amount_spent), 2)",
                                            "amount_spent")\
                        .withColumnRenamed("CustomerID",
                                            "customerids")

    # The review_score column has the total number of positive reviews for every
    # customer id available. On the other hand the review_count column has the
    # total number of reviews per customer id.
    review_score = classes_df.groupby("cid").sum()\
                            .withColumnRenamed("sum(positivity)", "review_score")
    review_count = classes_df.groupby("cid").count()\
                            .withColumnRenamed("count", "review_count")\
                            .withColumnRenamed("cid", "cid2")

    analysis_df = analysis_df.join(review_score,
                                analysis_df["customerids"] == review_score["cid"],
                                "inner")\
                            .join(review_count,
                                analysis_df["customerids"] == review_count["cid2"],
                                "inner")
    analysis_df = analysis_df.withColumn("insert_date", lit(datetime.now().date()))
    analysis_df = analysis_df.select("customerids",
                                    "amount_spent",
                                    "review_score",
                                    "review_count",
                                    "insert_date")
    analysis_df.write.mode("overwrite")\
      .parquet("s3://analytics-layer20211122002502098700000005/metrics_logic.parquet")

    spark.stop()