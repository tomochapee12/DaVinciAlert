# DaVinciAlert 🔔

FGO公式ニュース( https://news.fate-go.jp/ )の更新をチェックし、変更があれば通知します。GitHub Actionsベースで動作。

## 機能
- FGOニュースの定期チェック（既定では3時間ごと）
- 新着があれば通知（SlackやDiscordなどへカスタム可能）

## 使用方法
1. このリポジトリをフォーク
2. 必要に応じて `.github/workflows/check-news.yml` を編集（通知先など）
3. GitHub Actions を有効にするだけでOK

## 通知のカスタマイズ
Slack WebhookやDiscord Webhookなど、自由に通知先を設定可能です。環境変数や別スクリプトと連携してご利用ください。
