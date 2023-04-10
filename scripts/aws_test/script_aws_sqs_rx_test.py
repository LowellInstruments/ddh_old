import boto3
import os
import sys


# set this in pycharm or bash
AWS_KEY_ID = os.getenv("AWS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET")
SQS_QUEUE = "https://sqs.us-east-2.amazonaws.com/727249356285/ddw_in.fifo"


if not AWS_KEY_ID:
    print("{} needs credentials")
    sys.exit(1)


sqs = boto3.client(
    "sqs",
    region_name="us-east-2",
    aws_access_key_id=AWS_KEY_ID,
    aws_secret_access_key=AWS_SECRET,
)


# testing queue receive message
def main():
    rsp = sqs.receive_message(
        QueueUrl=SQS_QUEUE,
        AttributeNames=["SentTimestamp"],
        MaxNumberOfMessages=1,
        MessageAttributeNames=["All"],
        WaitTimeSeconds=0,
    )

    try:
        m = rsp["Messages"][0]
    except KeyError:
        print("[ TEST ] warning: AWS SQS_RX, no messages to dequeue")
        sys.exit(1)

    # remove message from queue
    receipt_handle = m["ReceiptHandle"]
    rsp = sqs.delete_message(QueueUrl=SQS_QUEUE, ReceiptHandle=receipt_handle)
    md = rsp["ResponseMetadata"]
    if md and int(md["HTTPStatusCode"]) == 200:
        print("[ TEST ] AWS SQS_RX OK, message", m)


if __name__ == "__main__":
    main()
