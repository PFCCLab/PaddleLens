import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib import response
from uuid import uuid4
import logging
from pathlib import Path
from github import Github

from utils import load_user_data
from utils.manage_data_update_time import get_now_date
from get_data.get_user_info import get_user_info
from config import GITHUB_TOKEN

DATA_DIR = "data"

class GovernanceRuleAnalyzer:
    """
    分析飞桨的治理规则得分
    """
    def __init__(self, repo: str = "PaddlePaddle/Paddle"):
        self.repo = repo
    
    def analyze_governance_rules(self):
        files = [
            os.path.join(f"{DATA_DIR}/governance_scores", f)
            for f in os.listdir(f"{DATA_DIR}/governance_scores")
            if f.endswith(".json")
        ]
        if not files:
            raise FileNotFoundError("找不到评分文件。")
        latest_file = max(files, key=os.path.getctime)

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = {
            "scores": data,
        }
            
        return results
    
class GovernanceAnalyzer:
    """
    分析飞桨的治理情况
    """
    def __init__(self, repo: str = "PaddlePaddle/Paddle"):
        """
        初始化
        """
        # 检查repo是否在飞桨里
        with open(f"{DATA_DIR}/paddle_repos.json", 'r', encoding='utf-8') as f:
            paddle_repos = json.load(f)
        repo_list = [r["full_name"] for r in paddle_repos]
        if repo not in repo_list:
            raise ValueError("目前仅支持分析PaddlePaddle和PFCCLab组织下的仓库，请检查仓库名是否正确")
        nowdate = get_now_date()
        nowdate = datetime.fromisoformat(nowdate).replace(tzinfo=timezone.utc)
        self.repo = repo
        self.recent = nowdate - timedelta(days=90)

    def analyze_response_time(self):
        """
        pr响应效率，pr关闭效率，issue响应效率
        """
        res = {
            "pr_response_time_recent": 0,
            "pr_close_time_recent": 0,
            "issue_response_time_recent": 0
        }
        owner, repo_name = self.repo.split('/')
        with open(f"{DATA_DIR}/paddle_prs/{owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
        with open(f"{DATA_DIR}/paddle_issues/{owner}_{repo_name}_issues.json", 'r', encoding='utf-8') as f:
            issues = json.load(f)

        pr_response_times = []
        pr_close_times = []
        issue_response_times = []

        for pr in prs:
            if not pr['closed_at']:
                continue
            # 计算pr的首次响应延迟
            first_response_at = datetime.fromisoformat(pr['closed_at'].replace('Z', '+00:00'))
            comments = pr.get('comment_by', [])
            for comment in comments:
                comment_author, comment_time = comment[0], comment[1]
                if 'paddle-bot' in comment_author.lower():
                    continue
                if 'CLAassistant' in comment_author:
                    continue
                else:
                    first_response_at = datetime.fromisoformat(comment_time.replace('Z', '+00:00'))
                    break
            review_comments = pr.get('review_by', [])
            for comment in review_comments:
                comment_author, comment_time = comment[0], comment[1]
                if not comment_author or not comment_time:
                    continue
                if 'paddle-bot' in comment_author.lower():
                    continue
                else:
                    first_response_at = datetime.fromisoformat(comment_time.replace('Z', '+00:00'))
                    break
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            response_time = (first_response_at - created_at).total_seconds() / 3600  # 小时
            pr_response_times.append(response_time)
            # 计算pr的关闭延迟
            closed_at = datetime.fromisoformat(pr['closed_at'].replace('Z', '+00:00'))
            close_time = (closed_at - created_at).total_seconds() / 3600  # 小时
            pr_close_times.append(close_time)

        for issue in issues:
            if 'error' in issue:
                continue
            if not issue['closed_at']:
                continue
            created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            # 计算issue的首次响应延迟
            first_response_at = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00'))
            comments = issue.get('comment_by', [])
            for comment in comments:
                comment_author, comment_time = comment[0], comment[1]
                if not comment_author or not comment_time:
                    continue
                if 'paddle-bot' in comment_author.lower():
                    continue
                else:
                    first_response_at = datetime.fromisoformat(comment_time.replace('Z', '+00:00'))
                    break
            response_time = (first_response_at - created_at).total_seconds() / 3600  # 小时
            issue_response_times.append(response_time)

        # 计算近期响应时间和关闭时间的中位数,保留两位小数
        if pr_response_times:
            res["pr_response_time_recent"] = round(sorted(pr_response_times)[len(pr_response_times) // 2], 1)
        if pr_close_times:
            res["pr_close_time_recent"] = round(sorted(pr_close_times)[len(pr_close_times) // 2], 1)
        if issue_response_times:
            res["issue_response_time_recent"] = round(sorted(issue_response_times)[len(issue_response_times) // 2], 1)

        return res

    def analyze_community_developer_activity(self):
        """
        社区开放性
        """
        res = {
            "community_developer_cnt_recent": 0,  # 近期提交pr的社区开发者人数
            "community_developer_merged_cnt_recent": 0,  # 近期提交并合并pr的社区开发者人数

            "community_newcomer_pr_cnt_recent": 0,  # 近期首次提交pr的开发者的pr数
            "community_newcomer_pr_merged_cnt_recent": 0,  # 近期首次提交并合并pr的开发者的pr数

            "top5_active_community_developers_recent": []  # 近期pr提交数最多的前5名社区开发者
        }
        owner, repo_name = self.repo.split('/')
        
        # 统计社区开发者的pr数量
        with open(f"{DATA_DIR}/paddle_prs/{owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
        community_developers_recent_set = set()
        community_developers_merged_recent_set = set()
        for pr in prs:
            author = pr.get('user')
            # 近期pr
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            if created_at < self.recent:
                continue
            community_developers_recent_set.add(author)  # 近期提交pr的开发者人数
            if pr.get('merged'):
                community_developers_merged_recent_set.add(author)  # 近期提交并合并pr的开发者人数
        res["community_developer_cnt_recent"] = len(community_developers_recent_set)
        res["community_developer_merged_cnt_recent"] = len(community_developers_merged_recent_set)

        # 近期社区新手
        existing_set = set()
        for pr in prs:
            author = pr.get('user')
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            if created_at < self.recent:
                existing_set.add(author)
        for pr in prs:
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            if created_at < self.recent:
                continue
            author = pr.get('user')
            if author not in existing_set:
                res["community_newcomer_pr_cnt_recent"] += 1  # 近期首次提交pr的开发者的pr数
                if pr.get('merged'):
                    res["community_newcomer_pr_merged_cnt_recent"] += 1  # 近期首次提交并合并pr的开发者的pr数

        # 近期提交pr开发者top5
        community_dev_pr_count = {}
        for pr in prs:
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            if created_at < self.recent:
                continue
            author = pr.get('user')
            if author not in community_dev_pr_count:
                community_dev_pr_count[author] = 0
            community_dev_pr_count[author] += 1
        top5_active_community_developers_recent = sorted(community_dev_pr_count.items(), key=lambda x: x[1], reverse=True)[:5]
        res["top5_active_community_developers_recent"] = top5_active_community_developers_recent

        return res

    def analyze_governance(self):
        """
        分析飞桨的治理情况，返回结果
        """
        response_time = self.analyze_response_time()
        community_developer_activity = self.analyze_community_developer_activity()
        res = {
            "date": get_now_date(),
            "scores": {
                "response_time": response_time,
                "community_developer_activity": community_developer_activity
            },
        }

        return res

if __name__ == "__main__":
    analyzer = GovernanceAnalyzer("PaddlePaddle/Paddle")
    result = analyzer.analyze_community_developer_activity()
    # result = analyzer.analyze_response_time()
    print(result)