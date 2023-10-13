import boto3
import os


# set this in pycharm or bash
AWS_KEY_ID = os.getenv("AWS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET")


s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    aws_access_key_id=AWS_KEY_ID,
    aws_secret_access_key=AWS_SECRET,
)


# testing S3 upload and listing
def main():
    k = os.path.basename(__file__)
    f = "{}/{}".format(os.getcwd(), k)
    s3.upload_file(Filename=f, Bucket="bkt-kaz", Key=k)
    rsp = s3.list_objects(Bucket="bkt-kaz")
    md = rsp["ResponseMetadata"]
    if md and int(md["HTTPStatusCode"]) == 200:
        print("[ TEST ] AWS S3 OK")


if __name__ == "__main__":
    main()
