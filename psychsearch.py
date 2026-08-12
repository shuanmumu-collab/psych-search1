import streamlit as st
import requests
import re
from urllib.parse import quote_plus, unquote
from bs4 import BeautifulSoup

# 1. 页面基础配置
st.set_page_config(
    page_title="心理学、心理咨询与社工学术搜索引擎",
    page_icon="🧠",
    layout="wide"
)

# 2. 自定义 CSS 样式（包含新标签页链接按钮样式）
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
    .badge-score {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
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
    .badge-gov {
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-book {
        background-color: #f3e8ff;
        color: #6b21a8;
        border: 1px solid #e9d5ff;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-media {
        background-color: #ffe4e6;
        color: #9f1239;
        border: 1px solid #fecdd3;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
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
    .ext-link-btn {
        display: inline-block;
        background-color: #f1f5f9;
        color: #0f172a !important;
        border: 1px solid #cbd5e1;
        padding: 8px 14px;
        margin: 4px;
        border-radius: 20px;
        text-decoration: none !important;
        font-size: 13px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .ext-link-btn:hover {
        background-color: #e2e8f0;
        border-color: #94a3b8;
        color: #1e40af !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. 支持 URL 搜索参数（方便在新标签页打开搜索结果）
query_params = st.query_params
url_query = query_params.get("q", "")

if "search_query" not in st.session_state:
    st.session_state["search_query"] = url_query
elif url_query and st.session_state["search_query"] != url_query:
    st.session_state["search_query"] = url_query

# 4. 专业中英及同义词字典
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

def translate_and_expand_query(user_input: str):
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

def calculate_scientific_relevance(title: str, text: str, raw_query: str, highlight_terms: list, is_open_access=False, source_type="general"):
    """科学多维度匹配度计算模型"""
    title_lower = title.lower()
    text_lower = (text or "").lower()
    raw_lower = raw_query.lower()
    
    score = 50  # 基础分（只要包含关键词即进入计算）
    reasons = []

    # 1. 标题权重判定 (最高 +25%)
    if raw_lower in title_lower:
        score += 25
        reasons.append("标题精确包含检索词 (+25%)")
    else:
        title_term_hits = [t for t in highlight_terms if len(t) > 2 and t.lower() in title_lower]
        if title_term_hits:
            score += 18
            reasons.append(f"标题命中相关术语 '{title_term_hits[0]}' (+18%)")

    # 2. 摘要/正文关键词与近义词密度判定 (最高 +16%)
    text_hits = 0
    for term in highlight_terms:
        if len(term) > 2:
            text_hits += len(re.findall(re.escape(term.lower()), text_lower))
    
    if text_hits > 0:
        hit_score = min(text_hits * 4, 16)
        score += hit_score
        reasons.append(f"摘要/内容出现 {text_hits} 次关键词/近义词 (+{hit_score}%)")

    # 3. 免费全文/开放获取加分 (+5%)
    if is_open_access:
        score += 5
        reasons.append("支持免费全文阅读 (+5%)")
        
    # 4. 权威机构/百科来源加分 (+4%)
    if source_type in ["gov", "wiki", "book"]:
        score += 4
        reasons.append("来源于权威学术/公共数据库 (+4%)")

    final_score = min(max(score, 60), 99)
    reason_str = " | ".join(reasons) if reasons else "领域内容相关"
    return final_score, reason_str

def highlight_text(text: str, terms: list) -> str:
    if not text:
        return "暂无详细摘要/内容介绍"
    for term in terms:
        if not term or len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', text)
    return text

# --- 数据抓取模块（海量 50+ 结果） ---

# 1. 权威百科与科普网站 (50+ 结果)
def fetch_pop_and_wiki(en_query: str, raw_query: str, highlight_terms: list):
    results = []
    seen_urls = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Wikipedia 多词条 (10 条)
    try:
        wiki_api = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(en_query)}&format=json&utf8=1&srlimit=15"
        res = requests.get(wiki_api, headers=headers, timeout=5)
        if res.status_code == 200:
            for w in res.json().get("query", {}).get("search", []):
                p_title = w.get("title")
                snippet = re.sub('<[^<]+?>', '', w.get("snippet", "")) + "..."
                page_url = f"https://en.wikipedia.org/wiki/{quote_plus(p_title)}"
                if page_url not in seen_urls:
                    seen_urls.add(page_url)
                    score, reason = calculate_scientific_relevance(p_title, snippet, raw_query, highlight_terms, source_type="wiki")
                    results.append({
                        "title": f"Wikipedia: {p_title}",
                        "snippet": snippet,
                        "url": page_url,
                        "source": "Wikipedia 维基百科",
                        "score": score,
                        "reason": reason
                    })
    except Exception:
        pass

    # 大众科普与知识导读网站 (目标 40+ 条)
    try:
        ddg_url = "https://html.duckduckgo.com/html/"
        res = requests.post(ddg_url, data={"q": f"{en_query} psychology OR counselling OR mental health"}, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.find_all("div", class_="result"):
                a_title = div.find("a", class_="result__a")
                a_snippet = div.find("a", class_="result__snippet")
                a_url = div.find("a", class_="result__url")
                if a_title:
                    title = a_title.text.strip()
                    raw_link = a_title.get("href", "")
                    actual_link = unquote(raw_link.split("uddg=")[1].split("&")[0]) if "uddg=" in raw_link else raw_link
                    
                    if actual_link in seen_urls:
                        continue
                    seen_urls.add(actual_link)

                    snippet = a_snippet.text.strip() if a_snippet else "暂无描述"
                    source_domain = a_url.text.strip() if a_url else "Web Resource"
                    
                    score, reason = calculate_scientific_relevance(title, snippet, raw_query, highlight_terms)
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "url": actual_link,
                        "source": source_domain,
                        "score": score,
                        "reason": reason
                    })
                    if len(results) >= 50:
                        break
    except Exception:
        pass

    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# 2. 政府报告与权威图书 (各 50+ 结果)
def fetch_openalex_gov_and_books(en_query: str, raw_query: str, highlight_terms: list):
    gov_results = []
    book_results = []
    headers = {"User-Agent": "PsychologyAcademicSearch/1.0 (mailto:researcher@example.com)"}
    
    try:
        url = f"https://api.openalex.org/works?search={quote_plus(en_query)}&per_page=50&sort=relevance_score:desc"
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            for item in res.json().get("results", []):
                title = item.get("display_name", "Untitled")
                doi_url = item.get("doi") or item.get("id")
                pub_year = item.get("publication_year", "N/A")
                doc_type = item.get("type", "")
                
                abstract_inverted = item.get("abstract_inverted_index")
                abstract = ""
                if abstract_inverted:
                    word_list = []
                    for word, pos_list in abstract_inverted.items():
                        for pos in pos_list:
                            word_list.append((pos, word))
                    word_list.sort()
                    abstract = " ".join([w[1] for w in word_list[:120]]) + "..."
                
                source_name = item.get("primary_location", {}).get("source", {}).get("display_name", "权威机构/数据库")
                authorships = item.get("authorships", [])
                authors = [a.get("author", {}).get("display_name") for a in authorships[:3]]
                author_str = ", ".join(filter(None, authors)) or "权威机构/学者"

                score, reason = calculate_scientific_relevance(title, abstract, raw_query, highlight_terms, source_type="gov")

                card_data = {
                    "title": title,
                    "url": doi_url,
                    "year": pub_year,
                    "author": author_str,
                    "source": source_name,
                    "abstract": abstract or "包含核心概念的权威学术文献/报告。",
                    "score": score,
                    "reason": reason
                }

                if doc_type in ["book", "book-chapter"]:
                    book_results.append(card_data)
                else:
                    gov_results.append(card_data)
    except Exception:
        pass
        
    gov_results.sort(key=lambda x: x["score"], reverse=True)
    book_results.sort(key=lambda x: x["score"], reverse=True)
    return gov_results, book_results

# 3. 音视频讲座与播客 (30+ 结果)
def fetch_audio_media(en_query: str, raw_query: str, highlight_terms: list):
    media_results = []
    try:
        url = f"https://itunes.apple.com/search?term={quote_plus(en_query + ' psychology counselling')}&entity=podcastEpisode&limit=30"
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            for item in res.json().get("results", []):
                title = item.get("trackName", "Untitled Episode")
                snippet = item.get("description", "暂无剧集简介")[:200] + "..."
                score, reason = calculate_scientific_relevance(title, snippet, raw_query, highlight_terms)
                
                media_results.append({
                    "title": title,
                    "artist": item.get("artistName", "Expert/Host"),
                    "collection": item.get("collectionName", "Academic Podcast"),
                    "url": item.get("trackViewUrl") or item.get("collectionViewUrl"),
                    "snippet": snippet,
                    "date": item.get("releaseDate", "")[:10],
                    "score": score,
                    "reason": reason
                })
    except Exception:
        pass
    media_results.sort(key=lambda x: x["score"], reverse=True)
    return media_results

# 4. 免费核心学术论文 (50+ 结果)
def fetch_academic_papers(en_query: str, raw_query: str, highlight_terms: list):
    formatted = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(en_query)}&format=json&pageSize=50"
        res = requests.get(pmc_url, headers=headers, timeout=8)
        if res.status_code == 200:
            for item in res.json().get("resultList", {}).get("result", []):
                doi = item.get("doi")
                pmcid = item.get("pmcid")
                
                is_free = False
                if pmcid:
                    download_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
                    is_free = True
                elif doi:
                    download_url = f"https://doi.org/{doi}"
                    is_free = item.get("isOpenAccess") == "Y"
                else:
                    download_url = f"https://europepmc.org/article/MED/{item.get('id')}"

                title = item.get("title", "Untitled Paper")
                abstract = item.get("abstractText", "")
                author_str = item.get("authorString", "")
                authors = ", ".join([a.strip() for a in author_str.split(",")[:3]]) if author_str else "Unknown"
                
                score, reason = calculate_scientific_relevance(title, abstract, raw_query, highlight_terms, is_open_access=is_free)

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

    formatted.sort(key=lambda x: (x["score"], x["is_free"]), reverse=True)
    return formatted

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

# --- 界面主逻辑 ---
st.title("🧠 Psychology, Counselling & Social Work Search Engine")
st.caption("私人学术搜索引擎 | 5大全维知识分类 · 海量50+展示 · 科学相关度评分 · 新标签页拓展")

# 搜索框
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
            st.markdown(f'💡 **自动匹配近义/同义术语:** `{", ".join(matched_synonyms)}`')
    with col_b:
        st.success("已开启无广告与全域宽泛匹配")

    # 还原并扩展为完整的 5 大分类 Tabs
    tab_pop, tab_gov, tab_books, tab_media, tab_academic = st.tabs([
        "📖 权威百科/科普/知识介绍", 
        "🏛️ 政府部门/智库/权威报告", 
        "📚 知名学者著作/专业图书", 
        "🎙️ 专家讲座/学术播客/音视频", 
        "🎓 核心学术论文 (免费全文优先)"
    ])

    # Tab 1: 百科与科普知识网站
    with tab_pop:
        with st.spinner("正在检索权威百科与科普资源 (至多 50+ 条)..."):
            pop_res = fetch_pop_and_wiki(en_query, query_input, highlight_keywords)
            if not pop_res:
                st.info("暂未检索到科普网页，请查看其他标签页。")
            else:
                st.caption(f"已为你展示按匹配度排序的 {len(pop_res)} 条百科与科普知识：")
                for idx, item in enumerate(pop_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    s_hl = highlight_text(item["snippet"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关度: {item['score']}%</span> <span class="badge-pop">🌐 百科 / 科普导读</span>
                        <br><br>
                        <a class="card-title" href="{item['url']}" target="_blank">#{idx} {t_hl}</a>
                        <div class="card-meta">🔗 <strong>来源:</strong> {item['source']}</div>
                        <div class="card-snippet">{s_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {item['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 2: 政府与权威机构报告
    with tab_gov:
        with st.spinner("正在检索政府与智库机构研究报告 (至多 50+ 条)..."):
            gov_res, _ = fetch_openalex_gov_and_books(en_query, query_input, highlight_keywords)
            if not gov_res:
                st.info("暂未检索到机构报告。")
            else:
                st.caption(f"已为你展示 {len(gov_res)} 条权威报告与白皮书：")
                for idx, item in enumerate(gov_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    a_hl = highlight_text(item["abstract"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关度: {item['score']}%</span> <span class="badge-gov">🏛️ 政府/智库报告</span>
                        <br><br>
                        <a class="card-title" href="{item['url']}" target="_blank">#{idx} {t_hl}</a>
                        <div class="card-meta">📅 <strong>年份:</strong> {item['year']} | ✍️ <strong>作者/机构:</strong> {item['author']} | 📖 <strong>出处:</strong> {item['source']}</div>
                        <div class="card-snippet">{a_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {item['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 3: 学者著作与学术图书
    with tab_books:
        with st.spinner("正在检索学术图书与专业专著 (至多 50+ 条)..."):
            _, book_res = fetch_openalex_gov_and_books(en_query, query_input, highlight_keywords)
            if not book_res:
                st.info("暂未检索到书籍专著。")
            else:
                st.caption(f"已为你展示 {len(book_res)} 部学术著作与专业图书：")
                for idx, item in enumerate(book_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    a_hl = highlight_text(item["abstract"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关度: {item['score']}%</span> <span class="badge-book">📚 学术专著/图书</span>
                        <br><br>
                        <a class="card-title" href="{item['url']}" target="_blank">#{idx} {t_hl}</a>
                        <div class="card-meta">📅 <strong>年份:</strong> {item['year']} | ✍️ <strong>作者:</strong> {item['author']} | 📖 <strong>出版方:</strong> {item['source']}</div>
                        <div class="card-snippet">{a_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {item['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 4: 音视频与讲座
    with tab_media:
        with st.spinner("正在检索专家讲座与学术音频..."):
            media_res = fetch_audio_media(en_query, query_input, highlight_keywords)
            if not media_res:
                st.info("暂未检索到音频讲座。")
            else:
                st.caption(f"已为你找到 {len(media_res)} 个专家访谈与学术讲座音频：")
                for idx, item in enumerate(media_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    s_hl = highlight_text(item["snippet"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关度: {item['score']}%</span> <span class="badge-media">🎙️ 音视频/专家讲座</span>
                        <br><br>
                        <a class="card-title" href="{item['url']}" target="_blank">#{idx} {t_hl}</a>
                        <div class="card-meta">🎙️ <strong>节目/讲座源:</strong> {item['collection']} | ✍️ <strong>主讲人:</strong> {item['artist']} | 📅 <strong>日期:</strong> {item['date']}</div>
                        <div class="card-snippet">{s_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {item['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 5: 核心学术论文
    with tab_academic:
        with st.spinner("正在检索核心学术期刊论文 (至多 50+ 篇)..."):
            papers = fetch_academic_papers(en_query, query_input, highlight_keywords)
            if not papers:
                st.info("暂未检索到相关论文。")
            else:
                st.caption(f"已为你展示 {len(papers)} 篇核心期刊论文（免费全文优先排序）：")
                for idx, paper in enumerate(papers, start=1):
                    t_hl = highlight_text(paper["title"], highlight_keywords)
                    a_hl = highlight_text(paper["abstract"], highlight_keywords)
                    free_badge = '<span class="badge-oa">🔓 免费全文阅读/下载</span>' if paper["is_free"] else ''
                    
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-score">🎯 相关度: {paper['score']}%</span> {free_badge}
                        <br><br>
                        <a class="card-title" href="{paper['url']}" target="_blank">#{idx} 🎓 {t_hl}</a>
                        <div class="card-meta">
                            📅 <strong>年份:</strong> {paper['year']} | 📖 <strong>期刊:</strong> {paper['venue']} | ✍️ <strong>作者:</strong> {paper['authors']} | 🔗 <strong>引用数:</strong> {paper['citations']}
                        </div>
                        <div class="card-snippet">{a_hl}</div>
                        <div class="card-meta" style="color: #059669; margin-top: 6px;">💡 <strong>匹配分析:</strong> {paper['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 底部新标签页拓展区域（在新标签页打开 `target="_blank"`）
    st.divider()
    st.markdown("### 🔍 纵深与横向拓展（点击将在浏览器新标签页发起搜索）")
    extensions = get_extension_keywords(query_input)
    col_v, col_h = st.columns(2)
    
    with col_v:
        st.markdown("**📌 纵深探索（在新标签页打开）：**")
        v_html = "".join([f'<a href="?q={quote_plus(ext)}" target="_blank" class="ext-link-btn">🔍 {ext}</a>' for ext in extensions["vertical"]])
        st.markdown(v_html, unsafe_allow_html=True)
    
    with col_h:
        st.markdown("**🌐 横向拓展（在新标签页打开）：**")
        h_html = "".join([f'<a href="?q={quote_plus(ext)}" target="_blank" class="ext-link-btn">🌐 {ext}</a>' for ext in extensions["horizontal"]])
        st.markdown(h_html, unsafe_allow_html=True)
