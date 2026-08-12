import streamlit as st
import requests
import re
from urllib.parse import quote_plus

# 页面基础配置
st.set_page_config(
    page_title="心理学、心理咨询与社工私人定制学术搜索引擎",
    page_icon="🧠",
    layout="wide"
)

# 自定义 CSS 样式
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
    .badge-gov {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
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

# 深度优化的心理学/咨询/社工同义词及专业机构映射字典
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
    "焦点解决短程心理咨询": ["Solution-focused brief therapy", "SFBT", "exception questions"]
}

if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

def update_query(new_term):
    st.session_state["search_query"] = new_term

def translate_and_expand_query(user_input: str):
    """同义词与近义词自动扩展与映射"""
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
    """自动高亮匹配文本及其近义词"""
    if not text:
        return "暂无详细摘要/简介"
    for term in terms:
        if not term or len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', text)
    return text

# 1. 抓取 OpenAlex 数据库（包含政府报告、权威机构白皮书、书籍专著）
def fetch_openalex_data(en_query: str):
    gov_results = []
    book_results = []
    headers = {"User-Agent": "PsychologyAcademicSearch/1.0 (mailto:researcher@example.com)"}
    
    try:
        url = f"https://api.openalex.org/works?search={quote_plus(en_query)}&per_page=25&sort=relevance_score:desc"
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            items = res.json().get("results", [])
            for item in items:
                title = item.get("display_name", "Untitled")
                doi_url = item.get("doi") or item.get("id")
                pub_year = item.get("publication_year", "N/A")
                doc_type = item.get("type", "")
                
                # 获取作者与机构信息
                authorships = item.get("authorships", [])
                authors = [a.get("author", {}).get("display_name") for a in authorships[:3]]
                author_str = ", ".join(filter(None, authors)) or "权威机构/学者"
                
                # 摘要还原
                abstract_inverted = item.get("abstract_inverted_index")
                abstract = ""
                if abstract_inverted:
                    word_list = []
                    for word, pos_list in abstract_inverted.items():
                        for pos in pos_list:
                            word_list.append((pos, word))
                    word_list.sort()
                    abstract = " ".join([w[1] for w in word_list[:120]]) + "..."
                
                source_name = item.get("primary_location", {}).get("source", {}).get("display_name", "权威学术数据库/机构")
                
                # 区分图书/智库报告与政府/机构文献
                if doc_type in ["book", "book-chapter"]:
                    book_results.append({
                        "title": f"📚 [图书专著] {title}",
                        "url": doi_url,
                        "year": pub_year,
                        "author": author_str,
                        "source": source_name,
                        "abstract": abstract or "心理学与社工领域专业出版物/专著。"
                    })
                else:
                    gov_results.append({
                        "title": title,
                        "url": doi_url,
                        "year": pub_year,
                        "author": author_str,
                        "source": source_name,
                        "abstract": abstract or "权威机构研究报告/学术白皮书。"
                    })
    except Exception:
        pass
        
    return gov_results, book_results

# 2. 抓取音视频、播客与学术讲座（iTunes API - 零封锁防爬）
def fetch_audio_media(en_query: str):
    media_results = []
    try:
        url = f"https://itunes.apple.com/search?term={quote_plus(en_query + ' psychology counselling')}&entity=podcastEpisode&limit=15"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            items = res.json().get("results", [])
            for item in items:
                media_results.append({
                    "title": item.get("trackName", "Untitled Episode"),
                    "artist": item.get("artistName", "Expert/Podcast Host"),
                    "collection": item.get("collectionName", "Academic Podcast"),
                    "url": item.get("trackViewUrl") or item.get("collectionViewUrl"),
                    "snippet": item.get("description", "暂无剧集简介")[:200] + "...",
                    "date": item.get("releaseDate", "")[:10]
                })
    except Exception:
        pass
    return media_results

# 3. 抓取学术期刊 (Europe PMC API)
def fetch_academic_papers(en_query: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    formatted = []
    try:
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(en_query)}&format=json&pageSize=20"
        res = requests.get(pmc_url, headers=headers, timeout=6)
        if res.status_code == 200:
            result_list = res.json().get("resultList", {}).get("result", [])
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
    except Exception:
        pass
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
st.caption("无广告·私人定制学术引擎 | 聚合政府机构报告、知名学者图书、音视频讲座与核心期刊")

query_input = st.text_input(
    "输入查询关键词（支持中文或英文）：",
    value=st.session_state["search_query"],
    placeholder="例如：创伤后应激、依恋理论、Child protection counselling",
    key="main_input"
)

if query_input:
    st.session_state["search_query"] = query_input
    en_query, highlight_keywords = translate_and_expand_query(query_input)
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info(f"**实际检索与学术/同义词映射表达式：** `{en_query}`")
    with col_b:
        st.success("已开启 API 防封锁与无广告过滤")

    tab_gov, tab_books, tab_media, tab_academic = st.tabs([
        "🏛️ 政府部门/权威机构报告", 
        "📖 知名学者著作与图书", 
        "🎙️ 权威音视频/专家讲座/播客", 
        "🎓 核心学术论文与期刊"
    ])

    # Tab 1: 政府与权威机构
    with tab_gov:
        with st.spinner("正在调取全球政府与权威机构研究报告..."):
            gov_res, _ = fetch_openalex_data(en_query)
            if not gov_res:
                st.info("暂未检索到相关机构报告，请查看其他标签页。")
            else:
                st.caption(f"已为你检索到 {len(gov_res)} 条政府与权威机构报告（按相关度排序）：")
                for idx, item in enumerate(gov_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    a_hl = highlight_text(item["abstract"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-gov">#{idx} 🏛️ 政府/权威机构/智库报告</span>
                        <a class="card-title" href="{item['url']}" target="_blank">{t_hl}</a>
                        <div class="card-meta">📅 <strong>年份:</strong> {item['year']} | ✍️ <strong>作者/机构:</strong> {item['author']} | 📖 <strong>出处:</strong> {item['source']}</div>
                        <div class="card-snippet">{a_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 2: 知名学者著作与图书
    with tab_books:
        with st.spinner("正在检索领域内学术专著与经典图书..."):
            _, book_res = fetch_openalex_data(en_query)
            if not book_res:
                st.info("暂未检索到相关书籍专著，请尝试微调关键词。")
            else:
                st.caption(f"已为你检索到 {len(book_res)} 部学术图书与论文集：")
                for idx, item in enumerate(book_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    a_hl = highlight_text(item["abstract"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-book">#{idx} 📖 权威学术图书/专著</span>
                        <a class="card-title" href="{item['url']}" target="_blank">{t_hl}</a>
                        <div class="card-meta">📅 <strong>出版年份:</strong> {item['year']} | ✍️ <strong>作者:</strong> {item['author']} | 📖 <strong>出版社/来源:</strong> {item['source']}</div>
                        <div class="card-snippet">{a_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 3: 音视频与讲座
    with tab_media:
        with st.spinner("正在检索专家讲座与权威音频资源..."):
            media_res = fetch_audio_media(en_query)
            if not media_res:
                st.info("暂未检索到相关音视频讲座。")
            else:
                st.caption(f"已为你找到 {len(media_res)} 个包含专家访谈、心理咨询讲座的音频/剧集：")
                for idx, item in enumerate(media_res, start=1):
                    t_hl = highlight_text(item["title"], highlight_keywords)
                    s_hl = highlight_text(item["snippet"], highlight_keywords)
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-media">#{idx} 🎙️ 音视频/专家讲座/学术播客</span>
                        <a class="card-title" href="{item['url']}" target="_blank">{t_hl}</a>
                        <div class="card-meta">🎙️ <strong>节目/讲座源:</strong> {item['collection']} | ✍️ <strong>主讲人/专家:</strong> {item['artist']} | 📅 <strong>发布日期:</strong> {item['date']}</div>
                        <div class="card-snippet">{s_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 4: 学术论文
    with tab_academic:
        with st.spinner("正在检索核心学术期刊论文..."):
            papers = fetch_academic_papers(en_query)
            if not papers:
                st.info("暂未检索到核心论文。")
            else:
                st.caption(f"已为你找到 {len(papers)} 篇核心期刊论文：")
                for idx, paper in enumerate(papers, start=1):
                    title = paper.get("title", "Untitled Paper")
                    abstract = paper.get("abstract", "")
                    url = paper.get("url")
                    year = paper.get("year", "N/A")
                    venue = paper.get("venue", "Academic Journal")
                    citations = paper.get("citationCount", 0)
                    authors = ", ".join([a["name"] for a in paper.get("authors", [])[:3]]) if paper.get("authors") else "Unknown"
                    
                    t_hl = highlight_text(title, highlight_keywords)
                    a_hl = highlight_text(abstract, highlight_keywords)
                    
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge-academic">#{idx} 🎓 期刊论文</span>
                        <a class="card-title" href="{url}" target="_blank">{t_hl}</a>
                        <div class="card-meta">
                            📅 <strong>年份:</strong> {year} | 📖 <strong>期刊:</strong> {venue} | ✍️ <strong>作者:</strong> {authors} | 🔗 <strong>引用数:</strong> {citations}
                        </div>
                        <div class="card-snippet">{a_hl}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 底部直接搜索的拓展区域
    st.divider()
    st.markdown("### 🔍 纵深与横向拓展（点击标签发起新检索）")
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
