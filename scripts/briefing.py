import os
import requests
import feedparser
import json
from datetime import datetime, timezone, timedelta
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

DASHBOARD_URL = "https://leebum0406-cloud.github.io/neo-daily-briefing/"

SEARCH_TOPICS = {
    "🚇 철도/교통 정책": [
        "철도 정책", "철도 노선", "철도 건설", "철도 개통", "철도 안전",
        "GTX", "GTX-A", "GTX-B", "광역급행철도",
        "지하철 노선", "지하철 연장", "지하철 개통",
        "신분당선", "신안산선", "수서광주선",
        "KTX", "SRT", "고속철도",
        "트램", "경전철", "도시철도",
        "코레일", "서울교통공사", "국토부 철도",
    ],
    "🏢 국내 경제/산업": [
        "한국 경제", "산업 동향", "수출 무역",
        "반도체 산업", "배터리 산업", "자동차 산업",
        "부동산 정책", "금리 인상", "물가 동향",
    ],
    "🤖 AI/테크": [
        "인공지능 AI", "챗GPT", "AI 로봇",
        "딥러닝", "AI 반도체", "생성형 AI",
        "자율주행", "스마트시티", "디지털 전환",
    ],
    "🌏 글로벌 철도": [
        "유럽 철도", "독일 철도", "프랑스 TGV",
        "일본 신칸센", "중국 고속철도",
        "사우디 철도", "해외 철도 수주",
        "자율주행 열차", "수소 열차", "철도 기술 혁신",
    ],
}

PAPER_FEEDS = [
    "https://export.arxiv.org/rss/cs.AI",
    "https://export.arxiv.org/rss/cs.LG",
    "https://export.arxiv.org/rss/cs.CV",
    "https://export.arxiv.org/rss/cs.RO",
    "https://export.arxiv.org/rss/eess.SY",
    "https://export.arxiv.org/rss/eess.SP",
    "https://export.arxiv.org/rss/eess.EE",
    "https://export.arxiv.org/rss/physics.soc-ph",
]

PAPER_KEYWORDS = [
    "railway", "railroad", "metro", "train", "transit", "transportation",
    "autonomous vehicle", "traffic", "rail",
    "large language model", "LLM", "reinforcement learning", "deep learning",
    "neural network", "transformer", "autonomous", "robot",
    "electric vehicle", "battery", "power grid", "energy storage",
]


def refresh_kakao_token():
    rest_key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET", "").strip()
    refresh_tok = os.environ.get("KAKAO_REFRESH_TOKEN", "").strip()
    if not rest_key or not refresh_tok:
        return None
    try:
        res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": rest_key,
                "client_secret": client_secret,
                "refresh_token": refresh_tok,
            },
            timeout=10,
        )
        data = res.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        env_file = os.environ.get("GITHUB_ENV", "")
        if env_file and new_access:
            with open(env_file, "a") as f:
                f.write(f"KAKAO_ACCESS_TOKEN={new_access}\n")
            if new_refresh:
                with open(env_file, "a") as f:
                    f.write(f"KAKAO_REFRESH_TOKEN={new_refresh}\n")
        return new_access
    except Exception as e:
        print(f"카카오 토큰 갱신 오류: {e}")
        return None


def send_kakao(today_display, kakao_sections):
    access_token = os.environ.get("KAKAO_ACCESS_TOKEN", "").strip()
    if not access_token:
        access_token = refresh_kakao_token()
    if not access_token:
        print("⚠️ 카카오 액세스 토큰 없음 — 발송 건너뜀")
        return

    lines = [f"🌤️ {today_display} 네오트랜스 브리핑\n"]
    for sec in kakao_sections:
        lines.append(f"{sec['topic']}")
        for hl in sec["headlines"][:2]:
            lines.append(f"  • {hl[:40]}...")
        lines.append("")
    lines.append("▶ 전체 내용은 이메일을 확인하세요")
    body_text = "\n".join(lines)

    template = {
        "object_type": "feed",
        "content": {
            "title": f"🚅 {today_display} 네오트랜스 브리핑",
            "description": body_text,
            "link": {
                "web_url": DASHBOARD_URL,
                "mobile_web_url": DASHBOARD_URL,
            },
        },
        "buttons": [
            {
                "title": "대시보드 열기",
                "link": {
                    "web_url": DASHBOARD_URL,
                    "mobile_web_url": DASHBOARD_URL,
                },
            }
        ],
    }

    def _post(token):
        return requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {token}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=10,
        )

    res = _post(access_token)
    if res.status_code == 200:
        print("✅ 카카오톡 발송 완료")
    elif res.status_code == 401:
        print("🔄 카카오 토큰 만료 — 자동 갱신 시도")
        new_token = refresh_kakao_token()
        if new_token:
            res2 = _post(new_token)
            if res2.status_code == 200:
                print("✅ 카카오톡 재발송 완료")
            else:
                print(f"❌ 카카오톡 재발송 실패: {res2.status_code} {res2.text}")
        else:
            print("❌ 토큰 갱신 실패")
    else:
        print(f"❌ 카카오톡 발송 실패: {res.status_code} {res.text}")


def search_naver_news(keyword, display=3):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": display, "sort": "date"}
    items = []
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        for item in data.get("items", []):
            title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&#39;", "'")
            desc = item["description"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&#39;", "'")
            items.append({
                "title": title,
                "link": item["originallink"] or item["link"],
                "summary": desc,
            })
    except Exception as e:
        print(f"네이버 API 오류 ({keyword}): {e}")
    return items


def fetch_papers(count=6):
    items = []
    seen = set()
    for url in PAPER_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:400].strip()
                link = entry.get("link", "").strip()
                if title in seen:
                    continue
                text = (title + " " + summary).lower()
                if any(kw.lower() in text for kw in PAPER_KEYWORDS):
                    seen.add(title)
                    items.append({
                        "title": title,
                        "link": link,
                        "summary": summary,
                    })
                if len(items) >= count:
                    break
        except Exception as e:
            print(f"논문 수집 오류 ({url}): {e}")
        if len(items) >= count:
            break
    return items[:count]


def summarize_section(topic, news_list, is_paper=False):
    if not news_list:
        return "❌ 해당 카테고리 뉴스를 가져오지 못했습니다."

    news_text = "\n\n".join([
        f"[{i+1}] 제목: {n['title']}\n내용: {n.get('summary', '요약 없음')}\n링크: {n['link']}"
        for i, n in enumerate(news_list)
    ])

    if is_paper:
        prompt = f"""
최신 논문을 네오트랜스(신분당선 운영사) 임직원이 이해하기 쉽게 정리해주세요.

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
네오트랜스(신분당선 운영사) 임직원을 위한 {topic} 뉴스 브리핑을 작성해주세요.

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

    try:
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
    except Exception as e:
        print(f"GPT 오류: {e}")
        return "❌ AI 요약 생성 중 오류가 발생했습니다."


def generate_top3(report):
    try:
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
    except Exception as e:
        print(f"TOP3 생성 오류: {e}")
        return ""


def send_email(subject, body):
    try:
        EMAIL_USER = os.environ.get("EMAIL_USER", "").strip()
        EMAIL_PASS = os.environ.get("EMAIL_PASS", "").strip()
        EMAIL_TO = os.environ.get("EMAIL_TO", "").strip()
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("✅ 이메일 발송 성공!")
    except Exception as e:
        print(f"❌ 이메일 발송 오류: {e}")


def ping_supabase():
    try:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        if url and key:
            requests.get(
                f"{url}/rest/v1/documents?select=id&limit=1",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                timeout=10
            )
            print("✅ Supabase 핑 완료!")
    except Exception as e:
        print(f"Supabase 핑 오류: {e}")


def main():
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    today_display = now.strftime("%Y년 %m월 %d일")

    print(f"[{today_display}] 브리핑 생성 시작...")

    # Supabase 활성화 유지
    ping_supabase()

    dashboard_items = []
    kakao_sections = []
    final_report = f"🌤️ {today_display} 네오트랜스 아침 브리핑\n오늘도 활기찬 하루 되세요! 😊\n{'='*60}\n\n"

    # 뉴스 섹션
    for topic, keywords in SEARCH_TOPICS.items():
        print(f"  {topic} 수집 중...")
        all_news = []
        for kw in keywords:
            all_news.extend(search_naver_news(kw, display=3))
        unique_news = list({n["title"]: n for n in all_news}.values())[:8]
        print(f"  → {len(unique_news)}개 수집됨")

        summary = summarize_section(topic, unique_news)
        final_report += f"{'='*60}\n{topic}\n{'='*60}\n\n{summary}\n\n"
        dashboard_items.append({"topic": topic, "content": summary})
        kakao_sections.append({
            "topic": topic,
            "headlines": [n["title"] for n in unique_news],
        })

    # 논문 섹션
    print("  📚 논문 수집 중...")
    papers = fetch_papers(count=5)
    print(f"  → {len(papers)}개 수집됨")
    p_summary = summarize_section("📚 최신 논문", papers, is_paper=True)
    final_report += f"{'='*60}\n📚 최신 논문 (AI/철도/교통)\n{'='*60}\n\n{p_summary}\n\n"
    dashboard_items.append({"topic": "📚 최신 논문", "content": p_summary})
    kakao_sections.append({
        "topic": "📚 최신 논문",
        "headlines": [p["title"] for p in papers],
    })

    # TOP3 요약
    print("  🎯 핵심 요약 생성 중...")
    top3 = generate_top3(final_report)
    final_report += f"{'='*60}\n🎯 오늘의 핵심 뉴스 TOP 3\n{'='*60}\n{top3}\n\n"
    final_report += "※ 본 메일은 네이버 뉴스 API 및 논문 데이터를 기반으로 AI가 자동 생성하였습니다.\n"
    final_report += "※ 각 뉴스의 원문 링크를 클릭하여 상세 내용을 확인하시기 바랍니다."

    # 데이터 저장
    os.makedirs("data", exist_ok=True)
    output = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "date": today,
        "report": dashboard_items,
    }
    with open(f"data/{today}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    index_path = "data/index.json"
    existing_dates = []
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            existing_dates = json.load(f)
    if today not in existing_dates:
        existing_dates.insert(0, today)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(existing_dates, f, ensure_ascii=False, indent=2)

    # 발송
    send_email(f"🚅 [네오트랜스] 오늘의 브리핑 ({now.strftime('%m/%d')})", final_report)
    send_kakao(today_display, kakao_sections)
    print(f"✅ 완료!")


if __name__ == "__main__":
    main()
