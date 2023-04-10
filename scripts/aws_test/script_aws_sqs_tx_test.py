import uuid

import json

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


def sqs_tx_test():
    d = {"my_sqs_test": "tx", "v": 123}
    m = json.dumps(d)
    rsp = sqs.send_message(
        QueueUrl=os.getenv("DDH_SQS_QUEUE_NAME"),
        MessageGroupId=str(uuid.uuid4()),
        MessageDeduplicationId=str(uuid.uuid4()),
        MessageBody=m,
    )

    md = rsp["ResponseMetadata"]
    if md and int(md["HTTPStatusCode"]) == 200:
        print("SQS OK sent msg\n\n{}\n".format(m))


if __name__ == "__main__":
    sqs_tx_test()
