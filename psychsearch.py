import streamlit as st
import requests
import re
from urllib.parse import quote_plus, unquote
from bs4 import BeautifulSoup

# 页面基础配置
st.set_page_config(
    page_title="心理学、咨询与社工全能搜索引擎",
    page_icon="🧠",
    layout="wide"
)

# 样式增强
st.markdown("""
<style>
    .card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .card-title {
        font-size: 18px;
        font-weight: 600;
        color: #1e3a8a;
        text-decoration: none;
    }
    .card-meta {
        font-size: 13px;
        color: #64748b;
        margin: 6px 0;
    }
    .card-snippet {
        font-size: 14px;
        color: #334155;
        line-height: 1.6;
    }
    .highlight {
        background-color: #fef08a;
        color: #854d0e;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: 600;
    }
    .badge-ngo {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-wiki {
        background-color: #f3f4f6;
        color: #374151;
        border: 1px solid #e5e7eb;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-pop {
        background-color: #f0fdf4;
        color: #166534;
        border: 1px solid #bbf7d0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-academic {
        background-color: #f0f9ff;
        color: #0369a1;
        border: 1px solid #bae6fd;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# 心理学/咨询/社工同义词与近义词扩展词典
DICT_MAPPING = {
    "认知行为疗法": ["Cognitive Behavioral Therapy", "CBT", "cognitive restructuring", "behavioral therapy"],
    "创伤后应激": ["Post-Traumatic Stress Disorder", "PTSD", "trauma-informed", "trauma therapy", "complex PTSD"],
    "依恋理论": ["Attachment Theory", "attachment style", "secure attachment", "insecure attachment", "internal working models"],
    "正念": ["Mindfulness", "mindfulness-based interventions", "MBCT", "MBSR"],
    "接纳承诺疗法": ["Acceptance and Commitment Therapy", "ACT", "psychological flexibility"],
    "移情": ["Transference", "countertransference", "therapeutic alliance", "counselling relationship"],
    "心理弹性": ["Psychological resilience", "resilience", "coping mechanisms", "adaptive coping"],
    "同理心": ["Empathy", "empathic listening", "therapeutic alliance", "person-centered"],
    "去标签化": ["Destigmatization", "mental health stigma", "stigma reduction"],
    "社工介入": ["Social work intervention", "community practice", "case management", "social work assessment"],
    "抑郁": ["Depression", "depressive symptoms", "major depressive disorder", "MDD"],
    "焦虑": ["Anxiety", "generalized anxiety disorder", "GAD", "anxiety symptoms"],
    "家庭治疗": ["Family therapy", "systemic therapy", "family systems"],
    "精神分析": ["Psychoanalysis", "psychodynamic therapy", "unconscious processes"]
}

# 知名公益机构与知识库域名关键字
NGO_DOMAINS = ["apa.org", "who.int", "nimh.nih.gov", "beyondblue.org.au", "headspace.org.au", "samhsa.gov", "blackdoginstitute.org.au", "mind.org.uk", "nami.org", "pacfa.org.au", "aasw.asn.au"]

if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

def update_query(new_term):
    st.session_state["search_query"] = new_term

def translate_and_expand_query(user_input: str):
    english_terms = []
    highlight_terms = [user_input.strip()]
    found_mapped = False
    
    for key, syn_list in DICT_MAPPING.items():
        if key in user_input:
            found_mapped = True
            english_terms.extend(syn_list)
            highlight_terms.extend(syn_list)
            highlight_terms.append(key)
    
    if not found_mapped:
        english_terms.append(user_input)
        for w in user_input.split():
            if len(w) > 1:
                highlight_terms.append(w)
    
    main_query = " ".join(english_terms[:3])
    return main_query, list(set(highlight_terms))

def highlight_text(text: str, terms: list) -> str:
    if not text:
        return "暂无简介/摘要"
    for term in terms:
        if not term or len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', text)
    return text

def fetch_pop_and_ngo_web(en_query: str):
    """抓取公益机构、百科与科普知识网站（有多大抓多大，有多少算多少）"""
    results = []
    seen_urls = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. 抓取 Wikipedia 多词条知识库 API（不限流，极速稳定）
    try:
        wiki_api = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(en_query)}&format=json&utf8=1"
        res = requests.get(wiki_api, headers=headers, timeout=4)
        if res.status_code == 200:
            wiki_items = res.json().get("query", {}).get("search", [])
            for w in wiki_items[:5]:
                page_title = w.get("title")
                snippet_clean = re.sub('<[^<]+?>', '', w.get("snippet", "")) + "..."
                page_url = f"https://en.wikipedia.org/wiki/{quote_plus(page_title)}"
                if page_url not in seen_urls:
                    seen_urls.add(page_url)
                    results.append({
                        "title": f"Wikipedia 百科词条: {page_title}",
                        "snippet": snippet_clean,
                        "url": page_url,
                        "source": "Wikipedia 维基百科",
                        "badge": "badge-wiki",
                        "badge_text": "📖 知识百科"
                    })
    except Exception:
        pass

    # 2. 抓取 Web 知识网站与公益机构（有多大展示多少）
    try:
        ddg_url = "https://html.duckduckgo.com/html/"
        search_term = f"{en_query} psychology OR counselling OR mental health"
        res = requests.post(ddg_url, data={"q": search_term}, headers=headers, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.find_all("div", class_="result"):
                a_title = div.find("a", class_="result__a")
                a_snippet = div.find("a", class_="result__snippet")
                a_url = div.find("a", class_="result__url")
                if a_title:
                    title = a_title.text.strip()
                    raw_link = a_title.get("href", "")
                    actual_link = raw_link
                    if "uddg=" in raw_link:
                        actual_link = unquote(raw_link.split("uddg=")[1].split("&")[0])
                    
                    if actual_link in seen_urls:
                        continue
                    seen_urls.add(actual_link)

                    snippet = a_snippet.text.strip() if a_snippet else "暂无描述"
                    source_domain = a_url.text.strip() if a_url else "Web Resource"

                    # 识别是否为公益/权威机构
                    is_ngo = any(domain in actual_link.lower() or domain in source_domain.lower() for domain in NGO_DOMAINS)
                    badge_cls = "badge-ngo" if is_ngo else "badge-pop"
                    badge_txt = "🏛️ 公益/权威机构" if is_ngo else "🌐 科普/知识网站"

                    if not any(domain in actual_link for domain in ["sciencedirect", "ncbi.nlm.nih.gov/pmc", "doi.org"]):
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "url": actual_link,
                            "source": source_domain,
                            "badge": badge_cls,
                            "badge_text": badge_txt
                        })
                    if len(results) >= 25:
                        break
    except Exception:
        pass

    return results

def fetch_academic_papers(en_query: str):
    """抓取学术论文（Semantic Scholar + Europe PMC）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(en_query)}&limit=25&fields=title,abstract,url,venue,year,authors,citationCount"
        res = requests.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            papers = res.json().get("data", [])
            if papers:
                return papers, "Semantic Scholar Academic Database"
    except Exception:
        pass

    try:
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(en_query)}&format=json&pageSize=25"
        res = requests.get(pmc_url, headers=headers, timeout=5)
        if res.status_code == 200:
            result_list = res.json().get("resultList", {}).get("result", [])
            formatted = []
            for item in result_list:
                doi = item.get("doi")
                url = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/MED/{item.get('id')}"
                author_str = item.get("authorString", "")
                authors = [{"name": a.strip()} for a in author_str.split(",")[:3]] if author_str else []
                formatted.append({
                    "title": item.get("title", "Untitled Paper"),
                    "abstract": item.get("abstractText", ""),
                    "url": url,
                    "year": item.get("pubYear", "N/A"),
                    "venue": item.get("journalTitle", "Academic Journal"),
                    "citationCount": item.get("citedByCount", 0),
                    "authors": authors
                })
            if formatted:
                return formatted, "Europe PMC Academic Database"
    except Exception:
        pass

    return [], "None"

def get_extension_keywords(query_text: str):
    return {
        "vertical": [
            f"{query_text} neurobiological mechanism",
            f"{query_text} randomized controlled trial RCT",
            f"{query_text} DSM-5 diagnostic criteria",
            f"{query_text} assessment scale measurement",
            f"{query_text} systematic review meta-analysis"
        ],
        "horizontal": [
            f"{query_text} social work community practice",
            f"{query_text} cross-cultural considerations",
            f"{query_text} family systems therapy",
            f"{query_text} ethics and therapeutic alliance",
            f"{query_text} group counselling intervention"
        ]
    }

# --- 主界面 ---
st.title("🧠 Psychology, Counselling & Social Work Search")
st.caption("无广告·公益机构与科普知识库·同义词扩展·点击拓展词直接检索")

query_input = st.text_input(
    "输入查询关键词（支持中文或英文）：",
    value=st.session_state["search_query"],
    placeholder="例如：依恋理论、认知行为疗法、Attachment Theory",
    key="main_input"
)

if query_input:
    st.session_state["search_query"] = query_input
    en_query, highlight_keywords = translate_and_expand_query(query_input)
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info(f"**实际检索与同义词映射表达式：** `{en_query}`")
    with col_b:
        st.success("已开启无广告学术与科普过滤")

    tab_pop, tab_academic = st.tabs(["📖 科普/公益机构/知识介绍网站", "🎓 专业学术论文与期刊"])

    # Tab 1: 科普与公益机构
    with tab_pop:
        with st.spinner("正在检索公益机构与知识库..."):
            pop_results = fetch_pop_and_ngo_web(en_query)
            if not pop_results:
                st.info("暂未检索到相关科普网页，请点击“学术论文”标签页查看相关学术文献。")
            else:
                st.caption(f"已为你检索到 {len(pop_results)} 条相关知识网站与公益机构资源（按相关性排序）：")
                for idx, item in enumerate(pop_results, start=1):
                    title_hl = highlight_text(item["title"], highlight_keywords)
                    snippet_hl = highlight_text(item["snippet"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="{item['badge']}">#{idx} {item['badge_text']}</span>
                        <a class="card-title" href="{item['url']}" target="_blank">{title_hl}</a>
                        <div class="card-meta">🔗 <strong>来源网站:</strong> {item['source']}</div>
                        <div class="card-snippet">{snippet_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 2: 学术论文
    with tab_academic:
        with st.spinner("正在检索学术文献..."):
            papers, source_engine = fetch_academic_papers(en_query)
            if not papers:
                st.info("暂未检索到学术论文，请尝试调整关键词。")
            else:
                st.caption(f"数据来源：`{source_engine}` | 已找到 {len(papers)} 篇学术文献")
                for idx, paper in enumerate(papers, start=1):
                    title = paper.get("title", "Untitled Paper")
                    abstract = paper.get("abstract", "")
                    url = paper.get("url") or f"https://www.google.com/search?q={quote_plus(title)}"
                    year = paper.get("year", "N/A")
                    venue = paper.get("venue", "Academic Journal")
                    citations = paper.get("citationCount", 0)
                    authors = ", ".join([a["name"] for a in paper.get("authors", [])[:3]]) if paper.get("authors") else "Unknown"
                    
                    title_hl = highlight_text(title, highlight_keywords)
                    abstract_hl = highlight_text(abstract, highlight_keywords)
                    
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-academic">#{idx} 🎓 期刊论文</span>
                        <a class="card-title" href="{url}" target="_blank">{title_hl}</a>
                        <div class="card-meta">
                            📅 <strong>年份:</strong> {year} | 📖 <strong>期刊:</strong> {venue} | ✍️ <strong>作者:</strong> {authors} | 🔗 <strong>引用数:</strong> {citations}
                        </div>
                        <div class="card-snippet">{abstract_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 底部直接搜索的拓展区域
    st.divider()
    st.markdown("### 🔍 知识拓展与横向/纵深延伸（点击直接发起新搜索）")
    extensions = get_extension_keywords(query_input)
    col_v, col_h = st.columns(2)
    
    with col_v:
        st.markdown("**📌 纵深探索（作用机制 / 实证研究 / 评估工具）：**")
        for ext in extensions["vertical"]:
            st.button(f"🔍 {ext}", on_click=update_query, args=(ext,), key=f"btn_v_{ext}")
    
    with col_h:
        st.markdown("**🌐 横向拓展（社工介入 / 交叉学科 / 流派结合）：**")
        for ext in extensions["horizontal"]:
            st.button(f"🌐 {ext}", on_click=update_query, args=(ext,), key=f"btn_h_{ext}")
