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

# 검색 키워드 설정
SEARCH_TOPICS = {
    "🚇 철도/교통 정책": [
        "철도 정책", "철도 노선", "철도 건설", "철도 개통", "철도 안전",
        "GTX", "GTX-A", "GTX-B", "GTX-C", "GTX-D", "광역급행철도",
        "지하철 노선", "지하철 연장", "지하철 개통", "서울 지하철", "수도권 지하철",
        "부산 지하철", "대구 지하철", "인천 지하철", "광주 지하철", "대전 지하철",
        "신분당선", "신안산선", "수서광주선", "동북선", "면목선", "목동선",
        "KTX", "SRT", "고속철도", "ITX", "무궁화호",
        "트램", "경전철", "도시철도",
        "코레일", "SR", "철도공단", "서울교통공사", "국토부 철도",
    ],
    "🏢 국내 경제/산업": ["한국 경제", "산업 동향", "수출 무역", "제조업", "반도체 산업"],
    "🤖 AI/테크": ["인공지능 AI", "챗GPT", "AI 로봇", "딥러닝", "AI 반도체"],
    "🌏 글로벌 철도": [
        # 유럽
        "유럽 철도", "독일 철도", "프랑스 철도", "영국 철도", "유럽 고속철도",
        "TGV", "ICE 열차", "유로스타", "야간열차 유럽",
        # 아시아
        "일본 철도", "신칸센", "중국 철도", "중국 고속철도", "인도 철도",
        "동남아 철도", "베트남 철도", "인도네시아 철도",
        # 중동/아프리카
        "사우디 철도", "사우디 네옴 철도", "UAE 철도", "중동 철도",
        "아프리카 철도", "이집트 철도",
        # 미주
        "미국 철도", "암트랙", "남미 철도", "브라질 철도",
        # 글로벌 기술/트렌드
        "해외 철도 수주", "철도 수출", "자율주행 열차", "수소 열차", "초고속 철도",
        "하이퍼루프", "철도 기술 혁신",
    ],
}

PAPER_FEEDS = [
    # AI / 머신러닝
    "https://export.arxiv.org/rss/cs.AI",       # 인공지능
    "https://export.arxiv.org/rss/cs.LG",       # 머신러닝
    "https://export.arxiv.org/rss/cs.CV",       # 컴퓨터 비전
    "https://export.arxiv.org/rss/cs.RO",       # 로보틱스
    # 시스템/제어 (철도 제어시스템 관련)
    "https://export.arxiv.org/rss/eess.SY",     # 시스템 및 제어
    "https://export.arxiv.org/rss/eess.SP",     # 신호처리
    # 전기/에너지 (전기철도 관련)
    "https://export.arxiv.org/rss/eess.EE",     # 전기공학
    # 물리/교통
    "https://export.arxiv.org/rss/physics.soc-ph",  # 사회물리학 (교통망 포함)
]

# 논문 필터링 키워드 (철도/교통/AI 관련 논문만 선별)
PAPER_KEYWORDS = [
    # 철도/교통
    "railway", "railroad", "metro", "train", "transit", "transportation",
    "autonomous vehicle", "traffic", "rail",
    # AI/테크
    "large language model", "LLM", "reinforcement learning", "deep learning",
    "neural network", "transformer", "autonomous", "robot",
    # 전기/에너지
    "electric vehicle", "battery", "power grid", "energy storage",
    "electric motor", "charging",
]


# ────────────────────────────────────────────────────────────
# 카카오 토큰 자동 갱신
# ────────────────────────────────────────────────────────────
def refresh_kakao_token():
    rest_key      = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET", "").strip()
    refresh_tok   = os.environ.get("KAKAO_REFRESH_TOKEN", "").strip()
    if not rest_key or not refresh_tok:
        return None

    res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type":    "refresh_token",
            "client_id":     rest_key,
            "client_secret": client_secret,
            "refresh_token": refresh_tok,
        },
        timeout=10,
    )
    data        = res.json()
    new_access  = data.get("access_token")
    new_refresh = data.get("refresh_token")

    env_file = os.environ.get("GITHUB_ENV", "")
    if env_file and new_access:
        with open(env_file, "a") as f:
            f.write(f"KAKAO_ACCESS_TOKEN={new_access}\n")
        if new_refresh:
            with open(env_file, "a") as f:
                f.write(f"KAKAO_REFRESH_TOKEN={new_refresh}\n")

    return new_access


# ────────────────────────────────────────────────────────────
# 카카오톡 나에게 보내기
# ────────────────────────────────────────────────────────────
def send_kakao(today_display, kakao_sections):
    access_token = os.environ.get("KAKAO_ACCESS_TOKEN", "").strip()
    if not access_token:
        access_token = refresh_kakao_token()
    if not access_token:
        print("⚠️ 카카오 액세스 토큰 없음 — 발송 건너뜀")
        return

    # 본문 텍스트 구성
    lines = [""]
    for sec in kakao_sections:
        lines.append(f"{sec['topic']}")
        for hl in sec["headlines"][:3]:
            lines.append(f"  • {hl}")
        lines.append("")
    lines.append("▶ 전체 내용은 대시보드에서 확인하세요")
    body_text = "\n".join(lines)

    template = {
        "object_type": "feed",
        "content": {
            "title":        f"{today_display}",
            "description":  body_text,
            "image_url":    f"{DASHBOARD_URL}og-image-v2.png?v={datetime.now().strftime('%Y%m%d')}",
            "image_width":  1200,
            "image_height": 630,
            "link": {
                "web_url":        DASHBOARD_URL,
                "mobile_web_url": DASHBOARD_URL,
            },
        },
        "buttons": [
            {
                "title": "대시보드 열기",
                "link": {
                    "web_url":        DASHBOARD_URL,
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


# ────────────────────────────────────────────────────────────
# 기존 함수들
# ────────────────────────────────────────────────────────────
def search_naver_news(keyword, display=3):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": display, "sort": "date"}
    items = []
    try:
        res  = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        for item in data.get("items", []):
            title = item["title"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
            desc  = item["description"].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
            items.append({
                "title":   title,
                "link":    item["originallink"] or item["link"],
                "summary": desc,
            })
    except:
        pass
    return items


def fetch_papers(count=6):
    items = []
    seen = set()
    for url in PAPER_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:400].strip()
                link    = entry.get("link", "").strip()

                if title in seen:
                    continue

                # 관련 키워드 포함 논문만 선별
                text = (title + " " + summary).lower()
                if any(kw.lower() in text for kw in PAPER_KEYWORDS):
                    seen.add(title)
                    items.append({
                        "title":   title,
                        "link":    link,
                        "summary": summary,
                    })
                    if len(items) >= count:
                        break
        except:
            pass
        if len(items) >= count:
            break
    return items[:count]


def summarize_section(topic, news_list, is_paper=False):
    if not news_list:
        return "❌ 해당 카테고리 뉴스를 가져오지 못했습니다."
    news_text = "\n\n".join(
        [f"제목: {n['title']}\n내용: {n.get('summary', '')}\n링크: {n['link']}" for n in news_list]
    )
    prompt = (
        f"네오트랜스 임직원을 위한 {topic} 브리핑을 작성해줘. "
        "형식은 마크다운을 사용하고 각 뉴스별로 제목, 핵심내용, 시사점, 링크를 포함해줘."
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "전문 뉴스 에디터 역할."},
            {"role": "user",   "content": f"{news_text}\n\n{prompt}"},
        ],
    )
    return response.choices[0].message.content


def send_email(subject, body):
    EMAIL_USER = os.environ.get("EMAIL_USER", "").strip()
    EMAIL_PASS = os.environ.get("EMAIL_PASS", "").strip()
    EMAIL_TO   = os.environ.get("EMAIL_TO",   "").strip()
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"]    = EMAIL_USER
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(body, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


# ────────────────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────────────────
def main():
    KST = timezone(timedelta(hours=9))
    now           = datetime.now(KST)
    today         = now.strftime("%Y-%m-%d")
    today_display = now.strftime("%Y년 %m월 %d일")
    dashboard_items = []
    kakao_sections  = []
    final_report    = f"🌤️ {today_display} 네오트랜스 아침 브리핑\n\n"

    # 뉴스 섹션 처리
    for topic, keywords in SEARCH_TOPICS.items():
        all_news = []
        for kw in keywords:
            all_news.extend(search_naver_news(kw))
        unique_news = list({n["title"]: n for n in all_news}.values())[:10]

        summary = summarize_section(topic, unique_news)
        final_report += f"### {topic}\n{summary}\n\n"
        dashboard_items.append({"topic": topic, "content": summary})
        kakao_sections.append({
            "topic":     topic,
            "headlines": [n["title"] for n in unique_news],
        })

    # 논문 섹션
    papers    = fetch_papers()
    p_summary = summarize_section("📚 최신 논문", papers, is_paper=True)
    final_report += f"### 📚 최신 논문\n{p_summary}"
    dashboard_items.append({"topic": "📚 최신 논문", "content": p_summary})
    kakao_sections.append({
        "topic":     "📚 최신 논문",
        "headlines": [p["title"] for p in papers],
    })

    # ── 데이터 저장 ──────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    output = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "date":       today,
        "report":     dashboard_items,
    }

    with open(f"data/{today}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    index_path     = "data/index.json"
    existing_dates = []
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            existing_dates = json.load(f)
    if today not in existing_dates:
        existing_dates.insert(0, today)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(existing_dates, f, ensure_ascii=False, indent=2)
    # ─────────────────────────────────────────────────────────

    # ── 발송 ─────────────────────────────────────────────────
    send_email(f"🚅 [네오트랜스] 브리핑 ({now.strftime('%m/%d')})", final_report)
    send_kakao(today_display, kakao_sections)
    print(f"✅ 완료 - {today}.json 저장, 이메일 + 카카오톡 발송")


if __name__ == "__main__":
    main()
