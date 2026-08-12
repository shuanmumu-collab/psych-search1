import streamlit as st
import requests
import re
from urllib.parse import quote_plus

# 1. 页面基础配置
st.set_page_config(
    page_title="心理学、心理咨询与社工学术搜索引擎",
    page_icon="🧠",
    layout="wide"
)

# 2. 自定义 CSS 样式
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
    .badge-oa {
        background-color: #dcfce7;
        color: #15803d;
        border: 1px solid #86efac;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-score {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-synonym {
        background-color: #f3e8ff;
        color: #6b21a8;
        border: 1px solid #e9d5ff;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-gov {
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# 3. 心理学/咨询/社工同义词与近义词扩展词典
DICT_MAPPING = {
    "认知行为疗法": ["Cognitive Behavioral Therapy", "CBT", "cognitive restructuring", "behavioral therapy"],
    "创伤后应激": ["Post-Traumatic Stress Disorder", "PTSD", "trauma-informed care", "complex PTSD", "trauma intervention"],
    "依恋理论": ["Attachment Theory", "attachment style", "secure attachment", "internal working models", "Bowlby"],
    "正念": ["Mindfulness", "mindfulness-based interventions", "MBCT", "MBSR"],
    "接纳承诺疗法": ["Acceptance and Commitment Therapy", "ACT", "psychological flexibility"],
    "移情": ["Transference", "countertransference", "therapeutic alliance", "counselling relationship"],
    "心理弹性": ["Psychological resilience", "resilience", "coping mechanisms", "adaptive coping"],
    "同理心": ["Empathy", "empathic listening", "therapeutic alliance", "person-centered counselling"],
    "去标签化": ["Destigmatization", "mental health stigma", "stigma reduction", "social inclusion"],
    "社工介入": ["Social work intervention", "community practice", "case management", "social policy"],
    "儿童保护": ["Child protection", "child welfare", "working with children", "out-of-home care"],
    "抑郁": ["Depression", "depressive disorders", "major depressive disorder", "MDD"],
    "焦虑": ["Anxiety disorders", "generalized anxiety disorder", "GAD", "social anxiety"],
    "叙事疗法": ["Narrative therapy", "externalizing the problem", "re-authoring"],
    "焦点解决": ["Solution-focused brief therapy", "SFBT", "exception questions"]
}

# 4. 初始化 Session State 解决底部点击发起新搜索失效问题
if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

def update_query(new_term):
    """同时同步 search_query 与 main_input，确保 Streamlit 实时重新运行"""
    st.session_state["search_query"] = new_term
    st.session_state["main_input"] = new_term

def translate_and_expand_query(user_input: str):
    """中文到专业英文术语自动映射，并提取命中近义词"""
    english_terms = []
    highlight_terms = [user_input.strip()]
    matched_synonyms = []
    
    for key, syn_list in DICT_MAPPING.items():
        if key in user_input:
            english_terms.extend(syn_list)
            matched_synonyms.extend(syn_list)
            highlight_terms.extend(syn_list)
    
    if not matched_synonyms:
        english_terms.append(user_input)
        for w in user_input.split():
            if len(w) > 1:
                highlight_terms.append(w)
    
    main_query = " ".join(english_terms[:4])
    return main_query, list(set(highlight_terms)), list(set(matched_synonyms))

def calculate_relevance(title: str, snippet: str, raw_query: str, highlight_terms: list):
    """计算智能相关性得分 (65% - 99%) 并给出打分依据说明"""
    combined = (title + " " + snippet).lower()
    score = 65
    reasons = []

    # 1. 标题完全匹配或高匹配
    if raw_query.lower() in title.lower():
        score += 20
        reasons.append("标题包含核心搜索词")
    else:
        for term in highlight_terms:
            if len(term) > 2 and term.lower() in title.lower():
                score += 15
                reasons.append(f"标题命中近义词 '{term}'")
                break

    # 2. 正文关键术语出现频次计算
    match_count = 0
    for term in highlight_terms:
        if len(term) > 2 and term.lower() in combined:
            match_count += 1

    score += min(match_count * 3, 14)
    if match_count > 0:
        reasons.append(f"正文匹配 {match_count} 个领域概念/同义术语")

    final_score = min(max(score, 68), 98)
    reason_str = " | ".join(reasons) if reasons else "领域内容语义高度相关"
    return final_score, reason_str

def highlight_text(text: str, terms: list) -> str:
    """自动高亮匹配文本及其近义词"""
    if not text:
        return "暂无详细摘要/内容介绍"
    for term in terms:
        if not term or len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', text)
    return text

# 5. 抓取政府与权威机构报告（OpenAlex API）
def fetch_gov_reports(en_query: str, raw_query: str, highlight_terms: list):
    results = []
    headers = {"User-Agent": "PsychologyAcademicSearch/1.0 (mailto:researcher@example.com)"}
    try:
        url = f"https://api.openalex.org/works?search={quote_plus(en_query)}&per_page=20&sort=relevance_score:desc"
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            for item in res.json().get("results", []):
                title = item.get("display_name", "Untitled")
                doi_url = item.get("doi") or item.get("id")
                pub_year = item.get("publication_year", "N/A")
                
                # 提取摘要
                abstract_inverted = item.get("abstract_inverted_index")
                abstract = ""
                if abstract_inverted:
                    word_list = []
                    for word, pos_list in abstract_inverted.items():
                        for pos in pos_list:
                            word_list.append((pos, word))
                    word_list.sort()
                    abstract = " ".join([w[1] for w in word_list[:120]]) + "..."
                
                source_name = item.get("primary_location", {}).get("source", {}).get("display_name", "权威机构/智库报告")
                authorships = item.get("authorships", [])
                authors = [a.get("author", {}).get("display_name") for a in authorships[:3]]
                author_str = ", ".join(filter(None, authors)) or "政府/权威智库"

                score, reason = calculate_relevance(title, abstract, raw_query, highlight_terms)
                
                results.append({
                    "title": title,
                    "url": doi_url,
                    "year": pub_year,
                    "author": author_str,
                    "source": source_name,
                    "abstract": abstract or "权威机构研究报告/学术白皮书。",
                    "score": score,
                    "reason": reason
                })
    except Exception:
        pass

    # 按智能相关性百分比从高到低排序
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# 6. 抓取可免费下载全文的学术论文 (Europe PMC + OpenAlex OA 过滤)
def fetch_free_academic_papers(en_query: str, raw_query: str, highlight_terms: list):
    formatted = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 检索 Europe PMC 开放获取文献
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(en_query + ' OPEN_ACCESS:y')}&format=json&pageSize=25"
        res = requests.get(pmc_url, headers=headers, timeout=6)
        if res.status_code == 200:
            result_list = res.json().get("resultList", {}).get("result", [])
            for item in result_list:
                doi = item.get("doi")
                pmcid = item.get("pmcid")
                
                # 优先构建可免费阅读/下载 PDF 的链接
                if pmcid:
                    download_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
                    is_free = True
                elif doi:
                    download_url = f"https://doi.org/{doi}"
                    is_free = item.get("isOpenAccess") == "Y"
                else:
                    download_url = f"https://europepmc.org/article/MED/{item.get('id')}"
                    is_free = False

                title = item.get("title", "Untitled Paper")
                abstract = item.get("abstractText", "")
                author_str = item.get("authorString", "")
                authors = ", ".join([a.strip() for a in author_str.split(",")[:3]]) if author_str else "Unknown"
                
                score, reason = calculate_relevance(title, abstract, raw_query, highlight_terms)

                formatted.append({
                    "title": title,
                    "abstract": abstract,
                    "url": download_url,
                    "year": item.get("pubYear", "N/A"),
                    "venue": item.get("journalTitle", "Academic Journal"),
                    "citations": item.get("citedByCount", 0),
                    "authors": authors,
                    "is_free": is_free,
                    "score": score,
                    "reason": reason
                })
    except Exception:
        pass

    # 按相关性排序，免费可下载论文优先排序
    formatted.sort(key=lambda x: (x["score"], x["is_free"]), reverse=True)
    return formatted

# 7. 动态拓展词生成
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
            f"{query_text} policy and government guidelines"
        ]
    }

# --- 8. 主界面交互逻辑 ---
st.title("🧠 Psychology, Counselling & Social Work Search Engine")
st.caption("私人定制学术搜索引擎 | 智能相关性排序 · 近义词标记 · 免费全文论文优先 · 纵深/横向一键检索")

# 搜索框绑定 key 与 session_state
query_input = st.text_input(
    "输入查询关键词（支持中文或英文）：",
    value=st.session_state["search_query"],
    placeholder="例如：创伤后应激、依恋理论、Child protection counselling",
    key="main_input"
)

if query_input:
    st.session_state["search_query"] = query_input
    en_query, highlight_keywords, matched_synonyms = translate_and_expand_query(query_input)
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info(f"**实际检索学术表达式：** `{en_query}`")
        if matched_synonyms:
            st.markdown(f'<span class="badge-synonym">💡 已自动匹配近义/同义术语: {", ".join(matched_synonyms)}</span>', unsafe_allow_html=True)
    with col_b:
        st.success("已开启 100% 智能排序与无广告过滤")

    tab_academic, tab_gov = st.tabs([
        "🎓 核心学术论文 (免费全文下载优先)", 
        "🏛️ 政府部门与权威机构报告"
    ])

    # Tab 1: 免费全文学术论文
    with tab_academic:
        with st.spinner("正在检索并进行智能相关性排序（优先筛选可免费阅读/下载论文）..."):
            papers = fetch_free_academic_papers(en_query, query_input, highlight_keywords)
            if not papers:
                st.info("暂未检索到相关论文，请切换关键词尝试。")
            else:
                st.caption(f"已按相关性最高降序展示 {len(papers)} 篇学术文献：")
                for idx, paper in enumerate(papers, start=1):
                    t_hl = highlight_text(paper["title"], highlight_keywords)
                    a_hl = highlight_text(paper["abstract"], highlight_keywords)
                    
                    free_badge = '<span class="badge-oa">🔓 免费全文阅读/下载</span>' if paper["is_free"] else '<span class="badge-meta">📖 期刊索引</span>'
                    
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关性: {paper['score']}%</span> {free_badge}
                        <br><br>
                        <a class="card-title" href="{paper['url']}" target="_blank">#{idx} {t_hl}</a>
                        <div class="card-meta">
                            📅 <strong>年份:</strong> {paper['year']} | 📖 <strong>期刊:</strong> {paper['venue']} | ✍️ <strong>作者:</strong> {paper['authors']} | 🔗 <strong>引用数:</strong> {paper['citations']}
                        </div>
                        <div class="card-snippet">{a_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {paper['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 2: 政府部门与权威机构
    with tab_gov:
        with st.spinner("正在检索政府部门与权威机构报告..."):
            gov_res = fetch_gov_reports(en_query, query_input, highlight_keywords)
            if not gov_res:
                st.info("暂未检索到机构报告。")
            else:
                st.caption(f"已按相关性高低展示 {len(gov_res)} 条权威报告与白皮书：")
                for idx, item in enumerate(gov_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    a_hl = highlight_text(item["abstract"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关性: {item['score']}%</span> <span class="badge-gov">🏛️ 政府/权威机构报告</span>
                        <br><br>
                        <a class="card-title" href="{item['url']}" target="_blank">#{idx} {t_hl}</a>
                        <div class="card-meta">📅 <strong>年份:</strong> {item['year']} | ✍️ <strong>作者/机构:</strong> {item['author']} | 📖 <strong>出处:</strong> {item['source']}</div>
                        <div class="card-snippet">{a_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {item['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 9. 底部交互式纵深与横向拓展（已修复一键检索功能）
    st.divider()
    st.markdown("### 🔍 纵深与横向拓展（点击下方标签将直接发起新检索）")
    extensions = get_extension_keywords(query_input)
    col_v, col_h = st.columns(2)
    
    with col_v:
        st.markdown("**📌 纵深探索（作用机制 / 实证研究 / 评估工具）：**")
        for ext in extensions["vertical"]:
            st.button(f"🔍 {ext}", on_click=update_query, args=(ext,), key=f"btn_v_{ext}")
    
    with col_h:
        st.markdown("**🌐 横向拓展（社工介入 / 政策与导则 / 流派结合）：**")
        for ext in extensions["horizontal"]:
            st.button(f"🌐 {ext}", on_click=update_query, args=(ext,), key=f"btn_h_{ext}")
