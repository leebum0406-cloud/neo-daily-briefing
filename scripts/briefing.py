import os
import requests
import feedparser
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# RSS 피드 목록
RSS_FEEDS = {
    "🚇 철도/교통 정책": [
        "https://www.railwayjournal.com/feed/",
        "https://www.railjournal.com/feed/",
        "http://www.kric.or.kr/rss/rss.do",
        "https://www.yna.co.kr/RSS/society.xml",
        "https://rss.donga.com/society.xml",
    ],
    "🏢 국내 산업/경제": [
        "https://www.hankyung.com/feed/economy",
        "https://www.etnews.com/rss/",
        "https://rss.mk.co.kr/rss/30000001.xml",
        "https://www.sedaily.com/RSS/sed_economy.xml",
        "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml",
    ],
    "🤖 AI/테크": [
        "https://techcrunch.com/feed/",
        "https://www.technologyreview.com/feed/",
        "https://venturebeat.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
    ],
    "🌏 글로벌 철도/교통": [
        "https://www.globalrailwayreview.com/feed/",
        "https://www.railwaygazette.com/feed/",
        "https://www.intelligent-transport.com/feed/",
    ],
}

# 논문 RSS
PAPER_FEEDS = [
    "https://export.arxiv.org/rss/cs.AI",
    "https://export.arxiv.org/rss/cs.RO",
    "https://export.arxiv.org/rss/eess.SY",  # 시스템/제어 (철도 관련)
]

def fetch_rss(feeds, count=5):
    items = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")[:300].strip()
                if title and link:
                    items.append({
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
        except Exception as e:
            print(f"RSS 수집 오류 ({url}): {e}")
    return items[:count]

def fetch_papers(count=4):
    items = []
    for url in PAPER_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")[:300].strip()
                if title:
                    items.append({
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
        except Exception as e:
            print(f"논문 수집 오류 ({url}): {e}")
    return items[:count]

def summarize_section(topic, news_list, is_paper=False):
    today = datetime.now().strftime('%Y년 %m월 %d일')
    
    if not news_list:
        return f"❌ {topic} 관련 최신 소식을 가져오지 못했습니다."
    
    news_text = "\n".join([
        f"[{i+1}] 제목: {n['title']}\n    요약: {n.get('summary','')}\n    링크: {n['link']}"
        for i, n in enumerate(news_list)
    ])
    
    if is_paper:
        prompt = f"""
{today} 기준 최신 논문들을 네오트랜스 임직원이 이해하기 쉽게 정리해주세요.

각 논문마다:
📄 [논문 제목 (한국어 번역)]
- 핵심 내용: (2문장)
- 쉬운 설명: (비유를 들어 1문장)
- 철도/업무 활용: (1문장)
- 링크: (링크)

논문 목록:
{news_text}
"""
    else:
        prompt = f"""
{today} 네오트랜스(신분당선 운영사) 임직원을 위한 {topic} 브리핑을 작성해주세요.

각 뉴스마다 아래 형식으로 작성:
📌 [제목 (한국어로)]
- 핵심 내용: (3문장으로 구체적으로)
- 쉬운 설명: (비유를 들어 1문장)
- 우리 회사/업계 시사점: (1문장)
- 중요도: [⭐~⭐⭐⭐⭐⭐]
- 링크: (링크)

뉴스 목록:
{news_text}
"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "너는 철도/AI/산업 분야 전문 에디터야. 구체적이고 실용적으로 정리해."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500
    )
    return response.choices[0].message.content

def generate_one_line_summary(full_report):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "너는 뉴스 에디터야."},
            {"role": "user", "content": f"아래 브리핑을 읽고 오늘의 핵심 한줄 요약을 작성해:\n{full_report[:2000]}"}
        ],
        max_tokens=100
    )
    return response.choices[0].message.content

def send_email(subject, body):
    EMAIL_USER = os.environ.get('EMAIL_USER', '').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS', '').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO', '').strip()

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
    print("이메일 발송 성공!")

def main():
    today = datetime.now().strftime('%Y년 %m월 %d일')
    print(f"[{today}] 브리핑 생성 시작...")

    report = f"""🌤️ {today} 네오트랜스 아침 브리핑
오늘도 활기찬 하루 되세요! 😊
{'='*50}

"""
    section_reports = []

    for topic, feeds in RSS_FEEDS.items():
        print(f"{topic} 뉴스 수집 중...")
        news = fetch_rss(feeds, count=5)
        summary = summarize_section(topic, news, is_paper=False)
        section = f"## {topic}\n{summary}\n\n{'─'*40}\n\n"
        report += section
        section_reports.append(summary)

    # 논문 섹션
    print("논문 수집 중...")
    papers = fetch_papers(count=4)
    paper_summary = summarize_section("📚 최신 논문", papers, is_paper=True)
    report += f"## 📚 최신 논문 (AI/철도/교통)\n{paper_summary}\n\n{'─'*40}\n\n"

    # 오늘의 한줄 요약
    one_line = generate_one_line_summary(report)
    report += f"{'='*50}\n🎯 오늘의 한줄 요약\n{one_line}\n{'='*50}\n\n"
    report += "※ 본 메일은 RSS 및 논문 데이터를 기반으로 AI가 자동 생성하였습니다."

    subject = f"🚅 [네오트랜스] 오늘의 브리핑 ({datetime.now().strftime('%m/%d')})"
    send_email(subject, report)
    print("완료!")

if __name__ == "__main__":
    main()
