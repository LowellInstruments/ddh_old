import glob
import os
import uuid
import boto3
import json

from dds.aws import ddh_write_aws_sqs_ts
from dds.net import ddh_get_internet_via
from dds.timecache import its_time_to
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
    if not its_time_to("sqs_serve", 600):
        return

    if not dds_get_cfg_flag_sqs_en():
        lg.a("warning: sqs_en is False")
        return

    if ddh_get_internet_via() == "none":
        # prevents main_loop getting stuck
        lg.a("warning: no internet to serve SQS")
        return

    # ---------------------------------
    # grab / collect SQS files to send
    # ---------------------------------
    fol = get_ddh_folder_path_sqs()
    files = glob.glob("{}/*.sqs".format(fol))
    if files:
        lg.a('\n')
        lg.a("---------------------")
        lg.a(f"serving {len(files)} SQS files")
        lg.a("---------------------\n")

    for _ in files:

        # this happens not often but did once
        if os.path.getsize(_) == 0:
            os.unlink(_)
            continue

        # reads local SQS file as JSON
        f = open(_, "r")
        j = json.load(f)
        lg.a("serving file {}".format(_))

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
                lg.a("debug: SQS OK sent msg\n\n{}\n".format(m))
                # delete SQS file
                os.unlink(_)
                # tell status database for API all went fine
                ddh_write_aws_sqs_ts('sqs', 'ok')

        except (Exception,) as ex:
            lg.a(f"error sqs_serve: {ex}")
            ddh_write_aws_sqs_ts('sqs', f'error {str(ex)}')

        finally:
            if f:
                f.close()

    if files:
        lg.a('\n')
        lg.a("---------------------------")
        lg.a("serving SQS files finished")
        lg.a("---------------------------\n")


if __name__ == "__main__":
    # this file can be tested in main_dds.py
    pass
