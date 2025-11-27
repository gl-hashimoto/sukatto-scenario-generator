import streamlit as st
import anthropic
import os
from datetime import datetime
import json
import re
import time
import traceback
from dotenv import load_dotenv, set_key

# バージョン情報
VERSION = "1.0.1"
PROMPT_VERSION = "3.0"

# Streamlit Cloud環境かどうかを検出
def is_streamlit_cloud():
    """Streamlit Cloud環境かどうかを検出"""
    # Streamlit Cloudでは HOME が /home/appuser または /home/adminuser
    home_dir = os.getenv("HOME", "")
    if "/home/appuser" in home_dir or "/home/adminuser" in home_dir:
        return True
    # 環境変数でも判定
    if os.getenv("STREAMLIT_SHARING_MODE"):
        return True
    return False

# ============================================================================
# 文字数カウント関数
# ============================================================================

def count_characters(text):
    """
    シナリオの文字数を正確にカウント
    
    Args:
        text: カウント対象のテキスト
        
    Returns:
        文字数（改行、記号、括弧を除いた純粋なテキスト文字のみ）
    """
    # 改行を削除
    text = text.replace('\n', '').replace('\r', '')

    # 除外する記号・括弧を削除
    text = re.sub(r'[※「」『』■\(\)（）…！？!?〜～\s]', '', text)

    # 残った文字数をカウント
    return len(text)

# ページ設定
st.set_page_config(
    page_title="スカッと系ショート漫画シナリオ生成ツール | 愛カツ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #333;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .version-badge {
        display: inline-block;
        background: #f0f0f0;
        color: #333;
        font-size: 0.9rem;
        font-weight: normal;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        margin-left: 1rem;
        vertical-align: middle;
    }
    
    .output-section {
        background: #f9f9f9;
        padding: 1rem;
        margin-top: 1rem;
        border: 1px solid #e0e0e0;
    }

    [data-testid="stSidebar"] .stButton button {
        justify-content: flex-start;
        text-align: left;
        padding-left: 0;
        padding-right: 0;
    }
    
    [data-testid="stSidebar"] .stButton {
        margin-bottom: -0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# マスタープロンプトを読み込む
def load_master_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "master_prompt.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# 改行を強制的に修正する関数
def enforce_line_breaks(text):
    """
    シナリオテキストの改行を強制的に修正する
    ※カメラ、※状況、セリフ、心の声をそれぞれ別の行に分離

    シンプルなアプローチ：
    1. 各行を処理
    2. 改行が必要なパターンの前に改行を挿入
    3. 結果を返す
    """
    # まず、改行が必要なパターンの前に特殊マーカーを挿入
    result = text

    # パターン1: ※カメラ、※状況説明などの前に改行
    # ただし、行頭の※は除外
    result = re.sub(r'(?<!^)(?<!\n)(※)', r'\n\1', result)

    # パターン2: キャラ名「セリフ」の前に改行（A子、B男、義母、助産師など）
    # 日本語のキャラ名パターン
    result = re.sub(r'(?<!\n)([A-Z][子男]「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(義母「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(義父「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(助産師「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(看護師「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(医師「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(弁護士「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(探偵「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(上司「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(友人「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(母「)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(父「)', r'\n\1', result)

    # パターン3: キャラ名（心の声）の前に改行
    result = re.sub(r'(?<!\n)([A-Z][子男]（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(義母（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(義父（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(助産師（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(看護師（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(医師（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(弁護士（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(探偵（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(上司（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(友人（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(母（)', r'\n\1', result)
    result = re.sub(r'(?<!\n)(父（)', r'\n\1', result)

    # 連続する改行を1つにまとめる（3つ以上の連続改行を2つに）
    result = re.sub(r'\n{3,}', '\n\n', result)

    # 各行の先頭・末尾の空白を整理
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned_lines.append(stripped)
        else:
            # 空行は保持（ただし連続しすぎないように）
            if cleaned_lines and cleaned_lines[-1] != '':
                cleaned_lines.append('')

    return '\n'.join(cleaned_lines)

# シナリオ自動チェック＆リライト関数
def check_and_fix_scenario(api_key, scenario_draft):
    """
    生成されたシナリオを自動でチェックし、品質向上のためにリライトする
    """
    client = anthropic.Anthropic(api_key=api_key)
    
    rewrite_prompt = f"""
以下のシナリオを、チェック基準に基づいて 客観的に自己評価 → 問題点抽出 → 最適な形にリライト してください。
トーンは漫画のネーム用のシナリオとして、テンポよく、読者にとって理解しやすく、感情移入しやすい形に整えてください。

【元のシナリオ】
{scenario_draft}

【ステップ1：問題点の抽出】※内部処理のみ、出力不要

以下のチェック基準に照らして、改善すべき点を把握：

▼ チェック基準
1. ストーリーのつじつま
   - 設定の矛盾はないか
   - 行動の必然性はあるか
   - 状況説明は明瞭か
   - 現実味はあるか（倫理観、違法行為、NG描写）

2. セリフと感情の自然さ
   - 会話の流れは自然か
   - 年齢・性格に合った話し方か
   - ポエム調・文学調を避けているか
   - 共感を生む感情描写になっているか

3. 話のまとまり・伏線回収
   - 伏線の貼り方と回収
   - 展開テンポ
   - ラストの納得感

4. スカッとポイントの設計
   - 前編に「小さなスカッと」があるか
   - 後編に「大きなスカッと」があるか
   - 読者が「スカッとした！」と感じられるか

5. テーマ/体験談への忠実性【超重要】
   - 入力された体験談に記載されている内容のみを使用しているか
   - 体験談に記載されていない設定・情報・要素を追加していないか
   - 体験談から大きく逸脱した展開になっていないか

6. 前後編の構成
   - 前編だけでも完結感があるか
   - 前編にスカッとポイントがあるか
   - 後編への引きが適切か
   - 後編で完全解決しているか

7. **【最重要】改行フォーマット**
   - ※カメラ指示は必ず1行目に単独で記述されているか
   - ※シーン描写（場所、状況、動作、音など）は、それぞれ必ず別の行に記述されているか
   - セリフ（「」で囲まれたもの）は、1つずつ必ず別の行に記述されているか
   - 心の声（（）で囲まれたもの）は、1つずつ必ず別の行に記述されているか
   - 同じ行に複数の要素が書かれていないか

【ステップ2：シナリオの完全リライト版を生成】

以下の条件を守って、最適化したシナリオを出力してください。

▼ リライト条件
- 前編5ページ・後編5ページのショート漫画を想定
- テンポの良いネーム用シナリオ
- **【最重要】前後編でそれぞれ完結しつつ、後編を絶対に読みたくなる構造**
  - 前編 = 問題提示 + 小スカッと（満足度60%）
  - 後編 = 真相 + 大スカッと（満足度100%）
  - 前編ラストに必ず「強烈な引き」を入れる
- **1ページ=ひとつの感情変化**を基本にする
- キャラの行動と感情が自然
- 読者が共感できる描写
- セリフは短く、説明過多を避ける
- クライマックスに向けて段階的に盛り上げる
- 伏線は自然に回収
- NG描写（鬱・殺人・宗教・差別・過度な暴力）なし
- **体験談への忠実性【最重要】**：
  - 入力された体験談に記載されている内容のみを使用すること
  - 体験談に記載されていない設定・情報・要素は一切追加しない
  - 体験談から大きく逸脱した展開は絶対に避けること
- **【必須】改行フォーマットの厳守**：
  - 各コマで、※カメラ、※状況、セリフ、心の声は必ずそれぞれ別の行に記述すること
  - 同じ行に複数の要素を書いてはいけません
  - 例：
    ```
    1コマ目
    ※カメラ：引き
    ※リビング。夕方
    ※A子が疲れた表情でソファに座っている
    A子「今日も疲れたな…」
    A子（また一人でご飯か…）
    ```

【重要】出力はリライトしたシナリオのみ。分析や評価コメントは不要です。
元のシナリオのフォーマット（【体験談の分析】から始まる形式）を維持してください。
"""

    try:
        message = client.messages.create(
            model="claude-haiku-3-5-20250313",
            max_tokens=8000,
            temperature=0.5,
            messages=[
                {"role": "user", "content": rewrite_prompt}
            ]
        )

        rewritten_scenario = message.content[0].text
        return rewritten_scenario
    except Exception as e:
        return scenario_draft

# ============================================================================
# シナリオ生成関数
# ============================================================================

def generate_scenario(api_key, experience):
    """
    Claude APIを使用してシナリオを生成
    
    Args:
        api_key: Anthropic APIキー
        experience: 体験談
        
    Returns:
        生成されたシナリオのテキスト
    """
    client = anthropic.Anthropic(api_key=api_key)

    master_prompt = load_master_prompt()

    # ユーザー入力を構造化
    user_prompt = f"""
{master_prompt}

---

## オーダー
{experience}

上記の体験談を、スカッと系ショート漫画のシナリオプロット（前編5P・後編5P）に変換してください。
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        return message.content[0].text
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

# 履歴を保存
def save_history(experience, result):
    # Streamlit Cloud環境ではファイル保存をスキップ
    if is_streamlit_cloud():
        return None

    try:
        history_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(history_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scenario_{timestamp}.json"
        filepath = os.path.join(history_dir, filename)

        data = {
            "timestamp": datetime.now().isoformat(),
            "experience": experience,
            "prompt_version": PROMPT_VERSION,
            "result": result
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath
    except Exception:
        return None

# 履歴を読み込む
def load_history(limit=10, search_query=""):
    # Streamlit Cloud環境ではファイル読み込みをスキップ
    if is_streamlit_cloud():
        return []

    try:
        history_dir = os.path.join(os.path.dirname(__file__), "output")
        if not os.path.exists(history_dir):
            return []

        history_files = sorted(
            [f for f in os.listdir(history_dir) if f.endswith('.json') and f != 'favorites.json'],
            reverse=True
        )

        histories = []
        for filename in history_files:
            filepath = os.path.join(history_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 検索クエリがある場合、フィルタリング
                if search_query:
                    if (search_query.lower() in data.get('experience', '').lower() or
                        search_query.lower() in data.get('result', '').lower()):
                        histories.append(data)
                else:
                    histories.append(data)

            # 制限数に達したら終了
            if len(histories) >= limit:
                break

        return histories
    except Exception:
        return []

# お気に入り管理
def get_favorites():
    """お気に入りリストを取得"""
    # Streamlit Cloud環境ではファイル操作をスキップ
    if is_streamlit_cloud():
        return []

    try:
        favorites_file = os.path.join(os.path.dirname(__file__), "output", "favorites.json")
        if os.path.exists(favorites_file):
            with open(favorites_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_favorites(favorites):
    """お気に入りリストを保存"""
    # Streamlit Cloud環境ではファイル操作をスキップ
    if is_streamlit_cloud():
        return

    try:
        favorites_file = os.path.join(os.path.dirname(__file__), "output", "favorites.json")
        os.makedirs(os.path.dirname(favorites_file), exist_ok=True)
        with open(favorites_file, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def toggle_favorite(timestamp):
    """お気に入りの追加/削除を切り替え"""
    favorites = get_favorites()
    if timestamp in favorites:
        favorites.remove(timestamp)
    else:
        favorites.append(timestamp)
    save_favorites(favorites)
    return timestamp in favorites

def is_favorite(timestamp):
    """お気に入りかどうかを確認"""
    favorites = get_favorites()
    return timestamp in favorites

# 統計情報を取得
def get_statistics():
    """生成統計情報を取得"""
    # Streamlit Cloud環境ではファイル操作をスキップ
    if is_streamlit_cloud():
        return {"total_count": 0}

    try:
        history_dir = os.path.join(os.path.dirname(__file__), "output")
        if not os.path.exists(history_dir):
            return {"total_count": 0}

        history_files = [f for f in os.listdir(history_dir) if f.endswith('.json') and f != 'favorites.json']

        stats = {
            "total_count": len(history_files)
        }

        return stats
    except Exception:
        return {"total_count": 0}

# シナリオを編集して保存
def update_history(timestamp, updated_result):
    """履歴のシナリオを更新"""
    # Streamlit Cloud環境ではファイル操作をスキップ
    if is_streamlit_cloud():
        return False

    try:
        history_dir = os.path.join(os.path.dirname(__file__), "output")
        history_files = [f for f in os.listdir(history_dir) if f.endswith('.json') and f != 'favorites.json']

        for filename in history_files:
            filepath = os.path.join(history_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get('timestamp', '') == timestamp:
                    data['result'] = updated_result
                    data['updated_at'] = datetime.now().isoformat()
                    data['is_edited'] = True
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return True
    except Exception:
        pass
    return False

# 履歴を削除
def delete_history(timestamp):
    """指定されたtimestampの履歴を削除"""
    # Streamlit Cloud環境ではファイル操作をスキップ
    if is_streamlit_cloud():
        return False

    try:
        history_dir = os.path.join(os.path.dirname(__file__), "output")
        history_files = [f for f in os.listdir(history_dir) if f.endswith('.json') and f != 'favorites.json']

        for filename in history_files:
            filepath = os.path.join(history_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get('timestamp', '') == timestamp:
                        # お気に入りからも削除
                        favorites = get_favorites()
                        if timestamp in favorites:
                            favorites.remove(timestamp)
                            save_favorites(favorites)
                        # ファイルを削除
                        os.remove(filepath)
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False

# APIキーを保存
def save_api_key(api_key):
    """
    APIキーを.envファイルに保存する
    """
    # Streamlit Cloud環境ではファイル操作をスキップ
    if is_streamlit_cloud():
        return False

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    try:
        # .envファイルが存在しない場合は作成
        if not os.path.exists(env_path):
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"ANTHROPIC_API_KEY={api_key}\n")
        else:
            # 既存の.envファイルを更新
            set_key(env_path, "ANTHROPIC_API_KEY", api_key)

        return True
    except Exception as e:
        st.error(f"APIキーの保存に失敗しました: {str(e)}")
        return False

# APIキーを取得する関数（Streamlit Cloud対応）
def get_api_key():
    """Streamlit CloudのsecretsまたはローカルのAPIキーを取得"""
    # まずStreamlit Cloudのsecretsを確認
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    # ローカル環境の場合は環境変数から
    return os.getenv("ANTHROPIC_API_KEY", "")

# メイン画面
def main():
    # .envファイルを読み込む（ローカル環境用）
    load_dotenv()

    # ヘッダー
    st.markdown(f'<div class="main-header">⚡ スカッと系ショート漫画シナリオ生成ツール <span class="version-badge">v{VERSION}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">前編5P・後編5P完結形式（プロンプトv{PROMPT_VERSION}）｜愛カツ専用ツール</div>', unsafe_allow_html=True)

    # サイドバー設定
    with st.sidebar:
        # プロジェクト識別情報
        st.markdown("""
        <div style="background-color: #FFE5E5; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border: 2px solid #FF6B6B;">
            <h3 style="color: #FF0000; margin: 0; text-align: center;">⚠️ プロジェクト識別</h3>
            <p style="color: #333; margin: 0.5rem 0; text-align: center; font-weight: bold; font-size: 1.1rem;">
                ⚡ スカッと系ショート漫画シナリオ生成ツール<br>
                🔌 ポート: <span style="color: #FF0000; font-size: 1.3rem;">8510</span>
            </p>
            <p style="color: #666; margin: 0; text-align: center; font-size: 0.85rem;">
                ディレクトリ: sukatto-scenario-generator
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.header("⚙️ 設定")

        # APIキー設定（Streamlit Cloud対応）
        default_api_key = get_api_key()

        # Streamlit Cloudの場合はSecretsから自動取得
        if default_api_key:
            api_key = default_api_key
            st.success("✅ APIキー設定済み")
        else:
            api_key = st.text_input(
                "Anthropic API Key",
                type="password",
                value="",
                help="Claude APIキーを入力してください"
            )

            # APIキー保存ボタン（ローカル環境のみ）
            if api_key:
                if st.button("💾 APIキーを保存", help="APIキーを.envファイルに保存します"):
                    if save_api_key(api_key):
                        st.success("✅ APIキーを保存しました！")
                        st.info("次回起動時から自動的に読み込まれます")

        st.divider()

        # 形式は前後編5P+5Pに固定
        story_format = "前後編2話完結（前編5ページ・後編5ページ）"
        st.info(f"📖 **形式**: {story_format}")

        st.divider()

        # 統計情報表示
        st.subheader("📊 統計情報")
        stats = get_statistics()
        if stats["total_count"] > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("総生成数", stats["total_count"])
            with col2:
                favorites_count = len(get_favorites())
                st.metric("お気に入り", favorites_count)
        else:
            st.info("まだ統計情報がありません")

        st.divider()

        # 履歴表示
        st.subheader("📚 生成履歴")
        
        # 検索機能
        search_query = st.text_input("🔍 検索", placeholder="体験談や内容で検索...", key="history_search")
        
        # フィルター
        filter_type = st.radio(
            "フィルター",
            ["すべて", "お気に入りのみ"],
            horizontal=True,
            key="history_filter"
        )
        
        if st.button("🔄 履歴を更新", type="primary"):
            st.rerun()

        histories = load_history(limit=20, search_query=search_query)
        
        # お気に入りフィルター
        if filter_type == "お気に入りのみ":
            favorites = get_favorites()
            histories = [h for h in histories if h.get('timestamp', '') in favorites]
        
        if histories:
            st.caption(f"表示中: {len(histories)}件")
            for i, hist in enumerate(histories, 1):
                timestamp = hist.get('timestamp', '')
                experience_preview = hist.get('experience', '')[:30] if hist.get('experience') else '体験談なし'
                is_fav = is_favorite(timestamp) if timestamp else False
                
                # タイトル（リンク風ボタン）
                if st.button(
                    f"{experience_preview}",
                    key=f"hist_link_{i}",
                    type="tertiary",
                    use_container_width=True
                ):
                    st.session_state.selected_history = hist
                    st.session_state.selected_history_index = i
                    st.rerun()
                
                # お気に入りボタン
                if timestamp:
                    fav_key = f"fav_{i}_{timestamp}"
                    if st.button(
                        "⭐" if is_fav else "☆", 
                        key=fav_key, 
                        type="tertiary",
                        help="お気に入り"
                    ):
                        toggle_favorite(timestamp)
                        st.rerun()
                
                # 区切り線
                st.markdown("<hr style='margin: 0.2rem 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
        else:
            st.info("まだ生成履歴がありません" if not search_query and filter_type == "すべて" else "検索結果がありません")

        st.divider()

        # ツール情報
        with st.expander("ℹ️ ツール情報"):
            st.markdown(f"""
**バージョン情報**
- アプリバージョン: v{VERSION}
- プロンプトバージョン: v{PROMPT_VERSION}

**特徴**
- ⚡ スカッと系ショート漫画専用
- 📖 前編5P・後編5Pの完結形式
- 💬 体験談ベースのシナリオ生成
- 🎯 10種類の落ちのパターンから自動選定

**生成時間**
- 初稿生成：約30〜60秒
- 自動リライト：約20〜40秒
- 合計：約1〜2分
            """)

    # メインコンテンツ
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("✍️ 体験談を入力")
        experience = st.text_area(
            "シナリオ化したい体験談を自由に記述してください",
            height=300,
            placeholder="例：\n夫にモラハラされていた私が、ある日親友の一言で離婚を決意。\n義母に理不尽な要求をされ続けていたが、ついに反撃した。\n婚活パーティーで出会った男性が、実は...",
            help="具体的な体験談を入力すると、より良いシナリオが生成されます"
        )

    with col2:
        st.header("💡 体験談のヒント")
        st.info("""
**人気のテーマ例：**

👨‍👩‍👧 **家族関係**
- 義家族とのトラブル
- 夫婦間のモラハラ
- 親の理不尽な要求

💔 **恋愛・婚活**
- 婚活パーティーの体験
- 浮気・不倫の暴露
- 別れの決断

🏢 **職場・人間関係**
- パワハラ上司
- 理不尽な同僚
- 立場逆転の瞬間

✨ **スカッとポイント**
- 反撃の一言
- 証拠の提示
- 第三者の登場
- 因果応報
        """)

    # 生成ボタン
    st.divider()

    if not api_key:
        st.warning("⚠️ サイドバーでAnthropic API Keyを入力してください")
    elif not experience:
        st.warning("⚠️ 体験談を入力してください")
    else:
        if st.button("🎬 シナリオを生成する", type="primary"):
            try:
                # 進捗表示用のプレースホルダー
                progress_container = st.container()
                
                with progress_container:
                    st.info("🚀 シナリオ生成を開始します...")
                    
                    # ステップ1: シナリオ生成
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("📝 ステップ1/2: シナリオ初稿を作成中... (約30-60秒)")
                    progress_bar.progress(25)
                    
                    draft_scenario = generate_scenario(api_key, experience)
                    
                    # エラーチェック
                    if draft_scenario.startswith("エラーが発生しました"):
                        st.error(f"❌ シナリオ生成中にエラーが発生しました: {draft_scenario}")
                        st.info("💡 解決方法:\n- APIキーが正しいか確認してください\n- インターネット接続を確認してください\n- しばらく待ってから再試行してください")
                    else:
                        progress_bar.progress(50)
                        
                        # ステップ2: 自動チェック＆リライト
                        status_text.text("✨ ステップ2/2: 品質チェック＆自動リライト中... (約20-40秒)")
                        progress_bar.progress(75)
                        
                        final_scenario = check_and_fix_scenario(api_key, draft_scenario)
                        
                        # 改行を強制的に修正
                        final_scenario = enforce_line_breaks(final_scenario)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ シナリオ生成が完了しました！")
                        
                        # セッションステートに保存
                        st.session_state.result = final_scenario
                        st.session_state.experience = experience

                        # 履歴に保存
                        save_history(experience, final_scenario)
                        
                        # 成功メッセージ
                        st.success("🎉 シナリオが生成されました！")
                        st.balloons()
                        
                        # 少し待ってからリロード
                        time.sleep(1)
                        st.rerun()
                        
            except anthropic.APIError as e:
                st.error(f"❌ APIエラーが発生しました: {str(e)}")
                st.info("💡 解決方法:\n- APIキーとクレジット残高を確認してください\n- APIの利用制限を確認してください")
            except Exception as e:
                st.error(f"❌ 予期しないエラーが発生しました: {str(e)}")
                st.info("💡 エラーが続く場合は、開発者にお問い合わせください")
                import traceback
                with st.expander("🔍 詳細なエラー情報"):
                    st.code(traceback.format_exc())

    # 結果表示（新規生成 or 履歴選択）
    if "selected_history" in st.session_state:
        # 履歴が選択された場合
        st.divider()
        hist = st.session_state.selected_history
        st.header(f"📝 履歴 #{st.session_state.selected_history_index}")

        # 履歴情報の表示
        prompt_ver = hist.get('prompt_version', '不明')
        st.info(f"""
**体験談**: {hist.get('experience', 'なし')}
**日時**: {hist['timestamp'][:19]}
**プロンプトバージョン**: v{prompt_ver}
        """)

        # シナリオ表示（改行処理を適用し、HTMLの<br>に変換）
        formatted_result = enforce_line_breaks(hist['result'])
        # Markdownで改行を表示するため、\nを<br>に変換
        html_result = formatted_result.replace('\n', '<br>')
        st.markdown(f'<div class="output-section">{html_result}</div>', unsafe_allow_html=True)

        # 編集機能
        with st.expander("✏️ シナリオを編集", expanded=False):
            edited_scenario = st.text_area(
                "シナリオを編集してください",
                value=hist['result'],
                height=400,
                key=f"edit_{hist.get('timestamp', '')}"
            )
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                if st.button("💾 保存", key=f"save_edit_{hist.get('timestamp', '')}"):
                    if update_history(hist.get('timestamp', ''), edited_scenario):
                        st.success("✅ シナリオを更新しました！")
                        # 履歴を再読み込み
                        hist['result'] = edited_scenario
                        st.session_state.selected_history = hist
                        st.rerun()
                    else:
                        st.error("❌ 保存に失敗しました")
            
            with col_edit2:
                if st.button("↩️ キャンセル", key=f"cancel_edit_{hist.get('timestamp', '')}"):
                    st.rerun()

        # アクションボタン
        col1, col2, col3, col4 = st.columns(4)
        
        timestamp_str = hist['timestamp'][:19].replace(":", "").replace("-", "").replace(" ", "_")

        # 完全な内容を作成
        full_content = f"""# スカッと系ショート漫画シナリオ

## 生成情報
- 日時: {hist['timestamp'][:19]}
- プロンプトバージョン: v{prompt_ver}

## 体験談
{hist.get('experience', 'なし')}

## 生成されたシナリオ

{hist['result']}
"""

        with col1:
            st.download_button(
                label="📄 TXT",
                data=full_content,
                file_name=f"scenario_{timestamp_str}.txt",
                mime="text/plain",
                key="hist_txt_dl"
            )

        with col2:
            st.download_button(
                label="📋 MD",
                data=full_content,
                file_name=f"scenario_{timestamp_str}.md",
                mime="text/markdown",
                key="hist_md_dl"
            )
        
        with col3:
            # お気に入りボタン
            timestamp = hist.get('timestamp', '')
            is_fav = is_favorite(timestamp) if timestamp else False
            if st.button("⭐ お気に入り" if is_fav else "☆ お気に入り", key=f"fav_detail_{timestamp}"):
                toggle_favorite(timestamp)
                st.rerun()
        
        with col4:
            col_close, col_delete = st.columns(2)
            with col_close:
                if st.button("✖️ 閉じる"):
                    del st.session_state.selected_history
                    del st.session_state.selected_history_index
                    st.rerun()
            with col_delete:
                if st.button("🗑️ 削除", type="secondary"):
                    if delete_history(hist.get('timestamp', '')):
                        st.success("✅ 履歴を削除しました")
                        del st.session_state.selected_history
                        del st.session_state.selected_history_index
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ 削除に失敗しました")

    elif "result" in st.session_state:
        # 新規生成された場合
        st.divider()
        st.header("📝 生成されたシナリオ")

        # 結果表示エリア（改行を<br>に変換して表示）
        html_result = st.session_state.result.replace('\n', '<br>')
        st.markdown(f'<div class="output-section">{html_result}</div>', unsafe_allow_html=True)

        # 編集機能
        with st.expander("✏️ シナリオを編集", expanded=False):
            edited_scenario_new = st.text_area(
                "シナリオを編集してください",
                value=st.session_state.result,
                height=400,
                key="edit_new_scenario"
            )
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                if st.button("💾 保存", key="save_edit_new"):
                    # セッションステートを更新
                    st.session_state.result = edited_scenario_new
                    st.success("✅ シナリオを更新しました！")
                    st.rerun()
            
            with col_edit2:
                if st.button("↩️ キャンセル", key="cancel_edit_new"):
                    st.rerun()

        # アクションボタン
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # テキストファイルダウンロード
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scenario_{timestamp}.txt"

            st.download_button(
                label="📄 テキストでダウンロード",
                data=st.session_state.result,
                file_name=filename,
                mime="text/plain"
            )

        with col2:
            # Markdownファイルダウンロード
            md_filename = f"scenario_{timestamp}.md"

            st.download_button(
                label="📋 Markdownでダウンロード",
                data=st.session_state.result,
                file_name=md_filename,
                mime="text/markdown"
            )
        
        with col3:
            # お気に入りボタン（新規生成の場合は履歴に保存後にお気に入り可能）
            st.info("💡 履歴に保存されるとお気に入り機能が利用できます")
        
        with col4:
            if st.button("🔄 新しいシナリオを生成"):
                del st.session_state.result
                if "experience" in st.session_state:
                    del st.session_state.experience
                st.rerun()

if __name__ == "__main__":
    main()

