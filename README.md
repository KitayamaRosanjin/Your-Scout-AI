# Your Scout AI 
https://g2euc27ywdy75lppplx646nrca0exeix.lambda-url.ap-northeast-1.on.aws/
**"No more spray and pray. Analyze, Select, and Win."**

自分にマッチする（勝てる）求人だけをAIが選定して通知する、20代エンジニアのための転職支援SaaS。
（非IT出身・転職回数多めの自身の課題を解決するために開発）

![Architecture](https://img.shields.io/badge/Architecture-Serverless-orange)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![AWS CDK](https://img.shields.io/badge/AWS%20CDK-Infrastructure%20as%20Code-yellow)

## Background (開発背景)

「転職回数が多いと、書類選考で弾かれやすい」
そんなハンデを覆すには、**「自分のスキルセットと企業の募集用件が完璧にマッチする場所」**をピンポイントで攻めるしかありません。
しかし、毎日求人サイトを目視で巡回し、募集要項を読み込むのは非効率です。

そこで、**「AIが私の代わりに24時間求人を監視し、勝率の高いカードだけを配ってくれる」** システムを開発しました。

## Architecture

完全サーバーレス・アーキテクチャを採用し、**維持費ほぼ0円**を実現しています。
Python 3.14の最新機能を利用するため、Lambdaは**コンテナイメージ (Docker)** でデプロイしています。

```mermaid
graph TD
    Trigger[EventBridge (Daily Cron)] --> Collector[Lambda: Collector]
    
    subgraph "Core Logic (Python 3.14)"
    Collector -->|Fetch RSS| Web(Job Sites)
    Collector -->|Save New Jobs| DDB[(DynamoDB)]
    
    DDB --Stream--> Matcher[Lambda: Matcher]
    Matcher -->|Analyze Match| LLM[AI Model (Mock/OpenAI)]
    Matcher -->|Update Status| DDB
    
    DDB --Stream--> Notifier[Lambda: Notifier]
    Notifier -->|High Score Only| Discord[Discord/Slack]
    end
```

### Tech Stack
*   **Infrastructure**: AWS CDK (Python)
*   **Backend**: AWS Lambda (Docker Container Image)
*   **Database**: Amazon DynamoDB (On-Demand)
*   **Language**: Python 3.14.0 (Latest)
*   **CI/CD**: GitHub Actions (Planned)

##  Features

1.  **Smart Collection**: RSSフィード等から自動で求人を収集。`ConditionExpression` を用いた効率的な重複排除。
2.  **AI Matching**: 求人の「必須スキル」「歓迎スキル」を抽出し、事前登録したレジュメと照合。「勝てる確率」をスコアリング。
3.  **Real-time Notification**: マッチ度が高い求人が見つかった瞬間、DynamoDB Streams駆動で通知。
4.  **Interactive Live Demo**: 使用者がその場で検索・体験できるWebダッシュボード機能。
    *   **Lambda Function URL** を用いたサーバーレス配信。
    *   **Safety & Domain Filter**: 不適切なコンテンツやプレスリリース記事を自動で除外するフィルタリングエンジン搭載。
    *   [Live Demo URL](https://g2euc27ywdy75lppplx646nrca0exeix.lambda-url.ap-northeast-1.on.aws/)
5.  **Resume Management**: Webダッシュボードから職務経歴書を直接入力・更新可能。
    *   入力されたMarkdown形式のレジュメはDynamoDBに保存され、即座にAIマッチングエンジンの判断基準として適用されます。

##  Usage

## Prerequisites
*   AWS CLI configured
*   Docker installed
*   CDK installed

## Deploy
```bash
# 1. Clone
git clone https://github.com/KitayamaRosanjin/Your-Scout-AI.git
cd Your-Scout-AI

# 2. Setup Dependencies
pip install -r cdk_app/requirements.txt

# 3. Deploy
cd cdk_app
cdk deploy
```

##  Author
**KitayamaRosanjin**
*   20代 / エンジニア (Ex-事務職)
*   「ないものは作る」精神でSaaS開発に挑戦中。

---
*This project serves as a technical portfolio demonstrating Full-Stack Serverless capabilities.*
