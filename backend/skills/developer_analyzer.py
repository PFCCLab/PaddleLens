import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import logging
from pathlib import Path
from github import Github

from skills import basic_info, experience, hardskill, softskill
from utils import load_user_data
from utils.manage_data_update_time import get_now_date
from get_data.get_user_info import get_user_info
from config import GITHUB_TOKEN

class DeveloperAnalyzer:
    """
    分析开发者的技能。
    """
    def __init__(self, username: str):
        """
        初始化分析器，设置cache目录。
        """
        self.username = username
        self.task_id = str(uuid4())
        # self.task_name = username  # ---暂时不使用uuid，方便调试---
        self.task_name = username + "_" + self.task_id
        self.user_cache_dir = Path("cache") / self.task_name  # 临时目录：./cache/{github_user}_{uuid4()}/

        self.user_cache_dir.mkdir(parents=True, exist_ok=True)  # 创建目录

    def fetch_data(self):
        """
        从 GitHub 和本地获取数据，并存入json
        """
        gh = Github(GITHUB_TOKEN)
        # ---从github获取用户基本信息和仓库信息---
        info = get_user_info(gh, self.username)
        with open(self.user_cache_dir / "info.json", 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=4)

        # ---从本地加载paddle相关repo，获取commits, pr, issue, review, comment等信息---
        with open(f"data/paddle_repos.json", 'r', encoding='utf-8') as f:
            repos = json.load(f)
        # commit
        commits = []
        for repo in repos:
            cmts = load_user_data.user_commits_in_repo(self.username, repo["full_name"])
            commits.extend(cmts)
        with open(self.user_cache_dir / "commits.json", 'w', encoding='utf-8') as f:
            json.dump(commits, f, ensure_ascii=False, indent=4)
        # pr
        prs = []
        for repo in repos:
            prs_tmp = load_user_data.user_prs_in_repo(self.username, repo["full_name"])
            prs.extend(prs_tmp)
        with open(self.user_cache_dir / "prs.json", 'w', encoding='utf-8') as f:
            json.dump(prs, f, ensure_ascii=False, indent=4)
        # issue
        issues = []
        for repo in repos:
            issues_tmp = load_user_data.user_issues_in_repo(self.username, repo["full_name"])
            issues.extend(issues_tmp)
        with open(self.user_cache_dir / "issues.json", 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=4)
        # review
        review_prs = []
        for repo in repos:
            reviews_tmp = load_user_data.user_review_prs_in_repo(self.username, repo["full_name"])
            review_prs.extend(reviews_tmp)
        with open(self.user_cache_dir / "review_prs.json", 'w', encoding='utf-8') as f:
            json.dump(review_prs, f, ensure_ascii=False, indent=4)
        # comment
        comment_prs_issues = []
        for repo in repos:
            comments_tmp = load_user_data.user_comment_prs_issues_in_repo(self.username, repo["full_name"])
            comment_prs_issues.extend(comments_tmp)
        with open(self.user_cache_dir / "comment_prs_issues.json", 'w', encoding='utf-8') as f:
            json.dump(comment_prs_issues, f, ensure_ascii=False, indent=4)
        # merge权限
        merge_repos = []
        for repo in repos:
            flag = load_user_data.user_merge_permission_in_repo(self.username, repo["full_name"])
            if flag:
                merge_repos.append(repo["full_name"])
        # print(f"{username} has merge permission in {len(merge_repos)} repositories: {merge_repos}")
        with open(self.user_cache_dir / "repos_can_merge.json", 'w', encoding='utf-8') as f:
            json.dump(merge_repos, f, ensure_ascii=False, indent=4)

    
    def analyze_skills(self) -> dict:
        """
        分析技能，返回技能列表。
        """
        # 读取数据
        self.fetch_data()  # ---调试时注释掉，避免重复获取---

        nowdate = get_now_date()
        nowdate = datetime.fromisoformat(nowdate).replace(tzinfo=timezone.utc)
        basic_info_data = basic_info.basic_info(self.task_name)
        experience_data, fig_repo_contrib, fig_recent_contrib = experience.experience(self.task_name, nowdate)
        fig_lang, fig_domain_bytes, solving_score, fig_solving = hardskill.hardskill(self.task_name, nowdate)
        fig_consistency, fig_activeness, time_mgmt, comm_score, fig_comm, sample_commits = softskill.softskill(self.task_name)

        # 返回结果
        result = {
            "date": nowdate.strftime("%Y-%m-%d"),
            "username": self.username,
            "basic_info": basic_info_data,
            "experience": {
                "data": experience_data,
                "fig_repo_contrib": fig_repo_contrib,
                "fig_recent_contrib": fig_recent_contrib
            },
            "hardskill": {
                "fig_lang": fig_lang,
                "fig_domain_bytes": fig_domain_bytes,
                "solving_score": solving_score,
                "fig_solving": fig_solving
            },
            "softskill": {
                "fig_consistency": fig_consistency,
                "fig_activeness": fig_activeness,
                "time_mgmt": time_mgmt,
                "comm_score": comm_score,
                "fig_comm": fig_comm,
                "sample_commits": sample_commits
            }
        }
        return result

    def clean_up(self):
        """
        分析完成后删除临时目录。
        """
        import shutil
        if self.user_cache_dir.exists():
            shutil.rmtree(self.user_cache_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_up()
        # pass  # 调试时不删除临时目录

if __name__ == "__main__":

    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    # username = 'dune0310421'
    username = 'Aurelius84'

    # 计时
    start_time = datetime.now()

    analyzer = DeveloperAnalyzer(username)
    results = analyzer.analyze_skills()
    print(results)

    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Completed in {duration}.")

    # info = user_info(token, username)
    # print(f"User {username} info: {info}")