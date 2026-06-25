# セットアップ手順

## 1. Supabase プロジェクト作成

1. https://supabase.com にアクセスし、アカウント作成
2. 「New Project」をクリック
3. プロジェクト名: `competitor-monitor`
4. リージョン: `Northeast Asia (Tokyo)` を選択
5. Database Password を設定（メモしておく）
6. 作成後、Settings > API から以下をメモ:
   - Project URL (`NEXT_PUBLIC_SUPABASE_URL`)
   - anon key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`)
   - service_role key (`SUPABASE_SERVICE_ROLE_KEY`)

### Google OAuth 設定

1. Supabase Dashboard > Authentication > Providers > Google
2. Enable をオンにする
3. Google Cloud Console で OAuth 2.0 クライアントIDを作成:
   - https://console.cloud.google.com/apis/credentials
   - 承認済みリダイレクトURI: `https://<your-project>.supabase.co/auth/v1/callback`
4. Client ID と Client Secret を Supabase に入力
5. Authorized domains に `lifull.com` を追加（ドメイン制限用）

### Storage バケット作成

1. Supabase Dashboard > Storage
2. 「New bucket」をクリック
3. バケット名: `screenshots`
4. Public: OFF

## 2. Google AI Studio (Gemini API)

1. https://aistudio.google.com/apikey にアクセス
2. 「Create API Key」をクリック
3. API Key をメモ (`GOOGLE_AI_API_KEY`)

## 3. Vercel デプロイ

1. https://vercel.com にGitHubアカウントでログイン
2. 「Add New Project」> GitHubリポジトリ `competitor-monitor` を選択
3. Root Directory: `apps/web` を指定
4. Environment Variables に以下を設定:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `GOOGLE_AI_API_KEY`
   - `SLACK_WEBHOOK_URL`（後で設定可）
5. Deploy

## 4. Slack Webhook（後で設定可）

1. https://api.slack.com/messaging/webhooks にアクセス
2. 「Create an App」> 「From scratch」
3. App Name: `Competitor Monitor`
4. Workspace を選択
5. 「Incoming Webhooks」を有効化
6. 「Add New Webhook to Workspace」で通知先チャンネルを選択
7. Webhook URL をメモ (`SLACK_WEBHOOK_URL`)

## 5. GitHub Actions Secrets

1. GitHub リポジトリ > Settings > Secrets and variables > Actions
2. 以下の Secrets を追加:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `GOOGLE_AI_API_KEY`
   - `SLACK_WEBHOOK_URL`
