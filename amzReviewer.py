import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re

# Gemini APIの初期化（Secretsから取得）
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("SecretsにGEMINI_API_KEYが設定されていません。")
    st.stop()

def fetch_amazon_reviews(url):
    """Amazonの商品ページ/レビューページからテキストを取得する"""
    # ボット弾きを回避するための仮のブラウザ情報（User-Agent）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # レビュー本文のクラス（Amazonの仕様変更により変わる可能性があります）
        review_elements = soup.find_all("span", {"data-hook": "review-body"})
        
        reviews = [elem.get_text(strip=True) for elem in review_elements]
        return "\n\n".join(reviews)
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

def smart_split_text(text, max_chars, suffix=" (続く)"):
    """句読点や改行を基準に文脈を維持して文字数分割する"""
    effective_limit = max_chars - len(suffix)
    
    # 「。」「！」「？」「改行」の直後で文字列を分割
    sentences = re.split(r'(?<=[。！？\n])', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if not sentence.strip():
            continue
            
        # 今のまとまりに次の文を足しても制限以内なら追加
        if len(current_chunk) + len(sentence) <= effective_limit:
            current_chunk += sentence
        else:
            # 制限を超える場合は、今のまとまりを確定させてリストに追加
            if current_chunk:
                chunks.append(current_chunk + suffix)
            
            # 1文自体が制限を超えて長い場合の例外処理（強制分割）
            while len(sentence) > effective_limit:
                chunks.append(sentence[:effective_limit] + suffix)
                sentence = sentence[effective_limit:]
            
            current_chunk = sentence
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

# --- UI部分 ---
st.title("Amazonレビュー統合 & X投稿ジェネレーター")

st.markdown("### 1. レビュー情報の入力")
input_method = st.radio("入力方法を選択してください", ["URLから自動取得", "テキストを直接入力"])

reviews_text = ""

if input_method == "URLから自動取得":
    url = st.text_input("Amazonの商品ページまたはレビューページのURL")
    if st.button("レビューを取得"):
        if url:
            with st.spinner("Amazonからレビューを取得中..."):
                fetched_data = fetch_amazon_reviews(url)
                if "エラーが発生しました" in fetched_data or not fetched_data:
                    st.error("レビューの取得に失敗しました。Amazonのボット対策で弾かれた可能性があるため、直接入力をお試しください。")
                else:
                    st.session_state["fetched_reviews"] = fetched_data
                    st.success("取得成功！")
        else:
            st.warning("URLを入力してください。")
            
    # 取得したレビューを編集可能なテキストエリアに表示
    reviews_text = st.text_area(
        "取得したレビュー（必要に応じて編集してください）", 
        value=st.session_state.get("fetched_reviews", ""), 
        height=200
    )
else:
    reviews_text = st.text_area("レビューテキストを複数貼り付けてください", height=200)

st.markdown("### 2. X（Twitter）投稿の生成")
max_chars_per_post = st.number_input("1投稿あたりの上限文字数（全角）", value=135, min_value=50, max_value=140)

if st.button("X用投稿文を生成する"):
    if not reviews_text.strip():
        st.warning("レビュー情報がありません。")
    else:
        with st.spinner("AIがレビューを要約・統合中..."):
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"""
            以下の複数のAmazon購入者レビュー情報を元に、実際に商品を使用した1人のユーザーが投稿したかのような、自然で説得力のある統合ユーザーレビュー文章を1つ作成してください。
            
            【条件】
            - 良かった点、気になった点（あれば）、総合的なおすすめ度を自然に盛り込む。
            - 押し付けがましくない、個人の感想・レビューの口調（「〜でした」「〜と感じました」など）。
            - 無駄な挨拶や前置きは排除し、レビュー本文のみを出力する。
            - X(Twitter)での連投を前提とするため、簡潔でテンポの良い文章にする。

            【元レビュー情報】
            {reviews_text}
            """
            response = model.generate_content(prompt)
            combined_review = response.text.strip()

        st.subheader("📝 AIが生成した統合レビュー")
        st.write(combined_review)

        st.subheader("📱 X投稿用テキスト（コピーボタン付き）")
        st.info("💡 右上のコピーアイコンをクリックしてテキストをコピーできます。")
        
        chunks = smart_split_text(combined_review, max_chars_per_post)
        
        for i, chunk in enumerate(chunks, 1):
            st.markdown(f"**【投稿 {i}/{len(chunks)}】** ({len(chunk)}文字)")
            # st.codeを使うことで自動的に右上にコピーボタンが表示されます
            st.code(chunk, language="text")
