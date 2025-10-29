import json
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import logging

logging.basicConfig(
    format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def plot_repo_contrib(df_repo_contrib: pd.DataFrame) -> go.Figure:
    """
    绘制贡献总数前5个仓库的统计图
    """
    colors = {
        'commits': "#81C784",
        'prs': "#4FC3F7",
        'issues': "#F06292",
        'comments': "#FFB74D",
        'reviews': "#A790F9",
    }
    
    df_repo_contrib = df_repo_contrib.sort_values(by="total", ascending=True)
    df_repo_contrib = df_repo_contrib.drop(columns=['total'])
    fig = go.Figure()
    for col in df_repo_contrib.columns:
        fig.add_trace(go.Bar(
            y=df_repo_contrib.index,
            x=df_repo_contrib[col],
            name=col,
            orientation='h',
            marker=dict(color=colors[col]),
            legendrank=5 - list(colors.keys()).index(col) + 1
        ))
    fig.update_layout(
        barmode='stack',
        # title="Top 5 Repository Contributions",
        xaxis_title="Number of Contributions",
        xaxis=dict(range=[0, None]),
        legend_title="Contribution Type",
        template="plotly_white",
        height=400 + len(df_repo_contrib.index) * 20,  # 高度
        margin=dict(l=100, r=40, t=80, b=60),  # 边距
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )
    return fig

def plot_recent_contrib(df_contrib: pd.DataFrame) -> go.Figure:
    """
    绘制最近一年的贡献图
    """
    colors = {
        'commits': "#81C784",
        'prs': "#4FC3F7",
        'issues': "#F06292",
        'comments': "#FFB74D",
        'reviews': "#A790F9",
    }
    df_contrib = df_contrib.drop(columns=['total'])
    fig = go.Figure()
    for col in df_contrib.columns:
        fig.add_trace(go.Scatter(
            x=df_contrib.index,
            y=df_contrib[col],
            mode='lines+markers',
            name=col,
            line=dict(color=colors[col]),
            marker=dict(size=6),
            # legendrank=5 - list(colors.keys()).index(col) + 1
        ))
    fig.update_layout(
        # title="Recent Contributions (Last Year)",
        xaxis_title="Month",
        yaxis_title="Number of Contributions",
        yaxis=dict(
            range=[0, None],    # 从0开始
        ),
        legend_title="Contribution Type",
        template="plotly_white",
        height=500,
        margin=dict(l=60, r=40, t=80, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )
    return fig

def experience(task_name: str, nowdate: datetime) -> tuple[dict, go.Figure, go.Figure]:
    """
    用户的开发经验
    """
    logging.info(f"Analyzing experience for task: {task_name}")
    username = task_name.split("_")[0]  # 从task_name中提取username
    # 读取数据
    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "commits.json", 'r', encoding='utf-8') as f:
        commits = json.load(f)
    with open(user_cache_dir / "prs.json", 'r', encoding='utf-8') as f:
        prs = json.load(f)
    with open(user_cache_dir / "issues.json", 'r', encoding='utf-8') as f:
        issues = json.load(f)
    with open(user_cache_dir / "comment_prs_issues.json", 'r', encoding='utf-8') as f:
        comment_prs_issues = json.load(f)
    with open(user_cache_dir / "review_prs.json", 'r', encoding='utf-8') as f:
        review_prs = json.load(f)
    with open(user_cache_dir / "repos_can_merge.json", 'r', encoding='utf-8') as f:
        repos_can_merge = json.load(f)

    # ---统计贡献总数---
    df_contrib = pd.DataFrame(columns=['commits', 'prs', 'issues', 'comments', 'reviews'], dtype=int)
    for commit in commits:
        repo = commit['repo']
        if repo not in df_contrib.index:
            df_contrib.loc[repo] = [0, 0, 0, 0, 0]
        df_contrib.at[repo, 'commits'] += 1
    for pr in prs:
        repo = pr['repo']
        if repo not in df_contrib.index:
            df_contrib.loc[repo] = [0, 0, 0, 0, 0]
        df_contrib.at[repo, 'prs'] += 1
    for issue in issues:
        repo = issue['repo']
        if repo not in df_contrib.index:
            df_contrib.loc[repo] = [0, 0, 0, 0, 0]
        df_contrib.at[repo, 'issues'] += 1
    for comment in comment_prs_issues:
        repo = comment['repo']
        if repo not in df_contrib.index:
            df_contrib.loc[repo] = [0, 0, 0, 0, 0]
        # cnt = comment.get('comment_by', []).count(username)
        cnt = sum(1 for c in comment.get('comment_by', []) if c[0] == username)
        df_contrib.at[repo, 'comments'] += cnt
    for review in review_prs:
        repo = review['repo']
        if repo not in df_contrib.index:
            df_contrib.loc[repo] = [0, 0, 0, 0, 0]
        # cnt = review.get('review_by', []).count(username)
        cnt = sum(1 for r in review.get('review_by', []) if r[0] == username)
        df_contrib.at[repo, 'reviews'] += cnt
    total_experience = {
        'paddle_repos_cnt': len(df_contrib),
        'repos_can_merge_cnt': len(repos_can_merge),
        'repos_can_merge': repos_can_merge,
        'commits_cnt': int(df_contrib['commits'].sum()),
        'prs_cnt': int(df_contrib['prs'].sum()),
        'issues_cnt': int(df_contrib['issues'].sum()),
        'comments_cnt': int(df_contrib['comments'].sum()),
        'reviews_cnt': int(df_contrib['reviews'].sum()),
    }

    # ---按贡献总数排序，获取前5个repo；如果少于5个repo，补齐---
    df_contrib["total"] = df_contrib[['commits', 'prs', 'issues', 'comments', 'reviews']].sum(axis=1)
    df_top5 = df_contrib.sort_values(by='total', ascending=False).head(5)
    if len(df_top5) < 5:
        rows_to_add = pd.DataFrame(
            0,
            columns=df_top5.columns,
            index=[" " * i for i in range(5 - len(df_top5))]
        )
        df_top5 = pd.concat([df_top5, rows_to_add])
    # 绘图
    fig_repo_contrib = plot_repo_contrib(df_top5)

    # ---获取最近一年的贡献，按月统计---
    index = pd.date_range(start=nowdate - pd.DateOffset(years=1), end=nowdate, freq='ME')
    df_recent_contrib = pd.DataFrame(0, index=index, columns=df_contrib.columns, dtype=int)
    for item in commits:
        date = item['created_at'][:7]
        if date in df_recent_contrib.index:
            df_recent_contrib.at[date, 'commits'] += 1
    for item in prs:
        date = item['created_at'][:7]
        if date in df_recent_contrib.index:
            df_recent_contrib.at[date, 'prs'] += 1
    for item in issues:
        date = item['created_at'][:7]
        if date in df_recent_contrib.index:
            df_recent_contrib.at[date, 'issues'] += 1
    for item in comment_prs_issues:
        for comment in item.get('comment_by', []):
            if comment[0] == username:
                date = comment[1][:7]
                if date in df_recent_contrib.index:
                    df_recent_contrib.at[date, 'comments'] += 1
    for item in review_prs:
        for review in item.get('review_by', []):
            if review[0] == username:
                date = review[1][:7]
                if date in df_recent_contrib.index:
                    df_recent_contrib.at[date, 'reviews'] += 1
    # 绘图
    fig_recent_contrib = plot_recent_contrib(df_recent_contrib)

    return total_experience, fig_repo_contrib, fig_recent_contrib


if __name__ == "__main__":

    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )

    # username = 'dune0310421'
    username = 'Aurelius84'

    # 计时
    start_time = datetime.now()

    experience_data, fig_repo_contrib, fig_recent_contrib = experience(username, datetime(2025, 6, 30, tzinfo=timezone.utc))
    print(f"experience of developer {username}: {experience_data}")
    # 保存绘图
    fig_repo_contrib.write_html(Path("cache") / username / "repo_contrib.html")
    fig_recent_contrib.write_html(Path("cache") / username / "recent_contrib.html")

    end_time = datetime.now()
    print(f"Time taken: {end_time - start_time}")
