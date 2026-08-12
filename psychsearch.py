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
    .ext-badge {
        display: inline-block;
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        padding: 6px 12px;
        margin: 4px;
        border-radius: 16px;
        font-size: 13px;
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

# 心理学/社工专业词汇映射字典
DICT_MAPPING = {
    "认知行为疗法": "Cognitive Behavioral Therapy CBT",
    "创伤后应激": "Post-Traumatic Stress Disorder PTSD trauma-informed",
    "依恋理论": "Attachment Theory internal working models",
    "正念": "Mindfulness-based interventions",
    "接纳承诺疗法": "Acceptance and Commitment Therapy ACT",
    "移情": "Transference countertransference counselling",
    "心理弹性": "Psychological resilience coping mechanisms",
    "同理心": "Empathy therapeutic alliance",
    "去标签化": "Destigmatization mental health social work",
    "社工介入": "Social work intervention community practice"
}

def translate_and_expand_query(user_input: str):
    """映射中文输入为专业英文表达式"""
    english_query = user_input
    for key, val in DICT_MAPPING.items():
        if key in user_input:
            english_query = english_query.replace(key, val)
    
    highlight_terms = [user_input.strip()]
    if english_query != user_input:
        highlight_terms.extend([term for term in english_query.split() if len(term) > 2])
    
    return english_query, list(set(highlight_terms))

def highlight_text(text: str, terms: list) -> str:
    """在文本中自动标黄匹配关键词"""
    if not text:
        return "暂无简介/摘要"
    for term in terms:
        if not term or len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', text)
    return text

def fetch_pop_science_web(en_query: str):
    """抓取科普与科普网站（Psychology Today, Verywell Mind, Simply Psychology, Wikipedia等）"""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. 优先获取维基百科（Wikipedia）权威词条概述
    try:
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(en_query)}"
        res = requests.get(wiki_url, headers=headers, timeout=4)
        if res.status_code == 200:
            w_data = res.json()
            if w_data.get("type") != "disambiguation" and w_data.get("extract"):
                results.append({
                    "title": f"维基百科 (Wikipedia): {w_data.get('title')}",
                    "snippet": w_data.get("extract"),
                    "url": w_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "source": "Wikipedia 权威词条"
                })
    except Exception:
        pass

    # 2. 获取大众科普与介绍性网页
    try:
        ddg_url = "https://html.duckduckgo.com/html/"
        search_term = f"{en_query} psychology"
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
                    
                    snippet = a_snippet.text.strip() if a_snippet else "暂无描述"
                    source_domain = a_url.text.strip() if a_url else "Web Resource"
                    
                    # 排除纯学术库域名，保留科普网站
                    if not any(domain in actual_link for domain in ["sciencedirect", "ncbi.nlm.nih.gov/pmc", "doi.org"]):
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "url": actual_link,
                            "source": source_domain
                        })
                    if len(results) >= 12:
                        break
    except Exception:
        pass
        
    return results

def fetch_academic_papers(en_query: str):
    """抓取学术期刊论文（Semantic Scholar + Europe PMC）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(en_query)}&limit=10&fields=title,abstract,url,venue,year,authors,citationCount"
        res = requests.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            papers = res.json().get("data")
            if papers:
                return papers, "Semantic Scholar"
    except Exception:
        pass

    try:
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(en_query)}&format=json&pageSize=10"
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
                return formatted, "Europe PMC"
    except Exception:
        pass

    return [], "None"

def get_extension_keywords(query_text: str):
    return {
        "vertical": [
            f"{query_text} neurobiological mechanism",
            f"{query_text} randomized controlled trial RCT",
            f"{query_text} DSM-5 diagnostic criteria",
            f"{query_text} assessment scale measurement"
        ],
        "horizontal": [
            f"{query_text} social work community practice",
            f"{query_text} cross-cultural considerations",
            f"{query_text} family systems therapy",
            f"{query_text} ethics and therapeutic alliance"
        ]
    }

# --- 主界面 UI ---
st.title("🧠 Psychology, Counselling & Social Work Search")
st.caption("综合搜索引擎 · 包含科普网站/知识介绍 + 学术论文 · 自动中英映射与高亮标黄")

query_input = st.text_input("输入查询关键词（支持中文或英文）：", placeholder="例如：依恋理论、认知行为疗法、Attachment Theory")

if query_input:
    en_query, highlight_keywords = translate_and_expand_query(query_input)
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info(f"**实际检索学术/英文表达式：** `{en_query}`")
    with col_b:
        st.success("已开启无广告学术与科普过滤")

    # 分标签页展示科普与学术结果
    tab_pop, tab_academic = st.tabs(["📖 科普/知识介绍网站 (Psychology Today / 维基 / 大众导读)", "🎓 专业学术论文与期刊 (Semantic Scholar / PubMed)"])

    # Tab 1: 科普网页
    with tab_pop:
        with st.spinner("正在检索科普与知识介绍网站..."):
            pop_results = fetch_pop_science_web(en_query)
            if not pop_results:
                st.warning("暂未抓取到相关科普网页，请尝试调整关键词或查看“学术论文”标签页。")
            else:
                st.caption(f"已为你找到 {len(pop_results)} 条科普与知识介绍网页：")
                for item in pop_results:
                    title_hl = highlight_text(item["title"], highlight_keywords)
                    snippet_hl = highlight_text(item["snippet"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-pop">🌐 科普 / 大众介绍</span>
                        <a class="card-title" href="{item['url']}" target="_blank">{title_hl}</a>
                        <div class="card-meta">🔗 <strong>来源网站:</strong> {item['source']}</div>
                        <div class="card-snippet">{snippet_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 2: 学术论文
    with tab_academic:
        with st.spinner("正在检索学术数据库..."):
            papers, source_engine = fetch_academic_papers(en_query)
            if not papers:
                st.warning("未找到匹配文献，请尝试更换关键词。")
            else:
                st.caption(f"数据来源：`{source_engine}` | 共匹配 {len(papers)} 篇学术文献")
                for paper in papers:
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
                        <span class="badge-academic">🎓 期刊论文</span>
                        <a class="card-title" href="{url}" target="_blank">{title_hl}</a>
                        <div class="card-meta">
                            📅 <strong>年份:</strong> {year} | 📖 <strong>期刊:</strong> {venue} | ✍️ <strong>作者:</strong> {authors} | 🔗 <strong>引用数:</strong> {citations}
                        </div>
                        <div class="card-snippet">{abstract_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 底部知识拓展
    st.divider()
    st.markdown("### 🔍 知识拓展与横向/纵深延伸")
    extensions = get_extension_keywords(query_input)
    col_v, col_h = st.columns(2)
    with col_v:
        st.markdown("**📌 纵深探索（作用机制 / 实证研究 / 评估工具）：**")
        for ext in extensions["vertical"]:
            st.markdown(f'<span class="ext-badge">🔍 {ext}</span>', unsafe_allow_html=True)
    with col_h:
        st.markdown("**🌐 横向拓展（社工介入 / 交叉学科 / 流派结合）：**")
        for ext in extensions["horizontal"]:
            st.markdown(f'<span class="ext-badge">🌐 {ext}</span>', unsafe_allow_html=True)
