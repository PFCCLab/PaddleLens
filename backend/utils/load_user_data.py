import json
from datetime import datetime, timezone
import logging

from utils.manage_data_update_time import get_now_date

def user_commits_in_repo(username, repo_full_name):
    """
    获取指定用户在指定仓库的commit信息
    """
    # logger.info(f"Fetching commits for {username} in repository {repo_full_name}")
    repo_owner, repo_name = repo_full_name.split('/')
    commit_list = []
    # 获取paddle相关仓库的commit信息，本地读取
    try:
        with open(f"data/paddle_commits/{repo_owner}_{repo_name}_commits.json", 'r', encoding='utf-8') as f:
            commits = json.load(f)
    except Exception as e:
        logger.error(f"Error fetching commits for {repo_full_name}: {e}")
        return commit_list
    
    nowdate = datetime.fromisoformat(get_now_date()).replace(tzinfo=timezone.utc)
    for commit in commits:
        try:
            commit_time = datetime.fromisoformat(commit['created_at'])
        except ValueError:
            continue
        if commit_time > nowdate:
            continue
        if commit['author'] == username:
            commit_list.append(commit)
    return commit_list

def user_prs_in_repo(username, repo_full_name):
    """
    获取指定用户在指定仓库的pr信息
    """
    # logger.info(f"Fetching prs for {username} in repository {repo_full_name}")
    repo_owner, repo_name = repo_full_name.split('/')
    pr_list = []
    try:
        with open(f"data/paddle_prs/{repo_owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
    except Exception as e:
        logger.error(f"Error fetching prs for {repo_full_name}: {e}")
        return pr_list
    
    nowdate = datetime.fromisoformat(get_now_date()).replace(tzinfo=timezone.utc)
    for pr in prs:
        try:
            pr_time = datetime.fromisoformat(pr['created_at'])
        except ValueError:
            continue
        if pr_time > nowdate:
            continue
        if pr['user'] == username:
            pr_list.append(pr)
    return pr_list

def user_issues_in_repo(username, repo_full_name):
    """
    获取指定用户在指定仓库的issue信息
    """
    # logger.info(f"Fetching issues for {username} in repository {repo_full_name}")
    repo_owner, repo_name = repo_full_name.split('/')
    issue_list = []
    try:
        with open(f"data/paddle_issues/{repo_owner}_{repo_name}_issues.json", 'r', encoding='utf-8') as f:
            issues = json.load(f)
    except Exception as e:
        logger.error(f"Error fetching issues for {repo_full_name}: {e}")
        return issue_list
    
    nowdate = datetime.fromisoformat(get_now_date()).replace(tzinfo=timezone.utc)
    for issue in issues:
        if 'error' in issue: # 可能会有deleted issue
            continue
        try:
            issue_time = datetime.fromisoformat(issue['created_at'])
        except ValueError:
            continue
        if issue_time > nowdate:
            continue
        if issue['user'] == username:
            issue_list.append(issue)
    return issue_list

def user_merge_permission_in_repo(username, repo_full_name):
    """
    获取指定用户的merge权限仓库
    """
    flag = False
    try:
        repo_owner, repo_name = repo_full_name.split('/')
        with open(f"data/paddle_prs/{repo_owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
    except Exception as e:
        logger.error(f"Error fetching prs for {repo_full_name}: {e}")
        return flag
    for pr in prs:
        if 'merged_by' not in pr or pr['merged_by'] == None:
            continue
        else:
            if pr['merged_by'] == username:
                flag = True
                break
    return flag

def user_review_prs_in_repo(username, repo_full_name):
    """
    获取指定用户在指定仓库中有review的pr信息
    """
    # logger.info(f"Fetching reviews for {username} in repository {repo_full_name}")
    repo_owner, repo_name = repo_full_name.split('/')
    review_pr_list = []
    try:
        with open(f"data/paddle_prs/{repo_owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
    except Exception as e:
        logger.error(f"Error fetching prs for {repo_full_name}: {e}")
        return review_pr_list

    nowdate = datetime.fromisoformat(get_now_date()).replace(tzinfo=timezone.utc)
    for pr in prs:
        try:
            pr_time = datetime.fromisoformat(pr['created_at'])
        except ValueError:
            continue
        if pr_time > nowdate:
            continue
        if 'review_by' not in pr or pr['review_by'] == None:
            continue
        for review in pr['review_by']:
            if review[0] == username:
                review_pr_list.append(pr)
                break
    return review_pr_list

def user_comment_prs_issues_in_repo(username, repo_full_name):
    """
    获取指定用户在指定仓库中有comment的pr和issue信息
    """
    # logger.info(f"Fetching comments for {username} in repository {repo_full_name}")
    repo_owner, repo_name = repo_full_name.split('/')

    nowdate = datetime.fromisoformat(get_now_date()).replace(tzinfo=timezone.utc)
    comment_prs_issues_list = []
    # pr评论
    try:
        with open(f"data/paddle_prs/{repo_owner}_{repo_name}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
        for pr in prs:
            try:
                pr_time = datetime.fromisoformat(pr['created_at'])
            except ValueError:
                continue
            if pr_time > nowdate:
                continue
            if 'comment_by' in pr and pr['comment_by']:
                for comment in pr['comment_by']:
                    if comment[0] == username:
                        comment_prs_issues_list.append(pr)
                        break
    except Exception as e:
        logger.error(f"Error fetching PR comments for {repo_full_name}: {e}")
    # issue评论
    try:
        with open(f"data/paddle_issues/{repo_owner}_{repo_name}_issues.json", 'r', encoding='utf-8') as f:
            issues = json.load(f)
        for issue in issues:
            if 'error' in issue: # 可能会有deleted issue
                continue
            try:
                issue_time = datetime.fromisoformat(issue['created_at'])
            except ValueError:
                continue
            if issue_time > nowdate:
                continue
            if issue['comment_by']:
                for comment in issue['comment_by']:
                    if comment[0] == username:
                        comment_prs_issues_list.append(issue)
                        break
    except Exception as e:
        logger.error(f"Error fetching issue comments for {repo_full_name}: {e}")

    return comment_prs_issues_list

if __name__ == "__main__":

    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    token = ''
    # username = 'dune0310421'
    username = 'Aurelius84'

    # info = user_info(token, username)
    # print(f"User {username} info: {info}")
