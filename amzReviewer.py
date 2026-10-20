import google.generativeai as genai
import math
import streamlit as st

# Gemini APIキーの設定
genai.configure(api_key="YOUR_GEMINI_API_KEY")

st.title("Amazonレビュー統合 & X投稿作成ツール")

# 入力フォーム
reviews_input = st.text_area(
    "Amazonのレビューテキストを複数貼り付けてください", height=200
)
max_chars_per_post = st.number_input(
    "1投稿あたりの上限文字数", value=130, min_value=50, max_value=280
)

if st.button("X用投稿文を生成する"):
    if not reviews_input.strip():
        st.warning("レビュー本文を入力してください。")
    else:
        with st.spinner("AIがレビューを要約・統合中..."):
            # 1. Geminiで1つのユーザーレビューに統合
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"""
            以下の複数のAmazon購入者レビュー情報を元に、実際に商品を使用した1人のユーザーが投稿したかのような、自然で説得力のある統合ユーザーレビュー文章を1つ作成してください。
            
            【条件】
            - 良かった点、気になった点（あれば）、総合的なおすすめ度を自然に盛り込むこと。
            - 押し付けがましくない、個人の感想・レビューの口調（「〜でした」「〜と感じました」など）にすること。
            - 無駄な挨拶や前置きは排除し、レビュー本文のみを出力すること。

            【元レビュー情報】
            {reviews_input}
            """

            response = model.generate_content(prompt)
            combined_review = response.text.strip()

        st.subheader("📝 統合されたレビュー文章")
        st.write(combined_review)

        # 2. X（Twitter）用に文字数分割処理
        st.subheader("📱 X（Twitter）投稿用テキスト")

        # 「 (続く)」の文字数を考慮した実質上限
        suffix = " (続く)"
        effective_limit = max_chars_per_post - len(suffix)

        # 簡易分割処理（句読点などを意識して分割する場合はロジック調整可能）
        chunks = []
        text = combined_review
        while len(text) > max_chars_per_post:
            # 分割位置の切り出し
            chunk = text[:effective_limit] + suffix
            chunks.append(chunk)
            text = text[effective_limit:]
        if text:
            chunks.append(text)

        # 結果の表示
        for i, chunk in enumerate(chunks, 1):
            st.markdown(f"**【投稿 {i}/{len(chunks)}】** ({len(chunk)}文字)")
            st.code(chunk, language="text")