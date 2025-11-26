#!/bin/bash

# スカッと系ショート漫画シナリオ生成ツール起動スクリプト

echo "⚡ スカッと系ショート漫画シナリオ生成ツールを起動中..."
echo "ポート: 8510"
echo "URL: http://localhost:8510"
echo ""

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Streamlitを起動（ローカルでは8510、デプロイ時は自動割り当て）
/Users/s-hashimoto/Documents/CURSOR/.venv/bin/streamlit run app.py --server.port 8510

