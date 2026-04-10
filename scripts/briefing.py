import feedparser
import requests
import os
from datetime import datetime

# RSS 피드 목록
RSS_FEEDS = {
    "AI/테크": [
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://www.technologyreview.com/feed/",
    ],
    "국내 산업": [
        "https://www.etnews.com/rss/",
        "https://www.zdnet.co.kr/rss/news.xml",
    ],
    "철도": [
        "https://www.kric.or.kr/rss/rss.do",
    ],
    "논문": [
        "https://export.arxiv.org/rss/cs.AI",
        "https://export.arxiv.org/rss/cs.RO",
    ]
}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
EMAIL_TO = os.environ.get("EMAIL_TO")

def fetch_news():
    all_news = {}
    for category, feeds in RSS_FEEDS.items():
        items = []
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    items.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", "")[:300],
                        "link": entry.get("link", "")
                    })
            except:
                pass
        all_news[category] = items[:5]
    return all_news

def summarize_with_gpt(news_data):
    content = ""
    for category, items in news_data.items():
        content += f"\n## {category}\n"
        for item in items:
            content += f"- {item['title']}: {item['summary']}\n"

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{
                "role": "user",
                "content": f"""아래 뉴스를 한국어로 브리핑해주세요.
각 카테고리별로 핵심 내용을 2-3줄로 요약하고,
오늘의 한줄 요약도 작성해주세요.

{content}"""
            }],
            "max_tokens": 1500
        }
    )
    return response.json()["choices"][0]["message"]["content"]

def send_email(subject, body):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def main():
    today = datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today}] 브리핑 시작...")

    news = fetch_news()
    summary = summarize_with_gpt(news)

    subject = f"🚇 네오트랜스 AI 브리핑 - {today}"
    body = f"""
🤖 네오트랜스 AI 브리핑 - {today}
{'='*50}

{summary}

{'='*50}
※ 본 브리핑은 AI가 자동으로 생성한 내용입니다.
    """

    send_email(subject, body)
    print("이메일 발송 완료!")

if __name__ == "__main__":
    main()
