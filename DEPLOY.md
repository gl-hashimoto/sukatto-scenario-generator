# 🚀 Streamlit Cloud デプロイ手順

## 📋 事前準備

### 必要なもの
- GitHubアカウント
- Streamlit Cloudアカウント（GitHubでログイン）
- Anthropic APIキー

---

## ステップ1: GitHubリポジトリを作成

```bash
cd "/Users/s-hashimoto/Documents/CURSOR/#biz_制作ツール/8510_sukatto-scenario-generator"

# Gitリポジトリを初期化
git init

# ファイルを追加
git add .

# 初回コミット
git commit -m "Initial commit: スカッと系ショート漫画シナリオ生成ツール v1.0.0"

# GitHubにリポジトリを作成（gh CLIを使用）
gh repo create sukatto-scenario-generator --private --source=. --push
```

---

## ステップ2: Streamlit Cloudでデプロイ

### 2-1. Streamlit Cloudにアクセス
1. https://share.streamlit.io/ にアクセス
2. GitHubアカウントでログイン

### 2-2. 新しいアプリをデプロイ
1. **「New app」**ボタンをクリック
2. 以下の情報を入力：
   - **Repository**: `gl-hashimoto/sukatto-scenario-generator`
   - **Branch**: `main`
   - **Main file path**: `app.py`

### 2-3. Advanced settings（重要！）
1. **「Advanced settings」**をクリック
2. **Python version**: `3.11` を選択

### 2-4. Secretsの設定（最重要！）
**「Advanced settings」→「Secrets」タブ**で以下を入力：

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-あなたの実際のAPIキー"
```

⚠️ **注意事項:**
- APIキーはダブルクォーテーション（`"`）で囲む
- このキーは絶対に公開しないでください

### 2-5. デプロイ実行
1. **「Deploy!」**ボタンをクリック
2. デプロイが開始されます（通常2〜3分）

---

## ステップ3: デプロイ完了後の確認

デプロイが完了したら、以下のURLでアクセス可能：

**https://sukatto-scenario-generator.streamlit.app/**

### ✅ 動作確認チェックリスト
- [ ] アプリが正常に起動する
- [ ] タイトルが表示される
- [ ] 体験談入力エリアが表示される
- [ ] シナリオ生成ボタンが機能する
- [ ] 生成されたシナリオが正しく改行表示される

---

## 🔄 更新方法

コードを更新した場合：
```bash
git add .
git commit -m "Update: 変更内容"
git push
```

GitHubへのプッシュで自動的に再デプロイされます。

---

## 🐛 トラブルシューティング

### エラー: "ANTHROPIC_API_KEY not found"
→ Streamlit CloudのSettings → Secretsを確認

### エラー: "ModuleNotFoundError"
→ requirements.txtが正しいか確認し、再プッシュ

---

## 📁 デプロイに必要なファイル

```
8510_sukatto-scenario-generator/
├── app.py                 # メインアプリ
├── requirements.txt       # 依存関係
├── runtime.txt           # Pythonバージョン
├── .streamlit/
│   └── config.toml       # Streamlit設定
├── prompts/
│   └── スカッと系ショート漫画シナリオ生成プロンプト.md
└── .gitignore
```
