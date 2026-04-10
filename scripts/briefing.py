import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

# 1. 설정
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 관심 키워드별 Google News RSS 주소
TOPICS = {
    "AI/테크": "https://news.google.com/rss/search?q=인공지능+IT&hl=ko&gl=KR&ceid=KR:ko",
    "국내 산업": "https://news.google.com/rss/search?q=국내+산업+경제&hl=ko&gl=KR&ceid=KR:ko",
    "철도": "https://news.google.com/rss/search?q=철도+GTX+지하철&hl=ko&gl=KR&ceid=KR:ko",
    "논문": "https://news.google.com/rss/search?q=AI+Research+Paper&hl=ko&gl=KR&ceid=KR:ko"
}

def get_news_from_rss(url):
    """RSS 피드에서 최신 뉴스 2건만 가져옵니다."""
    try:
        response = requests.get(url)
        root = ET.fromstring(response.content)
        news_items = []
        for item in root.findall('./channel/item')[:2]: # 주제당 2개씩
            news_items.append({
                "title": item.find('title').text,
                "link": item.find('link').text
            })
        return news_items
    except:
        return []

def summarize_with_gpt(topic, news_list):
    """주제별 뉴스 목록을 GENEXIS 스타일로 변환합니다."""
    if not news_list:
        return f"### {topic}\n- 현재 새로운 소식이 없습니다.\n"

    news_text = "\n".join([f"- 제목: {n['title']}\n  링크: {n['link']}" for n in news_list])
    
    prompt = f"""
    당신은 전문 뉴스 분석가입니다. 아래 제공된 '{topic}' 관련 뉴스들을 분석해서 뉴스레터 형식을 작성하세요.
    
    [형식]
    ### {topic}
    제목: [가장 중요한 뉴스 하나를 골라 제목 작성]
    요약: [내용을 2~3문장으로 핵심 요약]
    쉬운설명: [초등학생도 이해할 수 있게 아주 쉽게 비유해서 설명]
    관련분야: [관련 태그 작성]
    중요도: [0~10점 사이] 점
    전체링크: [해당 뉴스 링크]
    
    ---
    뉴스 리스트:
    {news_text}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", # 더 똑똑한 결과를 위해 4o 사용 권장
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def send_email(body):
    """최종 생성된 내용을 이메일로 발송합니다."""
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()

    today = datetime.now().strftime('%Y년 %m월 %d일')
    subject = f"🤖 네오트랜스 AI 브리핑 - {today}"
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def main():
    print(f"[{datetime.now()}] 브리핑 생성 시작...")
    final_report = f"📬 네오트랜스 AI 브리핑 - {datetime.now().strftime('%Y-%m-%d')}\n"
    final_report += "==========================================\n\n"
    
    for topic, url in TOPICS.items():
        print(f"{topic} 뉴스 수집 중...")
        news_list = get_news_from_rss(url)
        summary = summarize_with_gpt(topic, news_list)
        final_report += summary + "\n\n"
        
    final_report += "==========================================\n"
    final_report += "※ 본 브리핑은 AI가 실시간 뉴스를 수집하여 요약한 내용입니다."
    
    send_email(final_report)
    print("브리핑 발송 완료!")

if __name__ == "__main__":
    main()
