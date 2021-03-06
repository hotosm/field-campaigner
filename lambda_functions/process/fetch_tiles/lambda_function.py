import sys
sys.path.insert(0, 'dependencies')
import boto3
import os
import json
import logging
from landez import MBTilesBuilder

PATH = '/tmp/'

client = boto3.client("s3")


def lambda_handler(event, context):
    try:
        main(event)
    except Exception as e:
        error_dict = {'function': 'process_make_mbtiles', 'failure': str(e)}
        key = f'campaigns/{event["campaign_uuid"]}/failure.json'
        client.put_object(
            Bucket=os.environ['S3_BUCKET'],
            Key=key,
            Body=json.dumps(error_dict),
            ACL='public-read')


def spawn_make_pdf(event):
    aws_lambda = boto3.client('lambda')
    func_name = '{0}_process_make_pdf'.format(os.environ['ENV'])

    aws_lambda.invoke(
        FunctionName=func_name,
        InvocationType='Event',
        Payload=json.dumps(event)
    )


def main(event):
    uuid = event['campaign_uuid']
    logging.info(uuid)
    tiles_file = '{0}.mbtiles'.format(event['index'])
    local_mbtiles_path = os.path.join(PATH, tiles_file)

    mb = MBTilesBuilder(
        cache=False,
        tiles_headers={'User-Agent': 'github.com/hotosm/mapcampaigner'},
        filepath=local_mbtiles_path
    )
    mb.add_coverage(bbox=event['bbox'], zoomlevels=event['zoom_levels'])
    mb.run()

    # Upload to s3.
    key = os.path.join('campaigns', uuid, 'mbtiles', tiles_file)
    with open(local_mbtiles_path, "rb") as data:
        client.upload_fileobj(
            Fileobj=data,
            Bucket=os.environ['S3_BUCKET'],
            Key=key,
            ExtraArgs={'ACL': 'public-read'}
        )
    spawn_make_pdf(event)
