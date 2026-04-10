import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 💡 키워드를 더 구체적이고 다양하게 수정했습니다.
TOPICS = {
    "AI/테크": "https://news.google.com/rss/search?q=인공지능+LLM+NVIDIA+OpenAI&hl=ko&gl=KR&ceid=KR:ko",
    "국내 산업": "https://news.google.com/rss/search?q=반도체+HBM+K-배터리+현대차+실적&hl=ko&gl=KR&ceid=KR:ko",
    "철도/교통": "https://news.google.com/rss/search?q=GTX+철도+지하철+현대로템+국가철도공단&hl=ko&gl=KR&ceid=KR:ko",
    "해외 논문": "https://news.google.com/rss/search?q=AI+Research+Paper+Arxiv&hl=ko&gl=KR&ceid=KR:ko"
}

def get_news_from_rss(url):
    try:
        # User-Agent를 설정하여 차단을 방지합니다.
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        root = ET.fromstring(response.content)
        news_items = []
        # 최신 뉴스 3개로 늘림
        for item in root.findall('./channel/item')[:3]: 
            news_items.append({
                "title": item.find('title').text,
                "link": item.find('link').text
            })
        return news_items
    except Exception as e:
        print(f"RSS 수집 오류: {e}")
        return []

def summarize_with_gpt(topic, news_list):
    # 기사가 없을 경우를 위해 프롬프트를 강화
    if not news_list:
        news_text = "최근 이슈가 수집되지 않았습니다."
    else:
        news_text = "\n".join([f"- 제목: {n['title']}\n  링크: {n['link']}" for n in news_list])
    
    prompt = f"""
    당신은 '{topic}' 분야 전문 뉴스레터 에디터입니다. 
    수집된 뉴스 정보를 바탕으로 독자들에게 도움이 될 브리핑을 작성하세요.
    
    [작성 규칙]
    1. 반드시 '제목, 요약, 쉬운설명, 관련분야, 중요도, 전체링크' 형식을 지키세요.
    2. 기사가 없다면 해당 분야의 최근 일반적인 트렌드나 기술 동향을 바탕으로 '오늘의 인사이트'를 작성하세요. (절대 '내용 없음'으로 끝내지 마세요)
    3. 말투는 친절하고 전문적인 톤으로 작성하세요.
    
    뉴스 정보:
    {news_text}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", 
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()

    today = datetime.now().strftime('%Y년 %m월 %d일')
    subject = f"🚀 [네오트랜스] 오늘의 핵심 AI & 산업 브리핑 - {today}"
    
    # 더 이쁘게 보이기 위해 구분선 추가
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def main():
    print(f"[{datetime.now()}] 브리핑 생성 시작...")
    final_report = f"🤖 네오트랜스 AI & 산업 데일리 브리핑\n"
    final_report += f"발송일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    final_report += "==================================================\n\n"
    
    for topic, url in TOPICS.items():
        print(f"{topic} 처리 중...")
        news_list = get_news_from_rss(url)
        summary = summarize_with_gpt(topic, news_list)
        final_report += summary + "\n\n"
        
    final_report += "==================================================\n"
    final_report += "※ 본 메일은 AI가 실시간 데이터를 분석하여 자동 생성하였습니다."
    
    send_email(final_report)
    print("브리핑 발송 완료!")

if __name__ == "__main__":
    main()
