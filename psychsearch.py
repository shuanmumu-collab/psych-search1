import streamlit as st
import requests
import re
from urllib.parse import quote_plus

# 页面基础配置
st.set_page_config(
    page_title="心理学与社工无广告学术搜索引擎",
    page_icon="🧠",
    layout="wide"
)

# 样式增强：包含关键词高亮与高品质学术卡片布局
st.markdown("""
<style>
    .paper-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .paper-title {
        font-size: 18px;
        font-weight: 600;
        color: #1e3a8a;
        text-decoration: none;
    }
    .paper-meta {
        font-size: 13px;
        color: #64748b;
        margin: 8px 0;
    }
    .paper-abstract {
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
</style>
""", unsafe_allow_html=True)

# 常见心理学/咨询/社工中英专业词汇自动映射字典
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
    """映射中文输入为专业英文学术检索表达式"""
    english_query = user_input
    for key, val in DICT_MAPPING.items():
        if key in user_input:
            english_query = english_query.replace(key, val)
    
    highlight_terms = [user_input.strip()]
    if english_query != user_input:
        highlight_terms.extend([term for term in english_query.split() if len(term) > 2])
    
    return english_query, list(set(highlight_terms))

def highlight_text(text: str, terms: list) -> str:
    """在文本中自动标黄匹配的关键词"""
    if not text:
        return "暂无摘要 (No abstract available)"
    
    for term in terms:
        if not term or len(term) < 2:
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', text)
    return text

def get_extension_keywords(query_text: str):
    """生成纵深与横向知识拓展词"""
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

def fetch_academic_papers(en_query: str):
    """双源学术引擎拉取（主源 Semantic Scholar + 备用源 Europe PMC）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 尝试主源：Semantic Scholar API
    try:
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(en_query)}&limit=10&fields=title,abstract,url,venue,year,authors,citationCount"
        res = requests.get(api_url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            papers = data.get("data")
            if papers:
                return papers, "Semantic Scholar Academic Database"
    except Exception:
        pass

    # 尝试备用源：Europe PMC Academic API
    try:
        pmc_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quote_plus(en_query)}&format=json&pageSize=10"
        res = requests.get(pmc_url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            result_list = data.get("resultList", {}).get("result", [])
            formatted_papers = []
            for item in result_list:
                doi = item.get("doi")
                url = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/MED/{item.get('id')}"
                author_str = item.get("authorString", "")
                authors = [{"name": a.strip()} for a in author_str.split(",")[:3]] if author_str else []
                
                formatted_papers.append({
                    "title": item.get("title", "Untitled Paper"),
                    "abstract": item.get("abstractText", ""),
                    "url": url,
                    "year": item.get("pubYear", "N/A"),
                    "venue": item.get("journalTitle", "Academic Journal"),
                    "citationCount": item.get("citedByCount", 0),
                    "authors": authors
                })
            if formatted_papers:
                return formatted_papers, "Europe PMC Academic Database (Backup Engine)"
    except Exception:
        pass

    return [], "None"

# --- 界面主逻辑 ---
st.title("🧠 Psychology, Counselling & Social Work Search")
st.caption("无广告学术专用搜索引擎 · 支持中文自动映射专业英文文献 · 自动高亮与知识拓展")

# 搜索框
query_input = st.text_input("输入查询关键词（支持中文或英文）：", placeholder="例如：创伤后应激 认知重塑 或 Attachment Theory in counselling")

if query_input:
    en_query, highlight_keywords = translate_and_expand_query(query_input)
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info(f"**实际检索学术表达式：** `{en_query}`")
    with col_b:
        st.success("已开启 100% 无广告过滤")

    with st.spinner("正在检索学术数据库..."):
        papers, source_engine = fetch_academic_papers(en_query)
        
        if not papers:
            st.warning("未找到匹配文献，请尝试更换关键词。")
        else:
            st.caption(f"数据来源：`{source_engine}` | 共匹配 {len(papers)} 篇学术文献")
            st.markdown("---")
            
            for paper in papers:
                title = paper.get("title", "Untitled Paper")
                abstract = paper.get("abstract", "")
                url = paper.get("url") or f"https://www.google.com/search?q={quote_plus(title)}"
                year = paper.get("year", "N/A")
                venue = paper.get("venue", "Academic Journal")
                citations = paper.get("citationCount", 0)
                authors = ", ".join([a["name"] for a in paper.get("authors", [])[:3]]) if paper.get("authors") else "Unknown"
                
                # 高亮处理
                highlighted_title = highlight_text(title, highlight_keywords)
                highlighted_abstract = highlight_text(abstract, highlight_keywords)
                
                # 卡片渲染
                st.markdown(f"""
                <div class="paper-card">
                    <a class="paper-title" href="{url}" target="_blank">{highlighted_title}</a>
                    <div class="paper-meta">
                        📅 <strong>年份:</strong> {year} | 📖 <strong>期刊/出处:</strong> {venue} | ✍️ <strong>作者:</strong> {authors} | 🔗 <strong>被引次数:</strong> {citations}
                    </div>
                    <div class="paper-abstract">{highlighted_abstract}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- 底部纵深与横向拓展 ---
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
