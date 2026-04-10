import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
import xml.etree.ElementTree as ET

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_redaily_news():
    """철도경제(redaily.co.kr) 최신 뉴스 크롤링"""
    url = "https://www.redaily.co.kr/news/articleList.html?view_type=sm"
    headers = {'User-Agent': 'Mozilla/5.0'}
    items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('.list-titles a')[:5]:
            items.append({"title": a.get_text(strip=True), "link": "https://www.redaily.co.kr" + a['href']})
    except: pass
    return items

def get_rss_news(url, limit=5):
    """RSS 피드를 제공하는 전문지(AI타임스, 전자신문 등)용 함수"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(res.content)
        for item in root.findall('./channel/item')[:limit]:
            items.append({
                "title": item.find('title').text,
                "link": item.find('link').text
            })
    except: pass
    return items

def summarize_with_gpt(topic, news_list):
    """전문가 톤으로 요약하는 GPT 엔진"""
    if not news_list:
        news_text = "현재 수집된 기사가 없습니다. 해당 분야의 최신 트렌드를 바탕으로 인사이트를 작성하세요."
    else:
        news_text = "\n".join([f"- {n['title']} ({n['link']})" for n in news_list])
    
    prompt = f"""
    당신은 '{topic}' 분야의 수석 애널리스트입니다. 
    제공된 전문지의 정보를 바탕으로 '네오트랜스' 임직원들이 읽을 고품격 뉴스레터를 작성하세요.
    
    [형식]
    제목, 요약, 쉬운설명, 관련분야, 중요도, 전체링크
    
    특히 '철도' 섹션은 신분당선, 코레일, 서교공 소식 및 신기술 위주로 작성하고, 
    'AI'와 '산업' 섹션은 실무에 적용 가능한 기술 트렌드 위주로 분석하세요.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "너는 철도와 IT에 정통한 전문 에디터야."},
                  {"role": "user", "content": f"{news_text}\n\n위 데이터를 기반으로 작성해줘."}]
    )
    return response.choices[0].message.content

def main():
    print(f"[{datetime.now()}] 전문지 통합 브리핑 생성 시작...")
    
    # 1. 분야별 뉴스 수집 (각 전문지 RSS 및 크롤링 주소)
    sources = {
        "🚀 철도 전문 분석 (철도경제)": get_redaily_news(),
        "🤖 AI/테크 심층 분석 (AI타임스)": get_rss_news("http://www.aitimes.com/rss/allNews.xml"),
        "🏭 국내 산업/IT 동향 (전자신문)": get_rss_news("https://www.etnews.com/etnews/rss/all.xml"),
        "🔬 글로벌 테크/논문": get_rss_news("https://news.google.com/rss/search?q=AI+Research+Paper&hl=en&gl=US&ceid=US:en")
    }
    
    final_report = f"📬 네오트랜스 전문지 통합 브리핑 ({datetime.now().strftime('%Y-%m-%d')})\n"
    final_report += "==================================================\n\n"
    
    for topic, news_list in sources.items():
        print(f"{topic} 분석 중...")
        summary = summarize_with_gpt(topic, news_list)
        final_report += f"## {topic}\n{summary}\n\n---\n\n"
        
    final_report += "※ 본 보고서는 철도경제, AI타임스, 전자신문 등 전문 매체 데이터를 기반으로 작성되었습니다."
    
    # 이메일 발송
    send_email(final_report)

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO').strip()
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"🚅 [네오트랜스] 전문지 통합 산업 브리핑 - {datetime.now().strftime('%m월 %d일')}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
    print("브리핑 발송 완료!")

if __name__ == "__main__":
    main()
