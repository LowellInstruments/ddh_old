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


# used when S3 and SQS keys are the same
# getenv() keys are useful for development :)
sqs_key_id = (dds_get_cfg_aws_credential("cred_aws_key_id") or
              os.getenv('CRED_AWS_KEY_ID'))
sqs_access_key = (dds_get_cfg_aws_credential("cred_aws_secret") or
                  os.getenv('CRED_AWS_SECRET'))

# only used when S3 and SQS keys are different
custom_sqs_key_id = dds_get_cfg_aws_credential("cred_aws_custom_sqs_key_id")
custom_sqs_access_key = dds_get_cfg_aws_credential("cred_aws_custom_sqs_access_key")
if custom_sqs_key_id:
    sqs_key_id = custom_sqs_key_id
if custom_sqs_access_key:
    sqs_access_key = custom_sqs_access_key


sqs = boto3.client(
    "sqs",
    region_name="us-east-2",
    aws_access_key_id=sqs_key_id,
    aws_secret_access_key=sqs_access_key,
)


def dds_create_folder_sqs():
    r = get_ddh_folder_path_sqs()
    os.makedirs(r, exist_ok=True)


def sqs_serve():

    # this runs from time to time, not always
    if not is_it_time_to("sqs_serve", 600):
        return

    if not dds_get_cfg_flag_sqs_en():
        lg.a("warning: sqs_en is False")
        return

    if ddh_get_internet_via() == "none":
        # prevents main_loop getting stuck
        lg.a("error: no internet to serve SQS")
        return

    # ---------------------------------
    # grab / collect SQS files to send
    # ---------------------------------
    fol = get_ddh_folder_path_sqs()
    files = glob.glob(f"{fol}/*.sqs")
    if files:
        lg.a(f"serving {len(files)} SQS files")

    for i_f in files:

        # this happens not often but did once
        if os.path.getsize(i_f) == 0:
            os.unlink(i_f)
            continue

        # reads local SQS file as JSON
        f = open(i_f, "r")
        j = json.load(f)
        _bn = os.path.basename(i_f)
        lg.a(f"serving file {_bn}")

        try:
            # ENQUEUES the JSON as string to SQS service
            m = json.dumps(j)
            rsp = sqs.send_message(
                QueueUrl=dds_get_cfg_aws_credential("cred_aws_sqs_queue_name"),
                MessageGroupId=str(uuid.uuid4()),
                MessageDeduplicationId=str(uuid.uuid4()),
                MessageBody=m,
            )

            md = rsp["ResponseMetadata"]
            if md and int(md["HTTPStatusCode"]) == 200:
                lg.a(f"SQS OK sent msg\n\t{m}")
                # delete SQS file
                os.unlink(i_f)
                # tell status database for API all went fine
                ddh_write_timestamp_aws_sqs('sqs', 'ok')

        except (Exception,) as ex:
            lg.a(f"error sqs_serve: {ex}")
            ddh_write_timestamp_aws_sqs('sqs', f'error {str(ex)}')

        finally:
            if f:
                f.close()

    if files:
        lg.a("serving SQS files finished")


if __name__ == "__main__":
    # this file can be tested in main_dds.py
    pass
