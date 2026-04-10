import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_naver_news(keyword, count=5):
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        articles = soup.select('a.news_tit')
        for a in articles[:count]:
            items.append({
                "title": a.get_text(strip=True),
                "link": a['href']
            })
    except Exception as e:
        print(f"뉴스 수집 오류: {e}")
    return items

def get_arxiv_papers(query="railway OR railroad OR AI safety", count=3):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&sortBy=submittedDate&sortOrder=descending&max_results={count}"
    items = []
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'xml')
        entries = soup.find_all('entry')
        for entry in entries:
            title = entry.find('title').get_text(strip=True)
            link = entry.find('id').get_text(strip=True)
            summary = entry.find('summary').get_text(strip=True)[:200]
            items.append({
                "title": title,
                "link": link,
                "summary": summary
            })
    except Exception as e:
        print(f"논문 수집 오류: {e}")
    return items

def summarize_with_gpt(topic, news_list, is_paper=False):
    today = datetime.now().strftime('%Y-%m-%d')
    
    if is_paper:
        news_text = "\n".join([
            f"- 제목: {n['title']}\n  요약: {n['summary']}\n  링크: {n['link']}"
            for n in news_list
        ]) if news_list else "최신 논문이 없습니다."
        prompt = f"""
당신은 네오트랜스(신분당선) 임직원을 위한 아침 브리핑 에디터입니다.
{today} 기준 최신 논문을 쉽게 정리해주세요.

각 논문마다 아래 형식으로 작성:
📄 제목: [논문 제목]
- 핵심 내용: [2문장 요약]
- 쉬운 설명: [초등학생도 이해할 수 있는 비유로 1문장]
- 활용 가능성: [철도/AI 분야 적용 가능성 1문장]
- 링크: [논문 링크]

논문 데이터:
{news_text}
"""
    else:
        news_text = "\n".join([
            f"- {n['title']} (링크: {n['link']})"
            for n in news_list
        ]) if news_list else "최신 소식이 없습니다."
        prompt = f"""
당신은 네오트랜스(신분당선) 임직원을 위한 아침 브리핑 에디터입니다.
{today} 아침에 읽을 수 있도록 주요 소식을 정리하세요.

각 뉴스마다 아래 형식으로 작성:
📌 제목: [핵심 이슈]
- 요약: [3문장 요약]
- 쉬운 설명: [초등학생도 이해할 수 있는 비유로 1문장]
- 시사점: [네오트랜스/철도 업계 관점에서 1문장]
- 중요도: [⭐~⭐⭐⭐⭐⭐]
- 링크: [뉴스 링크]

뉴스 데이터:
{news_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "너는 철도/AI/산업 분야 전문 에디터야. 핵심만 간결하게 정리해."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )
    return response.choices[0].message.content

def main():
    print("아침 브리핑 생성 중...")
    today = datetime.now().strftime('%Y년 %m월 %d일')

    sections = {
        "🚇 철도 정책 및 노선": "철도+GTX+지하화+개통+정책",
        "🏢 철도 운영사 소식": "신분당선+네오트랜스+코레일+서울교통공사",
        "🤖 AI 및 신기술": "AI+인공지능+챗GPT+반도체+로봇",
        "🏭 대한민국 산업 전반": "산업+경제+제조업+수출+무역",
    }

    report = f"""🌤️ {today} 네오트랜스 아침 브리핑
밤사이 들어온 주요 소식을 정리해 드립니다. 오늘도 활기찬 하루 되세요! 😊
{'='*50}

"""

    for topic, keyword in sections.items():
        print(f"{topic} 수집 중...")
        news = get_naver_news(keyword, count=5)
        summary = summarize_with_gpt(topic, news, is_paper=False)
        report += f"## {topic}\n{summary}\n\n{'─'*40}\n\n"

    # 논문 섹션
    print("최신 논문 수집 중...")
    papers = get_arxiv_papers(query="railway AI transportation safety", count=3)
    paper_summary = summarize_with_gpt("📚 최신 논문", papers, is_paper=True)
    report += f"## 📚 최신 논문 (AI/철도/교통)\n{paper_summary}\n\n{'─'*40}\n\n"

    report += f"""{'='*50}
※ 본 메일은 전문 매체 데이터를 기반으로 AI가 자동 생성하였습니다.
※ 뉴스 링크를 클릭하여 원문을 확인하시기 바랍니다.
"""

    send_email(report)
    print("브리핑 발송 완료!")

def send_email(body):
    EMAIL_USER = os.environ.get('EMAIL_USER', '').strip()
    EMAIL_PASS = os.environ.get('EMAIL_PASS', '').strip()
    EMAIL_TO = os.environ.get('EMAIL_TO', '').strip()

    today = datetime.now().strftime('%m/%d')
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = f"🚅 [네오트랜스] 오늘의 산업 및 철도 브리핑 ({today})"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
    print("이메일 발송 성공!")

if __name__ == "__main__":
    main()
