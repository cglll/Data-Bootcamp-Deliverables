FROM 711395599931.dkr.ecr.us-east-2.amazonaws.com/spark/emr-6.3.0:latest
USER root

# installing numpy to be able to use pyspark's ml lib
RUN pip3 install numpy

### End customization
USER hadoop:hadoop
