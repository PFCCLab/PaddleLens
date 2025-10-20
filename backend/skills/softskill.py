import os
import json
import math
import logging
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import plotly.graph_objects as go

def plot_consistency(repo_consistency: dict) -> go.Figure:
    """
    绘制责任心柱状图
    """
    repos_sorted = sorted(repo_consistency.items(), key=lambda x: x[1])
    repo_names = [k for k, v in repos_sorted]
    month_counts = [v for k, v in repos_sorted]
    colors = [
        '#66c2a5',
        '#fc8d62',
        '#8da0cb',
        '#e78ac3',
        '#a6d854',
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=repo_names,
        x=month_counts,
        orientation="h",
        marker_color=colors,
    ))
    fig.update_layout(
        title="Consistency",
        xaxis_title="Max Continuous Commit Months",
        xaxis=dict(range=[0, 1] if max(month_counts) == 0 else [0, None]),
        template="plotly_white",
        height=400 + len(repo_names) * 30,
        margin=dict(l=150, r=40, t=60, b=40),
    )
    return fig

def plot_activeness(repo_activeness: dict) -> go.Figure:
    """
    绘制活跃度柱状图
    """
    repos_sorted = sorted(repo_activeness.items(), key=lambda x: x[1])
    repo_names = [k for k, v in repos_sorted]
    active_ratios = [v for k, v in repos_sorted]
    colors = [
        '#66c2a5',
        '#fc8d62',
        '#8da0cb',
        '#e78ac3',
        '#a6d854',
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=repo_names,
        x=active_ratios,
        orientation="h",
        marker_color=colors,
    ))
    fig.update_layout(
        title="Activeness",
        xaxis_title="Average Active Months Ratio in a Period (6 Months)",
        xaxis=dict(range=[0, 1]),
        template="plotly_white",
        height=400 + len(repo_names) * 30,
        margin=dict(l=150, r=40, t=60, b=40),
    )
    return fig

def plot_communication(labels: list[int]) -> go.Figure:
    """
    绘制沟通能力饼图
    """
    label_map = {
        0: 'no what and why',
        1: 'only why',
        2: 'only what',
        3: 'what and why'
    }
    label_count = {k:0 for k in label_map.keys()}
    for label in labels:
        label_count[label] += 1
    label_names = [label_map[k] for k in label_count.keys()]
    sizes = [v for v in label_count.values()]
    colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3']
    fig = go.Figure()

    fig.add_trace(go.Pie(
        labels=label_names,
        values=sizes,
        marker_colors=colors,
        textinfo='label+percent',
        insidetextorientation='radial'
    ))
    fig.update_layout(
        # title="Communication Skill in Commit Messages",
        template="plotly_white",
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig

# 责任心
def commitment(task_name: str) -> tuple[go.Figure, go.Figure]:
    """
    责任心：用户在每个项目中的最大连续贡献月份数 + 一段时间内的贡献月份比例。
    """

    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "commits.json", 'r', encoding='utf-8') as f:
        commits = json.load(f)
        
    # 获取每个项目的贡献年月
    project_months = {}
    for c in commits:
        repo = c['repo']
        commit_date = datetime.fromisoformat(c['created_at'].replace('Z', '+00:00'))
        ym = (commit_date.year, commit_date.month)
        if repo not in project_months:
            project_months[repo] = set()
        project_months[repo].add(ym)
    
    # ---consistency：每个项目的最大连续月份---
    repo_consistency = {}
    for repo, ym_pairs in project_months.items():
        sorted_ym = sorted(ym_pairs) # 按年月排序
        max_m = 1
        current_m = 1
        for i in range(1, len(sorted_ym)):
            y1, m1 = sorted_ym[i - 1]
            y2, m2 = sorted_ym[i]
            # 月份差计算
            diff = (y2 - y1) * 12 + (m2 - m1)
            if diff == 1:
                current_m += 1
                max_m = max(max_m, current_m)
            else:
                current_m = 1
        repo_consistency[repo] = max_m
    # 提取top5 repo，若少于5个repo，用0补齐
    top_repos = sorted(repo_consistency.items(), key=lambda x: x[1], reverse=True)[:5]
    top_repos_dict = dict(top_repos)
    if len(top_repos_dict) < 5:
        for i in range(5 - len(top_repos_dict)):
            top_repos_dict[" " * i] = 0
    # 绘图
    fig_consistency = plot_consistency(top_repos_dict)

    # ---activeness：每个项目的半年内贡献月份的均值---
    repo_activeness = {}
    for repo, ym_pairs in project_months.items():
        sorted_ym = sorted(ym_pairs)
        if not sorted_ym:
            repo_activeness[repo] = 0.0
            continue
        start_year, start_month = min(sorted_ym)
        end_year, end_month = max(sorted_ym)
        total_months = (end_year * 12 + end_month) - (start_year * 12 + start_month) + 1
        # 构造"某月是否有提交"的list
        month_flags = [0] * total_months
        for i in sorted_ym:
            y, m = i
            index = (y - start_year) * 12 + (m - start_month)
            month_flags[index] = 1    
        #滑动窗口统计活跃度
        window_size = 6
        if total_months < window_size:
            repo_activeness[repo] = sum(month_flags) / window_size
            continue
        window_sum = sum(month_flags[:window_size]) # 初始窗口
        windows = [window_sum]
        for i in range(window_size, total_months):
            window_sum = window_sum - month_flags[i - window_size] + month_flags[i]
            windows.append(window_sum)
        # Step 4: 平均值
        avg_active_months = (sum(windows) / len(windows)) / window_size
        repo_activeness[repo] = avg_active_months
    # 提取top5 repo，若少于5个repo，用0补齐
    top_repos = sorted(repo_activeness.items(), key=lambda x: x[1], reverse=True)[:5]
    top_repos_dict = dict(top_repos)
    if len(top_repos_dict) < 5:
        for i in range(5 - len(top_repos_dict)):
            top_repos_dict[" " * i] = 0.0
    # 绘图
    fig_activeness = plot_activeness(top_repos_dict)

    return fig_consistency,fig_activeness

# 时间管理能力
def time_management(task_name: str) -> dict:
    """
    时间管理：一段时间窗口内同时活跃于最多项目
    """
    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "commits.json", 'r', encoding='utf-8') as f:
        commits = json.load(f)

    # 获取每个月的活跃项目
    month_projects = {} # (year, month) -> set of projects
    for c in commits:
        repo = c['repo']
        commit_date = datetime.fromisoformat(c['created_at'].replace('Z', '+00:00'))
        ym = (commit_date.year, commit_date.month)
        if ym not in month_projects:
            month_projects[ym] = set()
        month_projects[ym].add(repo)
    month_projects = dict(sorted(month_projects.items()))  # 按年月排序
    if not month_projects:  # 没有commit
        return {
            "max_active_month_start": None,
            "max_active_month_end": None,
            "active_projects": set(),
            "commit_count": 0
        }
    # 填补缺失的月份
    start_year, start_month = next(iter(month_projects.keys())) # 起始年月
    end_year, end_month = next(iter(reversed(month_projects.keys()))) # 结束年月
    total_months = (end_year * 12 + end_month) - (start_year * 12 + start_month) + 1 # 总月份数
    for i in range(total_months):
        year = start_year + (start_month + i - 1) // 12 # 
        month = (start_month + i - 1) % 12 + 1
        if (year, month) not in month_projects:
            month_projects[(year, month)] = set()
    # 再次排序以确保顺序正确
    month_projects_lst = list(dict(sorted(month_projects.items())).values())

    # 计算每个时间窗口内活跃项目数
    window_size = 2
    active_projects = []
    max_active = (0, set())  # (月份索引, 活跃项目集合)
    if len(month_projects) < window_size:
        # 如果活跃月份数少于窗口大小，则直接使用所有项目的并集
        active_projects = set.union(*month_projects_lst)
        max_active = (0, active_projects)
    else:
        active_projects = month_projects_lst[:window_size]  # 初始窗口
        max_active = (0, set.union(*active_projects))
        for i in range(window_size, len(month_projects_lst)):
            # 滑动窗口
            active_projects.pop(0)
            active_projects.append(month_projects_lst[i])
            # 计算当前窗口的活跃项目
            current_active = set.union(*active_projects)
            if len(current_active) > len(max_active[1]):
                max_active = (i - window_size + 1, current_active)
    # 将索引转换为实际的年月
    max_active_month_start = list(month_projects.keys())[max_active[0]]
    max_active_month_end = list(month_projects.keys())[max_active[0] + min(window_size - 1, len(month_projects) - 1)]
    # 获取这些项目中的commit
    commit_active = [c for c in commits if c['repo'] in max_active[1]]

    return {
        "max_active_month_start": max_active_month_start,
        "max_active_month_end": max_active_month_end,
        "active_projects": max_active[1],
        "commit_count": len(commit_active)
    }

# 沟通能力
def communication_skill(task_name: str) -> tuple[float, go.Figure, dict]:
    """
    沟通能力：commit message的质量
    """
    user_cache_dir = Path("cache") / task_name
    with open(user_cache_dir / "commits.json", 'r', encoding='utf-8') as f:
        commits = json.load(f)

    if not commits:
        return 0.0, plot_communication([]), {}

    commit_labels = [commit['why_what_label'] for commit in commits]

    #计算分数
    score = 0
    for label in commit_labels:
        if label == 3:
            score += 1
        elif label == 1 or label == 2:
            score += 0.8
    score = score / len(commits)
    score = round(score * 100, 2)  # 转化为百分制，保留两位小数

    # 绘制饼图
    fig_comm = plot_communication(commit_labels)

    # 抽取每类的示例 commit
    label_names = {
        0: "what",
        1: "why",
        2: "other",
        3: "what+why"
    }

    sample_commits = {}
    seen_labels = set()

    for commit in commits:
        label = commit['why_what_label']
        key = label_names.get(label)
        if key and key not in seen_labels:
            sample_commits[key] = {
                "repo": commit['repo'],
                "sha": commit['sha'],
                "message": commit['message']
            }
            seen_labels.add(key)
        if len(seen_labels) == 4:
            break

    return score, fig_comm, sample_commits


def softskill(task_name: str) -> tuple[go.Figure, go.Figure, dict, float, go.Figure, dict]:
    """
    软技能：责任心、时间管理能力、沟通能力
    """
    logging.info(f"Analyzing softskills for task: {task_name}")
    # 1.责任心
    fig_consistency, fig_activeness = commitment(task_name)

    # 2.时间管理能力
    time_mgmt = time_management(task_name)

    # 3.沟通能力
    comm_score, fig_comm, sample_commits = communication_skill(task_name)

    return fig_consistency, fig_activeness, time_mgmt, comm_score, fig_comm, sample_commits

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    # 计时
    start_time = datetime.now()

    # username = 'dune0310421'
    username = 'Aurelius84'

    fig1, fig2, time_mgmt, comm_score, fig_comm, sample_commits = softskill(username)
    fig1.write_html(Path("cache") / username / "consistency.html")
    fig2.write_html(Path("cache") / username / "activeness.html")
    print(f"Time Management: {time_mgmt['max_active_month_start']} - {time_mgmt['max_active_month_end']}, Active Projects: {len(time_mgmt['active_projects'])}, Commit Count: {time_mgmt['commit_count']}")
    print(f"Communication Skill Score: {comm_score}")
    fig_comm.write_html(Path("cache") / username / "communication.html")

    end_time = datetime.now()
    print(f"Time taken: {end_time - start_time}")

