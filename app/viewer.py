import boto3
import os
import json
import base64
import urllib.parse
import feedparser
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name) if table_name else None

RESUME_ID = "MY_RESUME"

def handler(event, context):
    try:
        # Determine HTTP Method
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        
        demo_results = []
        search_keyword = ""
        user_skills = ""
        current_resume = get_resume()
        
        if http_method == 'POST':
            # Handle Form Submission
            body = event.get('body', '')
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(body).decode('utf-8')
            
            params = urllib.parse.parse_qs(body)
            
            # Check if this is a Resume Update
            if 'resume_text' in params:
                new_resume_text = params['resume_text'][0]
                save_resume(new_resume_text)
                current_resume = new_resume_text # Update display
            else:
                # Regular Search
                search_keyword = params.get('keyword', [''])[0]
                user_skills = params.get('skills', [''])[0]
                if search_keyword:
                    demo_results = run_live_search(search_keyword, user_skills)
        
        # Always fetch latest DB jobs
        db_jobs = get_db_jobs()
        
        # Generate HTML
        html_content = generate_html(db_jobs, demo_results, search_keyword, user_skills, current_resume)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": html_content
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": f"Internal Server Error: {str(e)}"
        }

def get_resume():
    if not table: return ""
    try:
        resp = table.get_item(Key={'job_id': RESUME_ID})
        return resp.get('Item', {}).get('text', '')
    except Exception as e:
        print(f"Failed to get resume: {e}")
        return ""

def save_resume(text):
    if not table: return
    try:
        table.put_item(Item={
            'job_id': RESUME_ID,
            'text': text,
            'updated_at': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Failed to save resume: {e}")

def get_db_jobs():
    if not table: return []
    try:
        response = table.scan()
        items = [i for i in response.get('Items', []) if i['job_id'] != RESUME_ID] # Exclude resume item
        items.sort(key=lambda x: x.get('fetched_at', ''), reverse=True)
        return items
    except Exception:
        return []

def run_live_search(keyword, skills):
    """
    Fetch RSS and perform simple matching on the fly.
    """
    # Safety Filter: Block queries that contain NG words
    NG_WORDS = ["sex", "porn", "xxx", "dead", "kill", "murder", "hate", "racist"] 
    if any(ng in keyword.lower() for ng in NG_WORDS):
        return []

    # Job-focus Filter
    job_query = f"{keyword} (求人 OR 採用 OR 募集 OR エンジニア)"
    encoded_keyword = urllib.parse.quote(job_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    
    feed = feedparser.parse(rss_url)
    results = []
    
    skills_list = [s.strip().lower() for s in skills.split(',') if s.strip()]
    
    # Noise Filter
    NOISE_WORDS = [
        "まとめ", "比較", "ランキング", "おすすめ", "選", "学習", "スクール", 
        "講座", "入門", "とは", "ニュース", "解説", "相場", "理由",
        "使ってみた", "感想", "リリース", "Watch", "速報", "レポート", 
        "研究", "なぜ", "Tips", "エラー", "解決", "体験記", "開始"
    ]
    
    # Domain Filter
    NOISE_DOMAINS = [
        "prtimes.jp", "atpress.ne.jp", "itmedia.co.jp", "nikkei.com", 
        "yahoo.co.jp", "impress.co.jp", "asahi.com", "mainichi.jp",
        "tech-camp.in", "runteq.jp", "samurai-engineer.jp", "python.jp",
        "qiita.com", "zenn.dev", "note.com"
    ]

    for entry in feed.entries:
        if len(results) >= 10: break
        
        title = entry.title
        link = entry.link
        
        if any(ng in title.lower() for ng in NG_WORDS): continue
        if any(noise in title for noise in NOISE_WORDS): continue
        if any(domain in link for domain in NOISE_DOMAINS): continue
        
        # Simple Scoring Logic
        score = 50 
        reason = "Basic Match"
        title_lower = title.lower()
        matched_skills = [s for s in skills_list if s in title_lower]
        if matched_skills:
            score += len(matched_skills) * 15
            reason = f"Matches skills: {', '.join(matched_skills)}"
        
        score = min(score, 99)
        results.append({
            "title": title,
            "url": link,
            "status": "LIVE", 
            "score": str(score),
            "reason": reason,
            "fetched_at": datetime.now().isoformat()
        })
    
    results.sort(key=lambda x: int(x['score']), reverse=True)
    return results

def generate_html(db_jobs, demo_jobs, keyword, skills, resume_text):
    
    # --- Generate Demo Results HTML ---
    demo_section = ""
    if demo_jobs:
        cards = generate_job_cards(demo_jobs, is_demo=True)
        demo_section = f"""
        <div class="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-12 animate-fade-in">
            <h2 class="text-2xl font-bold text-blue-900 mb-4 flex items-center">
                <span class="text-3xl mr-2">🎯</span> Demo Results for "{keyword}"
            </h2>
            <div class="grid gap-4">
                {cards}
            </div>
        </div>
        """
    elif keyword:
         demo_section = f"""
        <div class="bg-yellow-50 border border-yellow-200 rounded-xl p-6 mb-12">
            <p class="text-yellow-800 font-bold">No jobs found for "{keyword}". Try "Python" or "Remote".</p>
        </div>
        """

    # --- Generate DB Jobs HTML ---
    db_cards = generate_job_cards(db_jobs)
    
    # --- Resume Section Logic ---
    default_resume = "## Professional Summary\\nBackend Engineer... (Edit this area)"
    display_resume = resume_text if resume_text else default_resume

    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Scout AI - Interactive Demo</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .animate-fade-in {{ animation: fadeIn 0.5s ease-out; }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
    </head>
    <body class="bg-gray-50 min-h-screen">
        <div class="max-w-4xl mx-auto px-4 py-12">
            <header class="text-center mb-10">
                <h1 class="text-4xl font-extrabold text-gray-900 mb-2 tracking-tight">Your Scout AI 🤖</h1>
                <p class="text-lg text-gray-600">Analyze, Select, and Win.</p>
            </header>
            
            <!-- Resume Management Section -->
            <section class="bg-white rounded-xl shadow p-6 mb-8 border border-gray-200">
                <details>
                    <summary class="cursor-pointer font-bold text-gray-700 flex justify-between items-center">
                        <span>📄 My Resume & Match Settings</span>
                        <span class="text-blue-500 text-sm">View / Edit</span>
                    </summary>
                    <div class="mt-4">
                        <form method="POST">
                            <label class="block text-sm font-medium text-gray-700 mb-2">Resume Content (Markdown supported)</label>
                            <textarea name="resume_text" rows="10" class="w-full p-3 border rounded-lg font-mono text-sm bg-gray-50 mb-3 focus:ring-2 focus:ring-blue-500">{display_resume}</textarea>
                            <div class="flex justify-end">
                                <button type="submit" class="bg-gray-800 hover:bg-gray-900 text-white font-bold py-2 px-6 rounded-lg transition-colors">
                                    Save Resume Logic
                                </button>
                            </div>
                        </form>
                        <div class="mt-6 pt-6 border-t border-gray-100">
                            <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">Current Resume Preview</h3>
                            <div class="prose prose-sm max-w-none bg-gray-50 p-4 rounded-lg border border-gray-200 whitespace-pre-wrap">
{display_resume}
                            </div>
                        </div>
                    </div>
                </details>
            </section>
            
            <!-- Interactive Demo Form -->
            <section class="bg-white rounded-xl shadow-lg p-8 mb-12 border border-gray-100">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-xl font-bold text-gray-800">⚡ Interactive Live Demo</h2>
                    <span class="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">Try it now</span>
                </div>
                <form method="POST" class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Target Keyword</label>
                            <input type="text" name="keyword" value="{keyword}" placeholder="e.g., Python, AWS, Remote" required
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Your Skills (Comma separated)</label>
                            <input type="text" name="skills" value="{skills}" placeholder="e.g., Django, React, Docker"
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                        </div>
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors shadow-md flex justify-center items-center">
                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        Search & Match Live
                    </button>
                </form>
            </section>
            
            <main>
                {demo_section}
                
                <div class="mt-16">
                    <h2 class="text-lg font-semibold text-gray-500 mb-4 border-b pb-2">📅 Scheduled Collection History ({len(db_jobs)})</h2>
                    {db_cards}
                </div>
            </main>
            
            <footer class="mt-12 text-center text-gray-400 text-sm">
                <p>&copy; 2026 Your Scout AI. Powered by AWS Serverless (Lambda + DynamoDB).</p>
            </footer>
        </div>
    </body>
    </html>
    """

def generate_job_cards(jobs, is_demo=False):
    cards = ""
    for job in jobs:
        title = job.get('title', 'No Title')
        url = job.get('url', '#')
        status = job.get('status', 'NEW')
        score = job.get('score', '0')
        reason = job.get('reason', 'Analysis pending...')
        fetched_at = job.get('fetched_at', '')[:10]
        
        # Styling
        if is_demo:
             card_class = "bg-white border-l-4 border-blue-500 shadow-sm"
        else:
             card_class = "bg-white border border-gray-100"
             
        status_color = "bg-gray-100 text-gray-800"
        if status == 'MATCHED': status_color = "bg-green-100 text-green-800"
        elif status == 'LIVE': status_color = "bg-purple-100 text-purple-800"
            
        cards += f"""
        <div class="{card_class} rounded-lg p-5 mb-4 hover:shadow-md transition-shadow">
            <div class="flex justify-between items-start mb-2">
                <span class="px-2 py-1 text-xs font-semibold rounded {status_color}">{status}</span>
                <span class="text-xs text-gray-400">{fetched_at}</span>
            </div>
            <h3 class="text-lg font-bold text-gray-900 mb-2 truncate">
                <a href="{url}" target="_blank" class="hover:text-blue-600 transition-colors">{title}</a>
            </h3>
            <div class="flex items-center mb-3">
                <div class="flex-1 h-1.5 bg-gray-200 rounded-full mr-3">
                    <div class="h-1.5 bg-blue-600 rounded-full" style="width: {score}%"></div>
                </div>
                <span class="text-sm font-bold text-blue-600">{score}%</span>
            </div>
            <p class="text-gray-600 text-xs bg-gray-50 p-2 rounded">{reason}</p>
             <div class="mt-3 text-right">
                <a href="{url}" target="_blank" class="text-xs font-medium text-blue-500 hover:text-blue-700">View Job &rarr;</a>
            </div>
        </div>
        """
    return cards

if __name__ == "__main__":
    pass
