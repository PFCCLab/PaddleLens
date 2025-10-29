import datetime
import time
import json
import os
import sys
import math
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import requests
from github import Github

from utils.request_github import request_github
from utils.content_processor import get_domain, get_pr_type, get_commit_type
from utils.manage_data_update_time import get_now_date, update_now_date
from get_data.get_org_repos import get_org_repos_graphql
from get_data.get_repo_issues import update_repo_issues_graphql
from get_data.get_repo_commits import update_repo_commits
from get_data.get_repo_readme import get_repo_readme
from config import GITHUB_TOKEN

def update_paddle_repos(until: str) -> None:
    """
    更新Paddle相关组织的所有仓库信息
    """
    with open("data/paddle_repos.json", "r", encoding="utf-8") as f:
        repos = json.load(f)
    # ---更新paddle相关的repo信息---
    repos_now = get_org_repos_graphql(GITHUB_TOKEN, "PaddlePaddle", until=until)
    repos_now.extend(get_org_repos_graphql(GITHUB_TOKEN, "PFCCLab", until=until))
    repos_now = {repo["full_name"]: repo for repo in repos_now}
    # 从已有项目添加domain
    for repo in repos:
        if repo["full_name"] in repos_now:
            domain = repo["domain"]
            repos_now[repo["full_name"]]["domain"] = domain
    # 为新增的项目添加domain
    for repo in repos_now.values():
        if "domain" not in repo or not repo["domain"]:
            readme_content = get_repo_readme(repo["full_name"])
            domain = get_domain(repo["description"], readme_content)
            repo["domain"] = domain
    repos = list(repos_now.values())
    with open("data/paddle_repos.json", "w", newline="", encoding="utf-8") as f:
        json.dump(repos, f, indent=4, ensure_ascii=False)
    
def update_paddle_issues_prs(since: str, until: str) -> None:
    """
    更新Paddle相关组织的所有仓库的issue和pr信息
    """
    with open("data/paddle_repos.json", "r", encoding="utf-8") as f:
        repos = json.load(f)
    for repo in tqdm(repos):
        full_name = repo["full_name"]
        results = update_repo_issues_graphql(GITHUB_TOKEN, full_name, since, until)
        prs  = []
        issues = []
        for item in results:
            if item["type"] == "Issue":
                item.pop("type")
                issues.append(item)
            elif item["type"] == "PullRequest":
                item.pop("type")
                prs.append(item)
        
        # ---更新pr信息---
        pr_file = f"data/paddle_prs/{full_name.replace('/', '_')}_prs.json"
        if os.path.exists(pr_file):
            with open(pr_file, "r", encoding="utf-8") as f:
                existing_prs = json.load(f)
                existing_prs = {pr["number"]: pr for pr in existing_prs}
        else:
            existing_prs = {}
        # 区分新pr和更新pr
        new_items = []
        for pr_item in prs:
            pr_num = pr_item["number"]
            if pr_num not in existing_prs.keys():
                # 新pr，等待添加类型
                new_items.append(pr_item)
            else:
                # 更新的pr，直接在原数据集上更新
                old_item = existing_prs[pr_num]
                pr_item["type"] = old_item.get("type", "others")
                existing_prs[pr_num] = pr_item
        # 为新pr添加类型，使用多线程
        def enrich_with_type(pr_title: str, pr_body: str) -> str:
            return get_pr_type(pr_title, pr_body)
        with ThreadPoolExecutor(max_workers=9) as executor:
            future_to_pr = {
                executor.submit(enrich_with_type, pr_item["title"], pr_item["body"]): pr_item
                for pr_item in new_items
            }
            for future in as_completed(future_to_pr):
                pr_item = future_to_pr[future]
                try:
                    pr_type = future.result()
                except Exception as e:
                    logging.error(f"Error processing PR #{pr_item['number']}: {e}")
                    pr_type = "others"
                pr_item["type"] = pr_type
                existing_prs[pr_item["number"]] = pr_item
        # 保存更新后的pr数据
        updated_prs = list(existing_prs.values())
        with open(pr_file, "w", newline="", encoding="utf-8") as f:
            json.dump(updated_prs, f, indent=4, ensure_ascii=False)

        # ---更新issue数据---
        issue_file = f"data/paddle_issues/{full_name.replace('/', '_')}_issues.json"
        if os.path.exists(issue_file):
            with open(issue_file, "r", encoding="utf-8") as f:
                existing_issues = json.load(f)
                existing_issues = {issue["number"]: issue for issue in existing_issues}
        else:
            existing_issues = {}
        # 区分新issue和更新issue
        for issue_item in issues:
            if issue_item["number"] in existing_issues.keys():
                # 更新的issue，直接在原数据集上更新
                existing_issues[issue_item["number"]] = issue_item
            else:
                # 新issue，直接添加
                existing_issues[issue_item["number"]] = issue_item
        # 保存更新后的issue数据
        updated_issues = list(existing_issues.values())
        with open(issue_file, "w", newline="", encoding="utf-8") as f:
            json.dump(updated_issues, f, indent=4, ensure_ascii=False)

def update_paddle_commits(since: str, until: str) -> None:
    """
    更新Paddle相关组织的所有仓库的commit信息
    """
    with open("data/paddle_repos.json", "r", encoding="utf-8") as f:
        repos = json.load(f)

    for repo in tqdm(repos):
        full_name = repo["full_name"]
        commits_file = f'data/paddle_commits/{full_name.replace('/', '_')}_commits.json'
        if os.path.exists(commits_file):
            with open(commits_file, 'r', encoding='utf-8') as f:
                existing_commits = json.load(f)
        else:
            existing_commits = []

        results = update_repo_commits(GITHUB_TOKEN, full_name, since, until)
        # 多线程添加commit message type
        with ThreadPoolExecutor(max_workers=9) as executor:
            future_to_commit = {
                executor.submit(get_commit_type, commit.get("message", "")): commit for commit in results
            }
            for future in tqdm(as_completed(future_to_commit), total=len(future_to_commit), desc=f"Fetching commit types for {full_name}", dynamic_ncols=True):
                commit = future_to_commit[future]
                try:
                    commit["why_what_label"] = future.result()
                except Exception as e:
                    print(f"Error processing commit {commit['sha']} in repository {full_name}: {e}")

        # 去重
        existing_shas = {commit['sha'] for commit in existing_commits}
        results = [commit for commit in results if commit['sha'] not in existing_shas]
        existing_commits.extend(results)
        with open(commits_file, "w", newline="", encoding="utf-8") as f:
            json.dump(existing_commits, f, indent=4, ensure_ascii=False)

def update_repos_modules_weights():
    """
    更新Paddle相关组织的所有仓库的模块重要度信息
    """
    with open("data/paddle_repos.json", 'r', encoding='utf-8') as f:
        paddle_repos = json.load(f)
    module_weights = {}
    for repo in paddle_repos:
        repo_owner, repo_name = repo['full_name'].split('/')            
        with open(f"data/paddle_commits/{repo_owner}_{repo_name}_commits.json", 'r', encoding='utf-8') as f:
            commits = json.load(f)
        modules = {}
        for commit in commits:
            files = commit['files']
            for file in files:
                filename = file['filename']
                parts = filename.split('/')
                # 只取前两级目录作为模块名 eg: src/module1/file.py -> src/module1
                if len(parts) > 2:
                    module = '/'.join(parts[:2])
                else:
                    module = parts[0] # 一级及以下用第一级目录/文件名
                modules[module] = modules.get(module, 0) + 1
        # 归一化
        log_counts = {k: math.log(v + 1) for k, v in modules.items()}
        max_log = max(log_counts.values()) if log_counts else 1 # 取最大值作为标准计算相对权重
        repo_module_weights = {k: v / max_log for k, v in log_counts.items()} # 归一化权重
        module_weights[repo['full_name']] = repo_module_weights
    with open("data/paddle_repos_module_weights.json", 'w', encoding='utf-8') as f:
        json.dump(module_weights, f, indent=4, ensure_ascii=False)

def update_all():
    """
    更新所有数据
    """
    since = get_now_date()
    until = "2025-10-24"
    # until = datetime.datetime.now().strftime("%Y-%m-%d")

    # 一次最多处理一周的数据，避免触发rate limit
    since_dt = datetime.datetime.fromisoformat(since)
    until_dt = datetime.datetime.fromisoformat(until)
    delta = until_dt - since_dt
    for i in range(0, delta.days, 7):
        batch_since_dt = since_dt + datetime.timedelta(days=i)
        batch_until_dt = min(batch_since_dt + datetime.timedelta(days=7), until_dt)
        batch_since = batch_since_dt.strftime("%Y-%m-%d")
        batch_until = batch_until_dt.strftime("%Y-%m-%d")
        print(f"Updating data from {batch_since} to {batch_until}...")
        start_time = time.time()
        try:
            # ---更新paddle相关的repo信息---
            update_paddle_repos(batch_until)

            # ---更新paddle相关的issue和pr信息---
            update_paddle_issues_prs(batch_since, batch_until)

            # ---更新paddle相关的commit信息---
            update_paddle_commits(batch_since, batch_until)

            # ---更新paddle相关的模块重要度信息---
            update_repos_modules_weights()

            # 更新nowdate
            update_now_date(batch_until)

        except Exception as e:
            logging.error(f"Error updating data from {batch_since} to {batch_until}: {e}")
            time.sleep(max(3700-(time.time() - start_time), 0)) # 避免触发rate limit

    # # ---更新paddle相关的repo信息---
    # update_paddle_repos(until)

    # # ---更新paddle相关的issue和pr信息---
    # update_paddle_issues_prs(since, until)

    # # ---更新paddle相关的commit信息---
    # update_paddle_commits(since, until)

    # # ---更新paddle相关的模块重要度信息---
    # update_repos_modules_weights()

    # # 更新nowdate
    # update_now_date(until)

if __name__ == "__main__":

    # ---更新paddle相关的repo信息---
    # update_paddle_repos()

    # ---更新paddle相关的issue和pr信息---
    # update_paddle_issues_prs()

    # ---更新paddle相关的commit信息---
    # update_paddle_commits()

    # ---更新paddle相关的模块重要度信息---
    # update_repos_modules_weights()

    update_all()
