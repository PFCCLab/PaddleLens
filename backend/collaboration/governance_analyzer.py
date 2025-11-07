from hmac import new
import json
import math
import os
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from urllib import response
from uuid import uuid4
import logging
from collections import defaultdict
from pathlib import Path
from github import Github
from typing import Optional, List

from utils import load_user_data
from utils.manage_data_update_time import get_now_date
from utils.dvpr_affliation import get_community_developers
from get_data.get_user_info import get_user_info
from config import GITHUB_TOKEN

DATA_DIR = "data"
    
class GovernanceAnalyzer:
    """
    分析飞桨的治理情况
    """
    def __init__(self, input_date: Optional[date] = None):
        """
        初始化
        """
        # 检查repo是否在飞桨里
        nowdate = get_now_date()
        nowdate = datetime.fromisoformat(nowdate).replace(tzinfo=timezone.utc).date()  # date对象

        self.repo = "PaddlePaddle/Paddle"
        self.rules = []

        # 设置开始时间（默认90天前）
        if input_date:
            self.input_date = input_date
        else:
            self.input_date = nowdate
        self.before = self.input_date - timedelta(days=90)  # 近期时间段，默认30天
        self.after = self.input_date + timedelta(days=90)  # 后续时间段，默认30天
        self.new_rule = []


    def get_governance_rules(self):
        """
        获取治理规则
        """
        file_path = os.path.join(DATA_DIR, "paddle-rules.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError("找不到文件 paddle-rules.json。")
        
        with open(file_path, "r", encoding="utf-8") as f:
            rules = json.load(f)

        rules_now = []
        for rule in rules:
            rule_date = datetime.fromisoformat(rule.get("time")).date()
            if rule_date <= self.input_date:
                data = rule
                rules_now.append(data)
        rules_now = sorted(rules_now, key=lambda x: x.get("time"), reverse=True)

        rules_res = {}
        for rule in rules_now:
            category = rule.get("category", "其他")
            if category not in rules_res:
                rules_res[category] = []
            rules_res[category].append({
                "description": rule.get("description", ""),
                "time": rule.get("time", "")
            })

        rules_tree = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for rule in rules_now:
            time_ = rule.get("time").split("T")[0]
            category = rule.get("category", "其他")
            rule_type = rule.get("rule type", "未分类")
            detailed_code = rule.get("detailed code") or "_general"
            rule_desc = rule.get("rule description", "")
            rule_content = rule.get("content") or ""

            if time_ == self.input_date.strftime("%Y-%m-%d"):
                if detailed_code == "_general":
                    self.new_rule.append(f"{category} - {rule_type} : {rule_desc}。{rule_content}")
                else:
                    self.new_rule.append(f"{category} - {rule_type} - {detailed_code} : {rule_desc}。{rule_content}")

            rules_tree[category][rule_type][detailed_code].append(f"{rule_desc}。{rule_content} -- 发布时间：{time_}")

        category_order = {
            "position": 0,
            "boundary": 1,
            "choice": 2,
            "scope": 3,
            "aggregation": 4,
            "information": 5,
            "payoff": 6,
            "其他": 7
        }
        rules_tree = dict(sorted(rules_tree.items(), key=lambda x: category_order.get(x[0], 99)))

        # 转为普通字典
        structured_rule_dict = json.loads(json.dumps(rules_tree))
        return rules_tree


    def analyze_response_time(self):
        """
        分析 PR、Issue 的响应/关闭效率；分别统计 before / after 两个 30 天窗口。
        """
        res = {
            "before": {
                "pr_response_time_before": 0,
                "pr_close_time_before": 0,
                "issue_response_time_before": 0
            },
            "after": {
                "pr_response_time_after": 0,
                "pr_close_time_after": 0,
                "issue_response_time_after": 0
            }
        }
        owner, repo_name = self.repo.split('/')
        try:
            with open(f"{DATA_DIR}/paddle_prs/{owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
                prs = json.load(f)
            with open(f"{DATA_DIR}/paddle_issues/{owner}_{repo_name}_issues.json", 'r', encoding='utf-8') as f:
                issues = json.load(f)
        except FileNotFoundError:
            return res  # 数据缺失时直接返回 0

        # 初始化时间段
        recent_start = self.before
        recent_end = self.input_date
        later_start = self.input_date
        later_end = self.after

        # 各时间段的响应时间列表
        pr_response_recent, pr_response_later = [], []
        pr_close_recent, pr_close_later = [], []
        issue_response_recent, issue_response_later = [], []

        def is_in_range(dt, start, end):
            return start <= dt.date() <= end

        for pr in prs:
            if not pr['closed_at']:
                continue

            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            closed_at = datetime.fromisoformat(pr['closed_at'].replace('Z', '+00:00'))

            # 初始化响应时间为关闭时间（万一没人回复）
            first_response_at = closed_at

            # PR 评论
            comments = pr.get('comment_by', [])
            for comment_author, comment_time in comments:
                if not comment_author or not comment_time:
                    continue
                if 'paddle-bot' in comment_author.lower() or 'CLAassistant' in comment_author:
                    continue
                first_response_at = datetime.fromisoformat(comment_time.replace('Z', '+00:00'))
                break
            # review_by
            review_comments = pr.get('review_by', [])
            for comment_author, comment_time in review_comments:
                if not comment_author or not comment_time:
                    continue
                if 'paddle-bot' in comment_author.lower():
                    continue
                first_response_at = datetime.fromisoformat(comment_time.replace('Z', '+00:00'))
                break

            response_time = (first_response_at - created_at).total_seconds() / 3600
            close_time = (closed_at - created_at).total_seconds() / 3600

            if is_in_range(created_at, recent_start, recent_end):
                pr_response_recent.append(response_time)
                pr_close_recent.append(close_time)
            elif is_in_range(created_at, later_start, later_end):
                pr_response_later.append(response_time)
                pr_close_later.append(close_time)

        # ISSUE 分析
        for issue in issues:
            if 'error' in issue or not issue['closed_at']:
                continue

            created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
            closed_at = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00'))
            first_response_at = closed_at

            comments = issue.get('comment_by', [])
            for comment_author, comment_time in comments:
                if not comment_author or not comment_time:
                    continue
                if 'paddle-bot' in comment_author.lower():
                    continue
                first_response_at = datetime.fromisoformat(comment_time.replace('Z', '+00:00'))
                break

            response_time = (first_response_at - created_at).total_seconds() / 3600

            if is_in_range(created_at, recent_start, recent_end):
                issue_response_recent.append(response_time)
            elif is_in_range(created_at, later_start, later_end):
                issue_response_later.append(response_time)

        # 中位数计算函数
        def median_or_zero(data):
            if not data:
                return 0
            data.sort()
            mid = len(data) // 2
            if len(data) % 2 == 0:
                return round((data[mid - 1] + data[mid]) / 2, 1)
            else:
                return round(data[mid], 1)

        # 填入统计值
        res["before"] = {
            "pr_response_time_before": median_or_zero(pr_response_recent),
            "pr_close_time_before": median_or_zero(pr_close_recent),
            "issue_response_time_before": median_or_zero(issue_response_recent)
        }

        res["after"] = {
            "pr_response_time_after": median_or_zero(pr_response_later),
            "pr_close_time_after": median_or_zero(pr_close_later),
            "issue_response_time_after": median_or_zero(issue_response_later)
        }

        return res
    
    def analyze_community_developer_activity(self):
        """
        社区新贡献者（首次提交pr的贡献者）情况：新贡献者数量、新贡献者pr数量和占比、合并pr数量和占比、新贡献者归属
        """
        res = {
            "before": {
                "community_newcomer_cnt_before": 0,  # 近期首次提交PR的新贡献者数量
                "community_newcomer_pr_cnt_before": 0,  # 新贡献者的PR数量
                "community_newcomer_pr_cnt_ratio_before": 0.0,  # 新贡献者PR数量占比
                "community_newcomer_pr_merged_cnt_before": 0,  # 新贡献者合并PR数量
                "community_newcomer_pr_merged_cnt_ratio_before": 0.0,  # 新贡献者合并PR率
                "community_newcomer_affiliation_ratio_before": 0.0  # 新贡献者归属
            },
            "after": {
                "community_newcomer_cnt_after": 0,  # 后续首次提交PR的新贡献者数量
                "community_newcomer_pr_cnt_after": 0,  # 后续新贡献者的PR数量
                "community_newcomer_pr_cnt_ratio_after": 0.0,  # 后续新贡献者PR数量占比
                "community_newcomer_pr_merged_cnt_after": 0,  # 后续新贡献者合并PR数量
                "community_newcomer_pr_merged_cnt_ratio_after": 0.0,  # 后续新贡献者合并PR率
                "community_newcomer_affiliation_ratio_after": 0.0  # 后续新贡献者归属
            }
        }
    
        owner, repo_name = self.repo.split('/')
        # 获取社区开发者
        with open(f"{DATA_DIR}/paddle_commits/{owner}_{repo_name}_commits.json", "r", encoding="utf-8") as f:
            commits = json.load(f)
        community_developers = get_community_developers(commits)
        
        # 统计社区开发者的pr数量
        with open(f"{DATA_DIR}/paddle_prs/{owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
            # 保存作者首次提交 PR 的时间
        author_first_pr_time = {}
        for pr in prs:
            author = pr.get('user')
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            if author not in author_first_pr_time or created_at < author_first_pr_time[author]:
                author_first_pr_time[author] = created_at
        # 初始化统计数据
        def init_stats():
            return {
                "total_prs": 0,
                "total_merged_prs": 0,
                "newcomer_pr_cnt": 0,
                "newcomer_merged_pr_cnt": 0,
                "newcomer_authors": set(),
                "newcomer_affiliations": set()
            }
        stats = {
            "before": init_stats(),
            "after": init_stats()
        }
        # 遍历 PR，分时间段统计
        for pr in prs:
            created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            pr_date = created_at.date()
            author = pr.get('user')
            merged = pr.get('merged', False)
            first_pr_date = author_first_pr_time[author].date()
            # 判断 PR 所属时间段
            if self.before <= pr_date < self.input_date:
                key = "before"
            elif self.input_date <= pr_date < self.after:
                key = "after"
            else:
                continue  # 不属于我们关心的时间段
            stats[key]["total_prs"] += 1
            # 判断该作者是否是当前窗口中的新贡献者
            if ((key == "before" and self.before <= first_pr_date < self.input_date) or
                (key == "after" and self.input_date <= first_pr_date < self.after)):
                stats[key]["newcomer_authors"].add(author)
                stats[key]["newcomer_pr_cnt"] += 1
                if merged:
                    stats[key]["newcomer_merged_pr_cnt"] += 1
                # 判断是否为社区开发者
                if author.strip().lower() in community_developers:
                    stats[key]["newcomer_affiliations"].add(author)
        # 汇总结果
        for key in ["before", "after"]:
            stat = stats[key]
            newcomer_cnt = len(stat["newcomer_authors"])
            community_newcomer_cnt = len(stat["newcomer_affiliations"])
            total_prs = stat["total_prs"]
            newcomer_pr_cnt = stat["newcomer_pr_cnt"]
            res[key][f"community_newcomer_cnt_{key}"] = newcomer_cnt
            res[key][f"community_newcomer_pr_cnt_{key}"] = newcomer_pr_cnt
            res[key][f"community_newcomer_pr_merged_cnt_{key}"] = stat["newcomer_merged_pr_cnt"]
            # 新贡献者在该窗口内提交 PR 占所有 PR 比例
            if total_prs > 0:
                res[key][f"community_newcomer_pr_cnt_ratio_{key}"] = round(
                    newcomer_pr_cnt / total_prs, 4
                )
            # 新贡献者合并率（合并 PR / 提交 PR）
            if newcomer_pr_cnt > 0:
                res[key][f"community_newcomer_pr_merged_cnt_ratio_{key}"] = round(
                    stat["newcomer_merged_pr_cnt"] / newcomer_pr_cnt, 4
                )
            # 归属占比 (社区开发者数 / 新贡献者数)
            res[key][f"community_newcomer_affiliation_ratio_{key}"] = round(
                community_newcomer_cnt / newcomer_cnt, 4
            ) if newcomer_cnt > 0 else 0.0
        return res

    def analyze_governance(self):
        """
        分析飞桨的治理情况，返回结果
        """
        rules = self.get_governance_rules()
        new_rule = self.new_rule
        response_time = self.analyze_response_time()
        community_developer_activity = self.analyze_community_developer_activity()
        # community_developer_activity = {}
        res = {
            "date": get_now_date(),
            "scores": {
                "response_time": response_time,
                "community_developer_activity": community_developer_activity
            },
            "rules": rules,
            "new_rule": new_rule
        }

        return res

if __name__ == "__main__":
    analyzer = GovernanceAnalyzer(date(2022, 3, 9))
    # result = analyzer.analyze_community_developer_activity()
    # result = analyzer.analyze_response_time()
    result = analyzer.analyze_governance()
    print(result)