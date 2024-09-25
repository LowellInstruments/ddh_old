import glob
import os
import uuid
import boto3
import json

from dds.aws import ddh_write_timestamp_aws_sqs
from dds.net import ddh_get_internet_via
from dds.timecache import is_it_time_to
from utils.ddh_config import (
    dds_get_cfg_flag_sqs_en, dds_get_cfg_aws_credential)
from utils.logs import lg_sqs as lg
from utils.ddh_shared import (
    get_ddh_folder_path_sqs,
)
import warnings

warnings.filterwarnings("ignore",
                        category=FutureWarning,
                        module="botocore.client")


sqs_key_id = "AKIA2SU3QQX6Z4TX4VO3"
sqs_access_key = "TNb/28rhhnJsUkvZwmTFtOEovd7qyUM+eCvstU7L"
queue_name = "ddw_in.fifo"


sqs = boto3.client(
    "sqs",
    region_name="us-east-2",
    aws_access_key_id=sqs_key_id,
    aws_secret_access_key=sqs_access_key,
)


def main():

    s = '{ "name":"John", "age":30, "city":"New York"}'
    j = json.loads(s)

    try:
        # ENQUEUES the JSON as string to SQS service
        m = json.dumps(j)
        rsp = sqs.send_message(
            QueueUrl=queue_name,
            MessageGroupId=str(uuid.uuid4()),
            MessageDeduplicationId=str(uuid.uuid4()),
            MessageBody=m,
        )

        md = rsp["ResponseMetadata"]
        if md and int(md["HTTPStatusCode"]) == 200:
            print('send cannot mount notification OK')

    except (Exception,) as ex:
        print(f"error_main_test_sqs {ex}")


if __name__ == "__main__":
    main()
