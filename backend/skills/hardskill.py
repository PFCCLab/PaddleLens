import os
import json
import math
import logging
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from wordcloud import WordCloud
from io import BytesIO

from utils.extension_to_language import extension_to_language
from utils.get_module_weights import module_weights

logging.basicConfig(
    format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def plot_lang_skills(lang_counts: dict) -> go.Figure:
    """
    绘制编程语言使用能力的条形图
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(lang_counts.keys() if lang_counts else ['None']),
        y=list(lang_counts.values() if lang_counts else [0]),
        marker=dict(color="#75B8D7"),
        width=[0.4] * len(lang_counts)
    ))
    fig.update_layout(
        # title=f"Programming Language Skills",
        xaxis_title="Programming Language",
        yaxis=dict(
            range=[0, None],    # 从0开始
        ),
        yaxis_title="Language Usage Score",
        template="plotly_white"
    )
    return fig

def plot_domain_skills(domains: dict) -> bytes:
    """
    绘制领域能力的词云图
    """
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(domains)
    buf = BytesIO()
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    # plt.title("Domain Skills", fontsize=20)
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=150)
    plt.close()
    buf.seek(0)  # 重置指针
    return buf.read()

def plot_pr_types(pr_type_origin: dict, pr_type_weights: dict) -> go.Figure:
    """
    绘制PR类型的条形图，画在同一张图中
    """
    x = list(pr_type_origin.keys())
    y_count = list(pr_type_origin.values())
    y_score = [pr_type_weights.get(k, 0) for k in x]  # 保证顺序一致
    colors = [
        '#66c2a5',
        '#fc8d62',
        '#8da0cb',
        '#e78ac3',
        '#a6d854',
        '#ffd92f',
        '#e5c494'
    ]

    fig = go.Figure()

    # 第一个图：PR数量
    fig.add_trace(go.Bar(
        x=x,
        y=y_count,
        name="PR Count",
        marker_color=colors,
        visible=True
    ))
    # 第二个图：PR权重
    fig.add_trace(go.Bar(
        x=x,
        y=y_score,
        name="PR Score",
        marker_color=colors,
        visible=False
    ))
    # 两个图用按钮切换
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.5, y=1.15,
                showactive=True,
                buttons=[
                    dict(label="PR Count",
                         method="update",
                         args=[{"visible": [True, False]},
                               {"title": f"PR Count by Type",
                                "yaxis": {"title": "Count"}}]),

                    dict(label="PR Score",
                         method="update",
                         args=[{"visible": [False, True]},
                               {"title": f"PR Score by Type",
                                "yaxis": {"title": "Weight"}}])
                ]
            )
        ],
        xaxis_title="PR Type",
        yaxis=dict(range=[0, None]),
        template='plotly_white',
        height=600
    )
    return fig

# 编程语言使用能力
def language_skill(task_name: str, nowdate: datetime) -> go.Figure:
    """
    统计用户的编程语言使用情况
    """

    # 加载扩展名 -> 语言 的映射
    ext_to_lang = extension_to_language()

    # 获取commit修改文件的编程语言
    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "commits.json", 'r', encoding='utf-8') as f:
        commits = json.load(f)
    lang_counts = {}
    for commit in commits:
        files = commit['files']
        weight = 0.2 + 0.8 / (nowdate.year - datetime.fromisoformat(commit['created_at']).year + 1) # 用艾斯宾遗忘曲线计算权重
        for file_obj in files:
            filename = file_obj['filename']
            ext = os.path.splitext(filename)[1]
            if ext == '':
                continue
            lang = ext_to_lang.get(ext, 'Others')
            lang_counts[lang] = weight if lang not in lang_counts else lang_counts[lang] + weight

    # 排序，但'Others'放在最后
    lang_counts = dict(sorted(lang_counts.items(), key=lambda x: x[1], reverse=True))
    if 'Others' in lang_counts:
        others_count = lang_counts.pop('Others')
        lang_counts['Others'] = others_count
    # print(f"Language counts: {lang_counts}")

    # 绘制条形图
    fig = plot_lang_skills(lang_counts)
    
    return fig

# 领域能力
def domain_skill(task_name: str) -> bytes:
    """
    统计用户的领域能力
    """
    # 读取paddle相关repo及其领域
    with open("data/paddle_repos.json", 'r', encoding='utf-8') as f:
        paddle_repos = json.load(f)
    paddle_domains = {}
    for repo in paddle_repos:
        paddle_domains[repo['full_name']] = repo.get('topics', []) + repo.get('domain', '').split(', ')
        
    # 提取用户贡献过commit的repo
    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "commits.json", 'r', encoding='utf-8') as f:
        commits = json.load(f)
    repos = []
    for commit in commits:
        if commit['repo'] not in repos:
            repos.append(commit['repo'])

    # 统计领域
    domains = {}
    for repo in repos:
        domain = paddle_domains.get(repo, '')
        for d in domain:
            if d not in domains:
                domains[d] = 1
            else:
                domains[d] += 1
    if not domains:
        domains = {'None': 1}

    # 绘制词云图
    buf = plot_domain_skills(domains)

    return buf

# 问题解决能力
def problem_solving_skill(task_name: str) -> tuple[float, go.Figure]:
    """
    用户的问题解决能力，考虑 1）项目难度 2）贡献重要度 3）贡献类型
    """

    # 获取项目模块及模块修改数
    m_w_dic = module_weights()

    # print("Calculating pr weights...")
    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "prs.json", 'r', encoding='utf-8') as f:
        prs = json.load(f)
    prs = [pr for pr in prs if pr['merged'] == True]  # 只考虑已合并的PR
    pr_weights = {}
    for pr in prs:
        if pr['repo'] not in pr_weights:
            pr_weights[pr['repo']] = {}
        # 1.项目难度
        p_w = math.log10(int(pr['number']) + 1)/10 # 项目大小作为难度指标
        # 2.贡献重要度
        # 1）loc
        loc = math.log10(pr['additions'] + pr['deletions'] + 1)
        # 2）模块重要度
        repo_full_name = pr['repo']
        modules = m_w_dic.get(repo_full_name, {})
        m_w = 0
        files = pr['files']
        for file in files:
            filename = file['filename']
            parts = filename.split('/')
            # 只取前两级目录作为模块名 eg: src/module1/file.py -> src/module1
            if len(parts) > 2:
                module = '/'.join(parts[:2])
            else:
                module = parts[0]
            weight = modules.get(module, 0)
            m_w += weight
        m_w = m_w / len(files) if files else 0  # 平均模块重要度
        pr_weights[repo_full_name][pr['number']] =  m_w * p_w * loc
    # 3.pr类型
    pr_types = ['Bug fix', 'Documentation', 'Test', 'Build', 'Enhancement', 'New feature', 'Others']
    pr_type_origin = {p: 0 for p in pr_types} # 统计每种类型的pr数量
    pr_type_weights = {ptype: 0 for ptype in pr_types} # 统计每种类型的pr权重总和
    for pr in prs:
        repo_full_name = pr['repo']
        pr_weight = pr_weights[repo_full_name].get(pr['number'], 0)
        pr_type = pr["type"]
        if pr_type in pr_type_weights:
            pr_type_origin[pr_type] += 1
            pr_type_weights[pr_type] += pr_weight
        else:
            pr_type_origin['Others'] += 1
            pr_type_weights['Others'] += pr_weight

    # 最终问题解决能力分数和绘图
    total_score = sum(pr_type_weights.values())
    fig = plot_pr_types(pr_type_origin, pr_type_weights)

    return total_score, fig

def hardskill(task_name: str, nowdate: datetime) -> tuple[go.Figure, bytes, float, go.Figure]:
    """
    用户的硬技能分析
    """
    logging.info(f"Analyzing hardskills for task: {task_name}")
    # 1.编程语言使用能力
    fig_lang_skill = language_skill(task_name, nowdate)

    # 2.领域能力
    fig_domain_skill_bytes = domain_skill(task_name)

    # 3.问题解决能力
    solving_score, fig_solving_skill = problem_solving_skill(task_name)

    return fig_lang_skill, fig_domain_skill_bytes, solving_score, fig_solving_skill

if __name__ == "__main__":

    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.WARNING,
    )
    logger = logging.getLogger(__name__)

    # 计时
    start_time = datetime.now()

    # username = 'dune0310421'
    username = 'Aurelius84'

    fig1, fig2_bytes, solving_score, fig3 = hardskill(username, datetime(2025, 6, 30, tzinfo=None))
    fig1.write_html(Path("cache") / username / "lang_skill.html")
    with open(Path("cache") / username / "domain_skills.png", 'wb') as f:
        f.write(fig2_bytes)
    fig3.write_html(Path("cache") / username / "solving_skill.html")
    print(f"Problem Solving Skill Score: {solving_score}")

    end_time = datetime.now()
    print(f"Time taken: {end_time - start_time}")