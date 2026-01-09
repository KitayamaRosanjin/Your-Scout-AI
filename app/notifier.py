import json
import os
import requests

# Environment variables
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

def send_notification(job_details, score, reason):
    """Sends notification to Discord/Slack."""
    title = job_details.get("title", "No Title")
    url = job_details.get("url", "#")
    
    message = {
        "content": f"🎯 **New High Match Found! (Score: {score}%)**\n**{title}**\n{url}\n> {reason}"
    }

    if WEBHOOK_URL:
        try:
            response = requests.post(WEBHOOK_URL, json=message)
            response.raise_for_status()
            print(f"Notification sent for {title}")
        except Exception as e:
            print(f"Failed to send notification: {e}")
    else:
        print(f"[MOCK NOTIFICATION] {message['content']}")

def handler(event, context):
    print("Notifier started")
    
    processed_count = 0
    
    for record in event.get('Records', []):
        if record.get('eventName') != 'MODIFY':
            continue

        # In a real DynamoDB Stream, we check NewImage vs OldImage to ensure status changed to MATCHED
        # For simplicity, we just check NewImage status
        new_image = record.get('dynamodb', {}).get('NewImage', {})
        old_image = record.get('dynamodb', {}).get('OldImage', {})
        
        # Check simple type extraction
        new_status = new_image.get('status', {}).get('S')
        old_status = old_image.get('status', {}).get('S')
        
        if new_status == 'MATCHED' and old_status != 'MATCHED':
            job_id = new_image.get('job_id', {}).get('S')
            title = new_image.get('title', {}).get('S')
            url = new_image.get('url', {}).get('S')
            
            # Since Number type in DynamoDB Stream is sent as string in 'N'
            score_str = new_image.get('score', {}).get('N')
            score = int(score_str) if score_str else 0
            
            reason = new_image.get('analysis', {}).get('S', 'No details.')
            
            job_details = {
                "title": title,
                "url": url
            }
            
            send_notification(job_details, score, reason)
            processed_count += 1
            
    return {
        'statusCode': 200,
        'body': json.dumps(f'Notifier sent {processed_count} alerts.')
    }

if __name__ == "__main__":
    # Local Test
    print("Running in local test mode...")
    
    # Mock Event: Transition from NEW to MATCHED
    mock_event = {
        'Records': [
            {
                'eventName': 'MODIFY',
                'dynamodb': {
                    'OldImage': {
                        'status': {'S': 'NEW'}
                    },
                    'NewImage': {
                        'job_id': {'S': '123'},
                        'title': {'S': 'Senior Python Developer'},
                        'url': {'S': 'https://example.com/job/123'},
                        'status': {'S': 'MATCHED'},
                        'score': {'N': '95'},
                        'analysis': {'S': 'Perfect match for Python/AWS.'}
                    }
                }
            }
        ]
    }
    
    handler(mock_event, {})
