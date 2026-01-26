import os
import re
import random
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt
from textblob import TextBlob
from wordcloud import WordCloud
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- Gemini Setup ---
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-pro")
    genai_enabled = True
except Exception:
    genai_enabled = False

# --- Optional Keyword Rules ---
keyword_rules = {
    "Positive": ["strong results", "growth", "profits", "upgrade", "bullish", "record high", "momentum"],
    "Negative": ["layoffs", "scandal", "downturn", "fraud", "lawsuit", "decline", "losses", "bearish"],
    "Neutral": ["announced", "report", "update", "launch", "scheduled"]
}

# --- Helper Functions ---
def random_recent_datetime(within_days=7):
    dt = datetime.now() - timedelta(days=random.randint(0, within_days), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return dt

def simulate_user():
    return random.choice([
        "@finance_guru", "@investornews", "@techinsider", "@corporatebuzz", "@marketwatcher"
    ])

def generate_simulated_linkedin_post(brand, index):
    templates = [
        f"Excited to see how {brand} is driving innovation in financial tech!",
        f"Just attended a webinar hosted by {brand}. Great insights into market strategy.",
        f"Proud to be collaborating with {brand} on future-ready solutions.",
        f"{brand} is reshaping digital finance – impressive leadership!",
        f"Insights from {brand}'s recent panel on ESG and fintech."
    ]
    return f"{random.choice(templates)} [LinkedIn Post #{index+1}] by {simulate_user()}"

# --- Fetch Functions ---
def fetch_duckduckgo_news(brand, limit=5):
    with st.spinner("Fetching DuckDuckGo News..."):
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://duckduckgo.com/html/?q={brand}+news"
        articles = []
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("a", class_="result__a")
            for i, result in enumerate(results[:limit]):
                text = result.get_text(strip=True)
                if text:
                    dt = random_recent_datetime()
                    articles.append((f"{text} (Article #{i+1}) by {simulate_user()}", "DuckDuckGo News", dt))
        except Exception as e:
            print("DuckDuckGo error:", e)
        if not articles:
            for i in range(limit):
                text = f"Simulated DuckDuckGo article about {brand} #{i+1} by {simulate_user()}"
                articles.append((text, "DuckDuckGo News", random_recent_datetime()))
        return articles

def fetch_youtube_titles(brand, limit=5):
    with st.spinner("Fetching YouTube data..."):
        titles = []
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            url = f"https://duckduckgo.com/html/?q=site:youtube.com+{brand}"
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("a", class_="result__a")
            for i, res in enumerate(results[:limit]):
                text = res.get_text(strip=True)
                if text:
                    dt = random_recent_datetime()
                    titles.append((f"{text} [YouTube Clip #{i+1}] by {simulate_user()}", "YouTube", dt))
        except Exception as e:
            print("YouTube error:", e)
        if not titles:
            for i in range(limit):
                text = f"Simulated YouTube video about {brand} #{i+1} by {simulate_user()}"
                titles.append((text, "YouTube", random_recent_datetime()))
        return titles

def fetch_twitter_titles(brand, limit=5):
    with st.spinner("Fetching Twitter posts..."):
        tweets = []
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            url = f"https://duckduckgo.com/html/?q=site:twitter.com+{brand}"
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("a", class_="result__a")
            for i, res in enumerate(results[:limit]):
                text = res.get_text(strip=True)
                if text:
                    dt = random_recent_datetime()
                    tweets.append((f"{text} (Tweet #{i+1}) by {simulate_user()}", "Twitter", dt))
        except Exception as e:
            print("Twitter error:", e)
        if not tweets:
            for i in range(limit):
                text = f"Simulated tweet about {brand} #{i+1} by {simulate_user()}"
                tweets.append((text, "Twitter", random_recent_datetime()))
        return tweets

def fetch_glassdoor_reviews(brand, limit=5):
    with st.spinner("Fetching Glassdoor reviews..."):
        reviews = []
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            url = f"https://duckduckgo.com/html/?q=site:glassdoor.com+{brand}+reviews"
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("a", class_="result__a")
            for i, res in enumerate(results[:limit]):
                text = res.get_text(strip=True)
                if text:
                    dt = random_recent_datetime()
                    reviews.append((f"{text} [Glassdoor Review #{i+1}] by {simulate_user()}", "Glassdoor", dt))
        except Exception as e:
            print("Glassdoor error:", e)
        if not reviews:
            for i in range(limit):
                text = f"Simulated Glassdoor review about {brand} #{i+1} by {simulate_user()}"
                reviews.append((text, "Glassdoor", random_recent_datetime()))
        return reviews

def fetch_linkedin_titles(brand, limit=5):
    with st.spinner("Simulating LinkedIn posts..."):
        return [(generate_simulated_linkedin_post(brand, i), "LinkedIn", random_recent_datetime()) for i in range(limit)]

# --- Streamlit UI ---
st.set_page_config(page_title="Corporate Brand Sentiment Analyzer", layout="centered")
st.title("\U0001F310 Corporate Brand Sentiment Analyzer")

brand_input = st.text_input("Enter a company or brand name", "Broadridge")

if st.button("Analyze"):
    brand = brand_input

    duck = fetch_duckduckgo_news(brand)
    youtube = fetch_youtube_titles(brand)
    twitter = fetch_twitter_titles(brand)
    linkedin = fetch_linkedin_titles(brand)
    glassdoor = fetch_glassdoor_reviews(brand)

    all_data = duck + youtube + twitter + linkedin + glassdoor
    if not all_data:
        st.warning("\u274C No data found.")
        st.stop()

    df = pd.DataFrame(all_data, columns=["Text", "Source", "Date"])
    use_gemini = st.checkbox("Use Gemini AI (for first 10 rows)", value=False)

    sentiment_list = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        text = row["Text"]
        clean_text = re.sub(r"[^\w\s]", "", text.lower())

        if use_gemini and genai_enabled and i < 10:
            try:
                prompt = f"Classify the sentiment of this text as Positive, Negative, or Neutral:\n\n{text}"
                response = model.generate_content(prompt)
                label = response.text.strip().split("\n")[0]
                if any(x in label.lower() for x in ["positive", "neutral", "negative"]):
                    sentiment_list.append(label.title())
                    progress.progress((i + 1) / len(df))
                    continue
            except Exception as e:
                print("Gemini error:", e)

        # Fallback to keyword rules and TextBlob
        for label, keywords in keyword_rules.items():
            if any(kw in clean_text for kw in keywords):
                sentiment_list.append(label)
                break
        else:
            polarity = TextBlob(clean_text).sentiment.polarity
            if polarity > 0.1:
                sentiment_list.append("Positive")
            elif polarity < -0.1:
                sentiment_list.append("Negative")
            else:
                sentiment_list.append("Neutral")

        progress.progress((i + 1) / len(df))

    df["Sentiment"] = sentiment_list

    st.subheader("\U0001F4C8 Sentiment Trend Over Time")
    trend = df.groupby(["Date", "Sentiment"]).size().reset_index(name="Count")
    st.altair_chart(
        alt.Chart(trend).mark_line(point=True).encode(
            x="Date:T", y="Count:Q", color="Sentiment:N"
        ), use_container_width=True
    )

    st.subheader("\U0001F4CA Sentiment Distribution")
    st.altair_chart(
        alt.Chart(df["Sentiment"].value_counts().reset_index()).mark_bar().encode(
            x="index:N", y="Sentiment:Q", color="index:N"
        ).properties(title="Overall Sentiment")
    )

    st.subheader("\U0001F4E1 Source Contribution")
    source_counts = df['Source'].value_counts()
    fig, ax = plt.subplots()
    ax.pie(source_counts, labels=source_counts.index, autopct='%1.1f%%', startangle=90)
    ax.axis("equal")
    st.pyplot(fig, use_container_width=True)

    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(" ".join(df["Text"]))
    st.image(wordcloud.to_array(), use_container_width=True)

    st.subheader("\U0001F4CB Sentiment Table")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("\u2B07\uFE0F Download CSV Report", csv, "sentiment_report.csv", "text/csv")

    st.subheader("\U0001F9FE What Each Sentiment Means")
    st.markdown("""
| Sentiment | Description |
|-----------|-------------|
| ✅ Positive | Praise, support, or trust |
| ⚪ Neutral   | Mixed, unclear, or factual |
| ❌ Negative | Complaints, criticism, or risk |
""")
