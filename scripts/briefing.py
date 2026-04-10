import os
import requests
import feedparser
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

# 검색 키워드 설정
SEARCH_TOPICS = {
    "🚇 철도/교통 정책": ["철도 정책", "GTX 개통", "지하철 노선", "신분당선", "철도 안전"],
    "🏢 국내 경제/산업": ["한국 경제", "산업 동향", "수출 무역", "제조업", "반도체 산업"],
    "🤖 AI/테크": ["인공지능 AI", "챗GPT", "AI 로봇", "딥러닝", "AI 반도체"],
    "🌏 글로벌 철도": ["해외 철도", "고속철도", "철도 기술", "자율주행 열차"],
}

PAPER_FEEDS = [
    "https://export.arxiv.org/rss/cs.AI",
    "https://export.arxiv.org/rss/cs.RO",
    "https://export.arxiv.org/rss/eess.SY",
]

def search_naver_news(keyword, display=3):
    """네이버 뉴스 검색 API로 최신 뉴스 가져오기"""
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": keyword,
        "display": display,
        "sort": "date",  # 최신순
    }
    items = []
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        for item in data.get("items", []):
            # HTML 태그 제거
            title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
            desc = item["description"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
            items.append({
                "title": title,
                "link": item["originallink"] or item["link"],
                "summary": desc,
                "pubDate": item.get("pubDate", "")
            })
    except Exception as e:
        print(f"네이버 API 오류 ({keyword}): {e}")
    return items

def fetch_papers(count=4):
    items = []
    for url in PAPER_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")[:400].strip()
                if title:
                    items.append({
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
        except Exception as e:
            print(f"논문 오류 ({url}): {e}")
    return items[:count]

def summarize_section(topic, news_list, is_paper=False):
    today = datetime.now().strftime('%Y년 %m월 %d일')

    if not news_list:
        return "❌ 해당 카테고리 뉴스를 가져오지 못했습니다."

    news_text = "\n\n".join([
        f"[{i+1}]\n제목: {n['title']}\n내용: {n.get('summary', '요약 없음')}\n링크: {n['link']}"
        for i, n in enumerate(news_list)
    ])

    if is_paper:
        prompt = f"""
{today} 기준 최신 논문을 네오트랜스 임직원이 이해하기 쉽게 정리해주세요.

각 논문마다 반드시 아래 형식으로 작성하세요:

📄 제목: [한국어 번역 제목]
- 핵심 내용: (무엇을 연구했는지 2~3문장으로 구체적으로)
- 쉬운 설명: (중학생도 이해할 수 있는 비유로 1문장)
- 철도/업무 활용 가능성: (네오트랜스 관점에서 1문장)
- 원문 링크: [링크]

논문 목록:
{news_text}
"""
    else:
        prompt = f"""
{today} 기준 네오트랜스(신분당선 운영사) 임직원을 위한 {topic} 뉴스 브리핑을 작성해주세요.

각 뉴스마다 반드시 아래 형식으로 빠짐없이 작성하세요:

📌 제목: [뉴스 제목]
- 핵심 내용: (무슨 일이 있었는지 3문장으로 구체적으로 서술)
- 배경: (왜 이 뉴스가 나왔는지 1문장)
- 우리 업계 시사점: (철도/교통/AI 분야에서의 의미 1문장)
- 중요도: [⭐⭐⭐ ~ ⭐⭐⭐⭐⭐]
- 원문 링크: [링크]

뉴스 목록:
{news_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "너는 철도/AI/경제 분야 전문 뉴스 에디터야. 내용을 구체적이고 상세하게 정리해. 링크는 반드시 포함해."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )
    return response.choices[0].message.content

def generate_summary(report):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "너는 뉴스 에디터야."},
            {
                "role": "user",
                "content": f"아래 브리핑을 읽고 오늘 가장 중요한 뉴스 3가지를 한줄씩 요약해:\n\n{report[:3000]}"
            }
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

def send_email(subject, body):
    EMAIL_USER = os.environ.get('EMAIL_USER', '').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS', '').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO', '').strip()

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
    print("✅ 이메일 발송 성공!")

def main():
    today = datetime.now().strftime('%Y년 %m월 %d일')
    print(f"[{today}] 브리핑 생성 시작...")

    report = f"""🌤️ {today} 네오트랜스 아침 브리핑
오늘도 활기찬 하루 되세요! 😊
{'='*60}

"""

    for topic, keywords in SEARCH_TOPICS.items():
        print(f"  {topic} 수집 중...")
        all_news = []
        for keyword in keywords:
            news = search_naver_news(keyword, display=3)
            all_news.extend(news)
        # 중복 제거
        seen = set()
        unique_news = []
        for n in all_news:
            if n['title'] not in seen:
                seen.add(n['title'])
                unique_news.append(n)
        unique_news = unique_news[:6]
        print(f"  → {len(unique_news)}개 수집됨")
        summary = summarize_section(topic, unique_news, is_paper=False)
        report += f"{'='*60}\n{topic}\n{'='*60}\n\n{summary}\n\n"

    print("  📚 논문 수집 중...")
    papers = fetch_papers(count=4)
    print(f"  → {len(papers)}개 수집됨")
    paper_summary = summarize_section("📚 최신 논문", papers, is_paper=True)
    report += f"{'='*60}\n📚 최신 논문 (AI/철도/교통)\n{'='*60}\n\n{paper_summary}\n\n"

    print("  🎯 핵심 요약 생성 중...")
    top3 = generate_summary(report)
    report += f"""{'='*60}
🎯 오늘의 핵심 뉴스 TOP 3
{'='*60}
{top3}

{'='*60}
※ 본 메일은 네이버 뉴스 API 및 논문 데이터를 기반으로 AI가 자동 생성하였습니다.
※ 각 뉴스의 원문 링크를 클릭하여 상세 내용을 확인하시기 바랍니다.
"""

    subject = f"🚅 [네오트랜스] 오늘의 브리핑 ({datetime.now().strftime('%m/%d')})"
    send_email(subject, report)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
