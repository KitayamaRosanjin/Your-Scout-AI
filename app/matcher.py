import json
import os
import boto3
from botocore.exceptions import ClientError

# Environment variables
TABLE_NAME = os.environ.get("TABLE_NAME", "JobsTable")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

def get_dynamodb_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(TABLE_NAME)

def analyze_job_match(job_details, resume_text):
    """
    Calls LLM to analyze match between job and resume.
    Returns dict with score and reason.
    """
    # Placeholder for actual LLM call
    # In a real scenario, use openai.ChatCompletion.create()
    
    print(f"Analyzing job: {job_details.get('title')}...")
    
    title = job_details.get("title", "").lower()
    description = job_details.get("description", "").lower()
    
    # Mock Logic: High score if 'python' or 'aws' in title/desc
    score = 0
    reason = "Not relevant."
    
    if "python" in title or "python" in description:
        score += 50
        reason = "Python skill match."
    if "aws" in title or "aws" in description:
        score += 30
        reason += " AWS skill match."
        
    if score > 0:
        score += 10 # Base score for being tech related matches
        
    return {
        "score": min(score, 100),
        "reason": reason,
        "is_match": score >= 70
    }

def handler(event, context):
    print("Matcher started")
    table = get_dynamodb_table()
    
    # User Resume (Store in SSM Parameter Store or S3 in real app)
    # Hardcoded for portfolio MVP
    RESUME_TEXT = """
    Software Engineer with experience in Python, AWS.
    Built SaaS portfolio using CDK and Lambda.
    """
    
    processed_count = 0
    
    for record in event.get('Records', []):
        if record.get('eventName') != 'INSERT':
            continue
            
        # DynamoDB Stream record format is slightly different (NewImage)
        # We need to deserialize it or simpler, if running locally, we might pass different event structure.
        # But commonly we just use the keys.
        
        # NOTE: In real Stream event, 'dynamodb' key contains 'NewImage' with DynamoDB JSON format.
        # We need a deserializer if we use standard library, OR use boto3's TypeDeserializer.
        # For simplicity in this script, assuming we handle the structure or if locally invoked with simple dict.
        
        new_image = record.get('dynamodb', {}).get('NewImage', {})
        if not new_image:
            continue
            
        # Simple extraction (assuming string types for MVP simplicity)
        job_id = new_image.get('job_id', {}).get('S')
        title = new_image.get('title', {}).get('S')
        description = new_image.get('description', {}).get('S')
        
        if not job_id:
            continue
            
        job_details = {
            "title": title,
            "description": description
        }
        
        analysis = analyze_job_match(job_details, RESUME_TEXT)
        
        if analysis['is_match']:
            print(f"MATCH FOUND! {title} (Score: {analysis['score']})")
            
            # Update Item in DynamoDB with analysis
            try:
                table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression="set #s = :s, analysis = :a, score = :v",
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':s': 'MATCHED',
                        ':a': analysis['reason'],
                        ':v': analysis['score']
                    }
                )
                processed_count += 1
            except Exception as e:
                print(f"Failed to update job {job_id}: {e}")
        else:
            print(f"Not a match: {title}")
            # Optional: Mark as UNMATCHED to avoid processing again if we re-scan?
            # But we rely on Streams which only fire on changes. 
            
    return {
        'statusCode': 200,
        'body': json.dumps(f'Matcher processed {processed_count} matches.')
    }

if __name__ == "__main__":
    # Local Test
    print("Running in local test mode...")
    
    # Mock DynamoDB Table
    class MockTable:
        def update_item(self, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues):
            print(f"[MOCK DB] Update {Key['job_id']}: Status=MATCHED, Score={ExpressionAttributeValues[':v']}")
            
    def get_dynamodb_table(): # type: ignore
        return MockTable()
        
    # Mock Event
    mock_event = {
        'Records': [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'job_id': {'S': '123'},
                        'title': {'S': 'Senior Python Developer'},
                        'description': {'S': 'We need AWS and Python experts.'}
                    }
                }
            },
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': {
                        'job_id': {'S': '456'},
                        'title': {'S': 'Java Developer'},
                        'description': {'S': 'Spring Boot needed.'}
                    }
                }
            }
        ]
    }
    
    handler(mock_event, {})
