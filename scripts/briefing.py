import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 💡 운영기관 및 노선별로 키워드를 아주 구체적으로 분리했습니다.
TOPICS = {
    "AI/테크": "https://news.google.com/rss/search?q=인공지능+OpenAI+NVIDIA+LLM&hl=ko&gl=KR&ceid=KR:ko",
    
    # 🏢 주요 철도 운영기관 소식
    "철도 운영사 동향": "https://news.google.com/rss/search?q=서울교통공사+OR+코레일+OR+한국철도공사+OR+신분당선+OR+네오트랜스+OR+9호선+OR+공항철도&hl=ko&gl=KR&ceid=KR:ko",
    
    # 🚈 도시철도 및 기술 구분 (경전철, 중전철 등)
    "도시철도 및 경/중전철": "https://news.google.com/rss/search?q=경전철+OR+중전철+OR+우이신설선+OR+신림선+OR+지하철+연장+OR+트램&hl=ko&gl=KR&ceid=KR:ko",
    
    # 🚀 철도 신기술 및 정책
    "철도 신사업/기술": "https://news.google.com/rss/search?q=철도지하화+OR+수소열차+OR+자율주행열차+OR+하이퍼튜브+OR+LTE-R&hl=ko&gl=KR&ceid=KR:ko",
    
    "해외 철도/논문": "https://news.google.com/rss/search?q=High-speed+rail+OR+Maglev+OR+AI+Research+Paper&hl=en&gl=US&ceid=US:en"
}

def get_news_from_rss(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        news_items = []
        for item in root.findall('./channel/item')[:4]: 
            news_items.append({
                "title": item.find('title').text,
                "link": item.find('link').text
            })
        return news_items
    except Exception as e:
        print(f"RSS 수집 오류: {e}")
        return []

def summarize_with_gpt(topic, news_list):
    if not news_list:
        news_text = f"{topic}에 대한 구체적인 뉴스가 수집되지 않았습니다. 현재 알려진 산업 동향을 요약해 주세요."
    else:
        news_text = "\n".join([f"- 제목: {n['title']}\n  링크: {n['link']}" for n in news_list])
    
    prompt = f"""
    당신은 대한민국 철도 산업 전문 분석가입니다. 
    
    [분석 대상 및 규칙]
    1. '철도 운영사 동향': 서울교통공사, 코레일, 신분당선, 9호선, 공항철도 등 주요 운영사의 사건/사고, 경영 소식, 서비스 개선 내용을 집중적으로 분석하세요.
    2. '도시철도 및 경/중전철': 경전철(U-LRT 등)과 중전철 노선의 신설, 연장, 노선별 특이사항을 다루세요.
    3. '철도 신사업/기술': 신기술 도입 현황을 전문적으로 설명하세요.
    4. 반드시 '제목, 요약, 쉬운설명, 관련분야, 중요도, 전체링크' 형식을 지키세요.
    
    데이터:
    {news_text}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", 
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ... (send_email 및 main 함수는 이전과 동일) ...

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()
    today = datetime.now().strftime('%Y년 %m월 %d일')
    subject = f"🚅 [네오트랜스] 운영사 및 노선별 정밀 철도 브리핑 - {today}"
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def main():
    print(f"[{datetime.now()}] 정밀 철도 브리핑 생성 시작...")
    final_report = f"📬 네오트랜스 통합 철도 전문 브리핑\n"
    final_report += f"기준 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    final_report += "==================================================\n\n"
    for topic, url in TOPICS.items():
        print(f"[{topic}] 심층 분석 중...")
        news_list = get_news_from_rss(url)
        summary = summarize_with_gpt(topic, news_list)
        final_report += summary + "\n\n"
    final_report += "==================================================\n"
    final_report += "※ 이 보고서는 주요 철도 운영사 데이터를 기반으로 작성되었습니다."
    send_email(final_report)
    print("성공적으로 발송되었습니다!")

if __name__ == "__main__":
    main()
