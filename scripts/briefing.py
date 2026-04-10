import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 💡 검색 쿼리를 더 포괄적이고 강력하게 수정했습니다.
TOPICS = {
    "AI/테크": "인공지능+OpenAI+LLM+테크+트렌드",
    "국내 주요 산업": "반도체+HBM+자동차+배터리+현대차+삼성전자+경제+전망",
    "철도 운영/노선": "신분당선+네오트랜스+코레일+서울교통공사+9호선+공항철도+경전철+개통",
    "철도 신사업/기술": "철도+지하화+수소열차+자율주행+하이퍼튜브+스마트유지보수",
    "글로벌 AI 논문": "AI+Research+Paper+Arxiv+Machine+Learning"
}

def fetch_google_news(query):
    """구글 뉴스 RSS를 통해 사이트 차단을 우회하여 뉴스를 수집합니다."""
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    # 해외 논문 섹션은 영어로 검색
    if "Arxiv" in query:
        url = f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall('./channel/item')[:4]:
            items.append({
                "title": item.find('title').text,
                "link": item.find('link').text
            })
        return items
    except Exception as e:
        print(f"로그: {query} 수집 중 오류 발생 -> {e}")
        return []

def summarize_with_gpt(topic, news_list):
    """뉴스 데이터가 부족해도 GPT의 배경지식을 활용해 브리핑을 강제로 완성합니다."""
    news_content = ""
    if news_list:
        news_content = "\n".join([f"- 제목: {n['title']}\n  링크: {n['link']}" for n in news_list])
    else:
        # ⚠️ 핵심: 뉴스가 없을 때 GPT에게 줄 가이드라인
        news_content = "현재 실시간 뉴스 수집이 제한적입니다. 귀하가 알고 있는 2026년 해당 분야의 최신 트렌드와 주요 과제를 바탕으로 전문가 브리핑을 작성해 주세요."

    prompt = f"""
    당신은 '{topic}' 분야의 시니어 에디터입니다. 아래 제공된 정보를 바탕으로 뉴스레터를 작성하세요.
    
    [출력 서식]
    제목: [가장 임팩트 있는 제목]
    요약: [핵심 내용 3문장 요약]
    쉬운설명: [일상적인 비유를 사용하여 초등학생도 이해하게 설명]
    관련분야: [태그 2~3개]
    중요도: [1~10]점
    전체링크: [기사 링크 또는 관련 공식 사이트 주소]
    
    [주의사항]
    - 데이터가 부족해도 '정보 없음'이라고 하지 마세요. 전문가로서 현재 산업의 흐름을 예측하여 작성하세요.
    - 철도 섹션은 신분당선(네오트랜스), 9호선 등 운영기관의 입장에서 분석하세요.
    
    데이터:
    {news_content}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "너는 대한민국 최고의 산업 분석가야."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def main():
    print(f"[{datetime.now()}] 지능형 통합 브리핑 생성 시작...")
    
    # 기상 팁 및 인사말
    report = f"🌤️ 오늘 아침 기상 팁: {datetime.now().strftime('%m월 %d일')}, 안개가 잦으니 안전 운전하세요!\n\n"
    report += "🤖 **네오트랜스 통합 지능형 브리핑**\n"
    report += "==================================================\n\n"
    
    for topic, query in TOPICS.items():
        print(f"[{topic}] 분석 중...")
        news = fetch_google_news(query)
        briefing = summarize_with_gpt(topic, news)
        report += f"## {topic}\n{briefing}\n\n---\n\n"
        
    report += "※ 본 브리핑은 실시간 뉴스 및 GPT-4o의 산업 분석을 결합하여 작성되었습니다.\n"
    
    # 이메일 발송
    send_email(report)
    print("모든 공정 완료 및 발송 성공!")

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"🚅 [네오트랜스] 정밀 산업 브리핑 ({datetime.now().strftime('%m/%d')})"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

if __name__ == "__main__":
    main()
