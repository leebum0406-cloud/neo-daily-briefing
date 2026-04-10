import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
import xml.etree.ElementTree as ET

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- 1. 뉴스 수집 함수들 ---

def get_redaily_news():
    """철도경제 최신 뉴스"""
    url = "https://www.redaily.co.kr/news/articleList.html?view_type=sm"
    headers = {'User-Agent': 'Mozilla/5.0'}
    items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('.list-titles a')[:3]:
            items.append({"title": a.get_text(strip=True), "link": "https://www.redaily.co.kr" + a['href']})
    except: pass
    return items

def get_rss_news(url, limit=3):
    """AI타임스, 전자신문 RSS"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(res.content)
        for item in root.findall('./channel/item')[:limit]:
            items.append({"title": item.find('title').text, "link": item.find('link').text})
    except: pass
    return items

# --- 2. GPT 요약 엔진 (프롬프트 고도화) ---

def summarize_with_gpt(topic, news_list):
    if not news_list:
        return f"### {topic}\n현재 수집된 기사가 없습니다. 산업 동향을 분석 중입니다.\n"

    news_text = "\n".join([f"- {n['title']} (링크: {n['link']})" for n in news_list])
    
    # 스크린샷 형식을 그대로 강제하는 프롬프트
    prompt = f"""
    당신은 '{topic}' 분야 전문 에디터입니다. 아래 뉴스를 바탕으로 스크린샷과 동일한 형식의 리포트를 작성하세요.
    
    [반드시 지켜야 할 출력 형식]
    제목: [가장 중요한 기사를 선정하여 강렬한 제목 작성]
    요약: [기사 내용을 3~4문장으로 핵심 정리]
    쉬운설명: [초등학생도 이해할 수 있도록 일상적인 비유를 들어 설명]
    관련분야: [태그 형태로 작성, 예: AI 에이전트, 철도 신사업]
    중요도: [1~10점 사이] 점
    전체링크: [해당 기사의 실제 링크]
    
    데이터:
    {news_text}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "너는 전문 뉴스레터 큐레이터야. 마크다운 형식을 아주 잘 지켜."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- 3. 메인 실행 로직 ---

def main():
    print("브리핑 생성 중...")
    
    # 상단 팁 및 헤더
    today_str = datetime.now().strftime('%Y년 %m월 %d일')
    header = f"""🌤️ 오늘 아침 기상 팁: 2026년 봄 기운이 완연하지만 일교차가 큽니다. 가벼운 외투를 챙기세요! 😊

---

🤖 **네오트랜스 AI & 산업 브리핑** – {today_str}

# 📌 오늘의 한 줄 요약
- 철도 전문지 및 테크 매체의 핵심 이슈를 엄선했습니다.
- AI 혁신, 국내외 철도 정책, 신기술 트렌드를 분석합니다.

---
"""

    # 섹션별 수집 및 요약
    sources = [
        ("🚀 철도 산업 분석 (철도경제)", get_redaily_news()),
        ("🤖 AI/테크 트렌드 (AI타임스)", get_rss_news("http://www.aitimes.com/rss/allNews.xml")),
        ("🏭 국내 산업 동향 (전자신문)", get_rss_news("https://www.etnews.com/etnews/rss/all.xml"))
    ]
    
    body = ""
    for topic, news in sources:
        body += f"## {topic}\n"
        body += summarize_with_gpt(topic, news) + "\n\n---\n\n"

    footer = """# 마무리
오늘도 활기찬 하루 되시길 바랍니다! ☕
※ 본 브리핑은 전문 매체 데이터를 기반으로 AI가 자동 생성하였습니다.
"""

    final_report = header + body + footer
    send_email(final_report)

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"🚅 [네오트랜스] 오늘의 전문지 통합 브리핑 - {datetime.now().strftime('%m/%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
    print("발송 완료!")

if __name__ == "__main__":
    main()
