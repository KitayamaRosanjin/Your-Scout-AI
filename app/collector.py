import json
import os
import boto3
import feedparser
from datetime import datetime
from botocore.exceptions import ClientError

# Environment variables
TABLE_NAME = os.environ.get("TABLE_NAME", "JobsTable")

def get_dynamodb_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(TABLE_NAME)

def fetch_rss_feed(url):
    """Fetches and parses an RSS feed."""
    print(f"Fetching {url}...")
    # Add User-Agent to avoid getting blocked by some servers
    feed = feedparser.parse(url, agent="YourScoutAI/1.0 (+https://github.com/your-repo)")
    
    jobs = []
    if feed.bozo:
        print(f"Warning: Malformed feed {url}: {feed.bozo_exception}")
    
    for entry in feed.entries:
        # Use link as unique ID, or id if available
        job_id = entry.get("id", entry.get("link"))
        if not job_id:
            continue

        published = entry.get("published", datetime.now().isoformat())
        summary = entry.get("summary", entry.get("description", ""))
        
        # Simple text cleaning could go here
        
        jobs.append({
            "job_id": job_id,
            "title": entry.get("title", "No Title"),
            "url": entry.get("link", ""),
            "description": summary[:1500], # Truncate to avoid DynamoDB limits on simple MVP
            "published_at": published,
            "source": feed.feed.get("title", "Unknown Source"),
            "status": "NEW", # Logic: NEW -> MATCHING -> MATCHED/UNMATCHED
            "fetched_at": datetime.now().isoformat()
        })
    return jobs

def save_jobs(jobs):
    """Saves jobs to DynamoDB, avoiding duplicates."""
    table = get_dynamodb_table()
    saved_count = 0
    
    for job in jobs:
        try:
            # Conditional Put to avoid overwriting existing jobs (and triggering Matcher again)
            table.put_item(
                Item=job,
                ConditionExpression='attribute_not_exists(job_id)'
            )
            saved_count += 1
            print(f"Saved new job: {job['title'][:30]}...")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Job already exists
                pass
            else:
                print(f"Error saving job {job['job_id']}: {e}")
    
    return saved_count

def handler(event, context):
    print("Collector started")
    
    # Example feeds. In production, these might be loaded from another DB or Config.
    # Using 'Hacker News: Who is hiring?' search for 'python' as a demo source
    TARGET_FEEDS = [
        "https://hnrss.org/newest?q=hiring+python",
        # Add more feeds here
    ]
    
    total_new_jobs = 0
    for url in TARGET_FEEDS:
        try:
            jobs = fetch_rss_feed(url)
            if not jobs:
                print(f"No jobs found in {url}")
                continue
            
            count = save_jobs(jobs)
            total_new_jobs += count
        except Exception as e:
            print(f"Failed to process feed {url}: {e}")

    result_message = f"Collector finished. Saved {total_new_jobs} new jobs."
    print(result_message)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result_message)
    }

if __name__ == "__main__":
    # Local Test Run (Mocking DynamoDB or just printing)
    # If run directly, we can just print what we found to verify logic
    print("Running in local test mode...")
    
    # Mock table for local test
    class MockTable:
        def put_item(self, Item, ConditionExpression=None):
            print(f"[MOCK DB] Would save: {Item['title']}")
            # Simulate verify logic
            return
            
    # Override get_dynamodb_table logic for local test
    def get_dynamodb_table(): # type: ignore
        return MockTable()
        
    handler({}, {})
