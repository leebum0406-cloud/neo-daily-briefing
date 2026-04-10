import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_naver_news(keyword):
    """네이버에서 관련 키워드로 검색된 최근 뉴스 5개를 가져옵니다."""
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        articles = soup.select('a.news_tit')
        for a in articles[:5]:
            items.append({"title": a.get_text(strip=True), "link": a['href']})
    except: pass
    return items

def summarize_with_gpt(topic, news_list):
    """뉴스 목록을 바탕으로 아침 보고서 형식으로 요약합니다."""
    today = datetime.now().strftime('%Y-%m-%d')
    news_text = "\n".join([f"- {n['title']} (링크: {n['link']})" for n in news_list]) if news_list else "최신 소식이 없습니다."
    
    prompt = f"""
    당신은 네오트랜스(신분당선) 임직원을 위한 아침 브리핑 에디터입니다.
    {today} 아침에 읽을 수 있도록 어제의 주요 소식을 정리하세요.

    [필수 형식]
    - 제목: [핵심 이슈 선정]
    - 요약: [내용 3문장 요약]
    - 쉬운설명: [초등학생도 이해할 수 있는 비유]
    - 관련분야: [태그]
    - 중요도: [점수]
    - 전체링크: [뉴스 링크]

    데이터:
    {news_text}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "너는 전문적인 철도/IT 에디터야."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def main():
    print("아침 7시 정기 브리핑 생성 중...")
    
    sections = {
        "🚀 철도 정책 및 노선 (GTX, 철도지하화)": "철도+지하화+GTX+개통",
        "🏢 철도 운영사 소식 (신분당선, 코레일 등)": "신분당선+네오트랜스+서울교통공사+코레일",
        "🤖 AI 및 산업 신기술": "AI+인공지능+반도체+신기술"
    }
    
    # 헤더 구성
    report = f"🌤️ {datetime.now().strftime('%Y년 %m월 %d일')} 아침 브리핑\n"
    report += "밤사이 들어온 주요 소식을 정리해 드립니다. 오늘도 활기찬 하루 되세요! 😊\n"
    report += "==================================================\n\n"
    
    for topic, keyword in sections.items():
        news = get_naver_news(keyword)
        summary = summarize_with_gpt(topic, news)
        report += f"## {topic}\n{summary}\n\n---\n\n"
        
    report += "※ 본 메일은 전문 매체 데이터를 기반으로 AI가 자동 생성하였습니다."
    
    send_email(report)

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"🚅 [네오트랜스] 오늘의 산업 및 철도 브리핑 ({datetime.now().strftime('%m/%d')})"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
    print("브리핑이 성공적으로 발송되었습니다.")

if __name__ == "__main__":
    main()
