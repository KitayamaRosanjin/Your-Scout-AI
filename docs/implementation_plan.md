# Implementation Plan - Your Scout AI

## Goal Description
「自分にマッチする（勝てる）求人だけをAIが選定して通知する」SaaS。
20代転職回数多めというハンデを覆すため、自分のスキルと求人票の適合度をLLMで客観的に判定し、無駄な応募を減らして勝率を上げることを目的とする。

## User Review Required
> [!NOTE]
> **Python 3.14 Support**: AWS LambdaのManaged Runtimeは通常最新バージョンのサポートに時間がかかるため、**Docker Container Image**形式でのLambdaデプロイを採用します。これによりPython 3.14を確実に利用できます。
> **Target Sites**: まずはRSSフィード等の構造化データが取得可能なサイトをターゲットとします。
> **Notification**: 実装容易性とコストから **Discord/Slack Webhook** を採用します。

## Functional Requirements (Conditions)

### 1. 求人情報収集 (Collector)
*   **Target**: 指定キーワード（Python, AWS等）で求人サイト(RSS/API)を定期巡回。
*   **Frequency**: 1日1回 (AWS EventBridge)。

### 2. マッチングエンジン (Brain)
*   **Input**: ユーザーの履歴書/職務経歴書 (Markdownテキストとして保存)。
*   **Process**:
    *   求人票の必須要件・歓迎要件を抽出。
    *   ユーザーのスキルセットと比較。
    *   **「勝率スコア (0-100%)」**と**「推薦理由」**を生成。
*   **Filter**: スコア80%以上のみ通知、など。

### 3. 通知 (Notifier)
*   **Content**: 求人タイトル、URL、勝率スコア、一言コメント。

## Technical Stack & Architecture
*   **Language**: **Python 3.14** (Local & Lambda Runtime)
*   **IaC**: AWS CDK (Python) - **DockerImageFunction** construct
*   **Architecture**: Serverless (Free Tier Optimized)

```mermaid
graph TD
    Trigger[EventBridge (Cron)] --> Collector[Lambda: Collector (Container)]
    Collector -->|Job Data| DDB[(DynamoDB)]
    DDB --Stream/Trigger--> Matcher[Lambda: Matcher (Container)]
    Matcher -->|LLM API (OpenAI/Gemini)| AI[AI Model]
    AI -->|Analysis Result| DDB
    DDB --Stream/Trigger--> Notifier[Lambda: Notifier (Container)]
    Notifier --> User[User (Discord/Slack)]
```

## Proposed Changes

### Configuration
#### [NEW] [cdk_app](file:///C:/Users/avign/.gemini/antigravity/scratch/portfolio-saas/cdk_app/)
CDKプロジェクトディレクトリ。

### Database
#### DynamoDB Tables
*   `JobsTable`: 求人情報、判定ステータス、AI分析結果を保存。

### Functions (Lambda via Docker)
*   `Dockerfile`: Python 3.14ベースのコンテナイメージ定義。
*   `app/collector.py`: 求人等の取得。
*   `app/matcher.py`: LLM呼び出しと判定。
*   `app/notifier.py`: 通知送信。

## Verification Plan
### Automated Tests
*   `pytest` によるロジック単体テスト。

### Manual Verification
*   CDK deploy によるAWS環境構築確認。
*   `cdk synth` によるCloudFormationテンプレート生成確認。
