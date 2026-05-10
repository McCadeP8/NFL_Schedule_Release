import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="McCade Pearson | Analytics Engineer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Professional Color Palette ────────────────────────────────────────────────
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F8F9FA"
MEDIUM_GRAY = "#6B7280"
DARK_GRAY = "#1F2937"
SUBTLE_BLUE = "#3E92CC"

# ── Clean Professional CSS ────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {WHITE};
        color: {DARK_GRAY};
    }}

    [data-testid="stMainBlockContainer"] {{
        background-color: {WHITE};
        padding: 0;
        max-width: 1200px;
        margin: 0 auto;
    }}

    .header-section {{
        padding: 4rem 2rem;
        text-align: center;
        background: linear-gradient(135deg, {WHITE} 0%, {LIGHT_GRAY} 100%);
        border-bottom: 1px solid #E5E7EB;
    }}

    h1 {{
        color: {DARK_GRAY};
        font-size: 3em;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }}

    .subtitle {{
        color: {MEDIUM_GRAY};
        font-size: 1.2em;
        font-weight: 400;
        margin: 0.5rem 0 0 0;
    }}

    .headshot {{
        width: 140px;
        height: 140px;
        border-radius: 8px;
        margin: 1.5rem 0 0 0;
        object-fit: cover;
        border: 1px solid #E5E7EB;
    }}

    h2 {{
        color: {DARK_GRAY};
        font-size: 1.8em;
        font-weight: 600;
        margin: 2.5rem 0 1.5rem 0;
        letter-spacing: -0.01em;
        padding: 0 2rem;
    }}

    p {{
        color: {MEDIUM_GRAY};
        font-size: 1.05em;
        line-height: 1.7;
        margin: 0 2rem;
    }}

    .content-wrapper {{
        padding: 0 2rem;
    }}

    .project-card {{
        background: {WHITE};
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 2rem;
        margin: 1.5rem 0;
        transition: all 0.3s ease;
    }}

    .project-card:hover {{
        border-color: {SUBTLE_BLUE};
        box-shadow: 0 4px 12px rgba(62, 146, 204, 0.08);
    }}

    .project-title {{
        color: {DARK_GRAY};
        font-size: 1.3em;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }}

    .project-desc {{
        color: {MEDIUM_GRAY};
        font-size: 1em;
        line-height: 1.6;
        margin: 0.75rem 0;
    }}

    .rating {{
        color: {SUBTLE_BLUE};
        font-weight: 600;
        font-size: 0.95em;
        margin-top: 1rem;
        display: inline-block;
    }}

    .project-link {{
        color: {SUBTLE_BLUE};
        text-decoration: none;
        font-weight: 500;
        font-size: 0.95em;
        margin-top: 1rem;
        display: inline-block;
        transition: all 0.2s ease;
    }}

    .project-link:hover {{
        color: {DARK_GRAY};
        text-decoration: underline;
    }}

    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }}

    .stat-box {{
        text-align: center;
        padding: 1.5rem;
        background: {LIGHT_GRAY};
        border-radius: 8px;
        border: 1px solid #E5E7EB;
    }}

    .stat-number {{
        color: {SUBTLE_BLUE};
        font-size: 2em;
        font-weight: 700;
        margin: 0;
    }}

    .stat-label {{
        color: {MEDIUM_GRAY};
        font-size: 0.95em;
        margin-top: 0.5rem;
        font-weight: 500;
    }}

    .divider {{
        border: none;
        border-top: 1px solid #E5E7EB;
        margin: 3rem 2rem;
    }}

    .contact-section {{
        background: {LIGHT_GRAY};
        padding: 3rem 2rem;
        text-align: center;
        margin-top: 2rem;
    }}

    .contact-buttons {{
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 1.5rem;
    }}

    .contact-link {{
        display: inline-block;
        color: {DARK_GRAY};
        text-decoration: none;
        padding: 0.8rem 1.8rem;
        background: {WHITE};
        border: 1.5px solid {SUBTLE_BLUE};
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.95em;
        transition: all 0.3s ease;
    }}

    .contact-link:hover {{
        background: {SUBTLE_BLUE};
        color: {WHITE};
    }}

    .download-btn {{
        color: {DARK_GRAY};
        text-decoration: none;
        padding: 0.8rem 1.8rem;
        background: {WHITE};
        border: 1.5px solid {SUBTLE_BLUE};
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.95em;
        transition: all 0.3s ease;
        display: inline-block;
        cursor: pointer;
    }}

    .download-btn:hover {{
        background: {SUBTLE_BLUE};
        color: {WHITE};
    }}

    .footer {{
        text-align: center;
        color: {MEDIUM_GRAY};
        font-size: 0.9em;
        padding: 2rem;
        border-top: 1px solid #E5E7EB;
    }}

    /* Streamlit tweaks */
    [data-testid="stMarkdownContainer"] {{
        color: {DARK_GRAY};
    }}

    a {{
        color: {SUBTLE_BLUE};
    }}

    button {{
        border-radius: 6px;
        border: 1.5px solid {SUBTLE_BLUE};
        color: {DARK_GRAY};
        background: {WHITE};
        transition: all 0.3s ease;
        font-weight: 500;
    }}

    button:hover {{
        background: {SUBTLE_BLUE};
        color: {WHITE};
    }}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='header-section'>
    <h1>McCade Pearson</h1>
    <p class='subtitle'>Analytics Engineer & Data Scientist</p>
""", unsafe_allow_html=True)

headshot_path = Path("C:/Users/mppac/Downloads/headshot.jpg")
if headshot_path.exists():
    st.image(str(headshot_path), width=140, caption="")

st.markdown("</div>", unsafe_allow_html=True)

# ── About Section ─────────────────────────────────────────────────────────────
st.markdown("""
<div class='content-wrapper'>

## About

I'm an analytics engineer who specializes in building production-grade data tools and interactive dashboards
that drive informed decision-making. My expertise spans full-stack analytics—from backend data pipelines to
user-facing applications—with a focus on sports analytics, predictive modeling, and real-time data systems.

I build with **Streamlit**, **Python**, **R**, **SQL**, and cloud platforms. I believe in clean code,
thoughtful design, and analytics that solve real problems.

""", unsafe_allow_html=True)

# ── Stats Section ─────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(f"""
    <div class='stat-box'>
        <div class='stat-number'>7+</div>
        <div class='stat-label'>Live Projects</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='stat-box'>
        <div class='stat-number'>5K+</div>
        <div class='stat-label'>Hours Built</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='stat-box'>
        <div class='stat-number'>2M+</div>
        <div class='stat-label'>Queries Optimized</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class='stat-box'>
        <div class='stat-number'>∞</div>
        <div class='stat-label'>mg Caffeine Daily</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Projects Data ─────────────────────────────────────────────────────────────
PROJECTS = [
    {
        "title": "SBC Cap Sheets",
        "url": "https://sbc-cap-sheets.streamlit.app/",
        "rating": "10/10",
        "description": "Comprehensive fantasy basketball league management platform. Features live stat aggregation, team salary cap tracking, draft history, contract management, trade simulator, and advanced team analytics. Built with real-time data pipelines and custom metrics.",
    },
    {
        "title": "NFL Schedule Dashboard",
        "url": "https://nfl-schedule.streamlit.app/",
        "rating": "9/10",
        "description": "Production analytics dashboard displaying complete NFL schedules with travel analytics, venue information, and temporal distribution. Includes interactive filtering and geospatial analysis of team locations.",
    },
    {
        "title": "NBA Draft Lottery Calculator",
        "url": "https://nba-lottery-odds.streamlit.app/",
        "rating": "9/10",
        "description": "Interactive probabilistic simulator for NBA Draft Lottery scenarios. Implements pick protections, conditional probability calculations, and dynamic scenario analysis across 24K+ lottery combinations.",
    },
    {
        "title": "Fantasy Hoops Committee Tool",
        "url": "https://fantasy-hoops-cross.streamlit.app/",
        "rating": "8/10",
        "description": "Decision support system for league committee evaluations. Enables side-by-side player resume comparison with weighted metrics and collaborative voting frameworks.",
    },
    {
        "title": "March Madness Pool Tracker",
        "url": "https://kirk-march-madness.streamlit.app/",
        "rating": "8/10",
        "description": "Bracket pool management system with custom scoring engine. Tracks predictions, calculates expected value metrics, and measures game leverage to optimize bracket performance.",
    },
    {
        "title": "Bracket Optimizer",
        "url": "https://mccadep8r.shinyapps.io/March_Madness_2024/",
        "rating": "7/10",
        "description": "Shiny application for data-driven bracket selection. Integrates pool odds, custom scoring logic, and predictive models to recommend optimal bracket configurations.",
    },
    {
        "title": "Voronoi Spatial Analysis",
        "url": "https://mccadep8.github.io/Portfolio/Voronoi_Example.html",
        "rating": "7/10",
        "description": "Interactive geospatial visualization using Voronoi partitioning and KMeans clustering. Maps player influence and court dominance patterns through computational geometry.",
    },
]

# ── Projects Section ──────────────────────────────────────────────────────────
st.markdown("## Projects", unsafe_allow_html=True)

st.markdown("<div class='content-wrapper'>", unsafe_allow_html=True)

for project in PROJECTS:
    st.markdown(f"""
    <div class='project-card'>
        <div class='project-title'>{project['title']}</div>
        <div class='project-desc'>{project['description']}</div>
        <div class='rating'>★ {project['rating']}</div>
        <a href='{project['url']}' target='_blank' class='project-link'>View Project →</a>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Contact Section ───────────────────────────────────────────────────────────
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

resume_path = Path("C:/Users/mppac/Downloads/McCade_Pearson_Resume.pdf")
if resume_path.exists():
    with open(resume_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="📥 Download Resume",
            data=pdf_bytes,
            file_name="McCade_Pearson_Resume.pdf",
            mime="application/pdf",
        )
    with col2:
        pass
    with col3:
        pass

st.markdown("""
<div class='contact-section'>
    <h2 style='margin-top: 0; padding: 0;'>Let's Connect</h2>
    <p style='margin-bottom: 1.5rem; padding: 0;'>Open to interesting projects and collaboration opportunities.</p>
    <div class='contact-buttons'>
        <a href='https://github.com/mccadep8' target='_blank' class='contact-link'>GitHub</a>
        <a href='https://linkedin.com/in/mccade-pearson' target='_blank' class='contact-link'>LinkedIn</a>
        <a href='mailto:mccade.pearson@gmail.com' class='contact-link'>Email</a>
    </div>
</div>

<div class='footer'>
    <p>Built with Streamlit • Designed for clarity and impact</p>
</div>
""", unsafe_allow_html=True)
