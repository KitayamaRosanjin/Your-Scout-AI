import boto3
import os

def clean_table():
    # Get table name from stack output or hardcode for this script since it's one-off
    # We found the table name in previous steps: CdkAppStack-JobsTable1970BC16-4UEXLK22X7AD
    table_name = "CdkAppStack-JobsTable1970BC16-4UEXLK22X7AD"
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    print(f"Scanning table {table_name}...")
    try:
        scan = table.scan()
        with table.batch_writer() as batch:
            count = 0
            for each in scan['Items']:
                batch.delete_item(
                    Key={
                        'job_id': each['job_id']
                    }
                )
                count += 1
        print(f"Deleted {count} items.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_table()
