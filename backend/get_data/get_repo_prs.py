import time
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import requests
from datetime import datetime, timezone
from github import Github
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from time import sleep

from utils.request_github import request_github
from utils.content_processor import get_pr_type
from config import GITHUB_TOKEN

logger = logging.getLogger(__name__)
GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
token_list = [
    GITHUB_TOKEN,
]

def fetch_pr_info(gh, repo_full_name, pr_num):
    """
    获取PR的详细信息：使用特定的 gh 获取
    """
    pr = request_github(gh, lambda n: gh.get_repo(repo_full_name).get_pull(n), (pr_num,))

    try:
        pr_info = {
            'repo': pr.base.repo.full_name,
            'number': pr.number,
            'title': pr.title,
            'body': pr.body,
            'issue_number': pr.issue_url.split('/')[-1] if pr.issue_url else None,
            'state': pr.state,
            'merged': pr.merged,
            'user': pr.user.login if pr.user else None,
            'merged_by': pr.merged_by.login if pr.merged_by else None,
            'created_at': pr.created_at.isoformat(),
            'closed_at': pr.closed_at.isoformat() if pr.closed_at else None,
            'additions': pr.additions,
            'deletions': pr.deletions,
            'changed_files': pr.changed_files,
        }
        # 获取commits sha
        # commits = pr.get_commits()
        commits = request_github(gh, pr.get_commits, ())
        pr_info['commits'] = [commit.sha for commit in commits]
        # 获取comments
        pr_info['comment_by'] = []
        if pr.comments > 0:
            # comments = pr.get_issue_comments()
            comments = request_github(gh, pr.get_issue_comments, ())
            comments_list = []
            for comment in comments:
                comment_author = comment.user.login if comment.user else None
                comment_time = comment.created_at.isoformat() if comment.created_at else None
                comments_list.append((comment_author, comment_time))
            pr_info['comment_by'] = comments_list
        # 获取review comments
        pr_info['review_by'] = []
        if pr.review_comments > 0:
            # review_comments = pr.get_review_comments()
            review_comments = request_github(gh, pr.get_review_comments, ())
            review_comments_list = []
            for comment in review_comments:
                comment_author = comment.user.login if comment.user else None
                comment_time = comment.created_at.isoformat() if comment.created_at else None
                review_comments_list.append((comment_author, comment_time))
            pr_info['review_by'] = review_comments_list
        # 获取files
        pr_files = pr.get_files()
        pr_info['files'] = []
        if pr_files:
            for file in pr_files:
                file_info = {
                    'filename': file.filename,
                    'status': file.status,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes,
                }
                pr_info['files'].append(file_info)
        # 获取类型
        pr_info['type'] = get_pr_type(pr.title, pr.body)
        return pr_info
    except Exception as e:
        logger.error(f"Error fetching PR {pr.number} for repository {pr.base.repo.full_name}: {e}")
        return {
            'repo': repo_full_name,
            'number': pr.number,
            'error': str(e)
        }

def fetch_pr_info_graphql(token, repo_full_name, pr_num):
    """
    使用GitHub GraphQL获取指定pr的信息（替代 REST API）
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    repo_owner, repo_name = repo_full_name.split('/')
    query = """
    query ($owner: String!, $name: String!, $prNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
                number
                title
                body
                state
                merged
                createdAt
                closedAt
                additions
                deletions
                changedFiles
                author {
                    login
                }
                mergedBy {
                    login
                }
                commits(first: 100, after: $commitsCursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        commit {
                            oid
                        }
                    }
                }
                comments(first: 100, after: $commentsCursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        author {
                            login
                        }
                    }
                }
                reviewThreads(first: 100, after: $reviewsCursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        comments(first: 100) {
                            nodes {
                                author {
                                    login
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """

    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "prNumber": pr_num,
        "cursor": None  # 用于分页
    }

    response = requests.post(GITHUB_GRAPHQL_ENDPOINT, headers=headers, json={'query': query, 'variables': variables})
    if response.status_code != 200:
        return {"error": f"GraphQL query failed: {response.text}", "pr_number": pr_num}

    data = response.json()
    try:
        pr = data['data']['repository']['pullRequest']
        if pr is None:
            return {"error": "Pr not found", "pr_number": pr_num}

        pr_info = {
            "repo": repo_full_name,
            "number": pr['number'],
            "title": pr['title'],
            "body": pr['body'],
            "state": pr['state'],
            "merged": pr['merged'],
            "user": pr['author']['login'] if pr['author'] else None,
            "merged_by": pr['mergedBy']['login'] if pr['mergedBy'] else None,
            "created_at": pr['createdAt'],
            "closed_at": pr['closedAt'],
            "additions": pr['additions'],
            "deletions": pr['deletions'],
            "changed_files": pr['changedFiles'],
            "commits": [c['commit']['oid'] for c in pr['commits']['nodes']],
            "comment_by": [c['author']['login'] for c in pr['comments']['nodes'] if c['author']],
            "review_by": list({rc['author']['login']
                               for rt in pr['reviewThreads']['nodes']
                               for rc in rt['comments']['nodes']
                               if rc['author']}),
        }

        return pr_info
    except Exception as e:
        logger.error(f"Error fetching PR {pr.number} for repository {pr.base.repo.full_name}: {e}")
        return {
            'repo': repo_full_name,
            'number': pr.number,
            'error': str(e)
        }

def get_repo_prs(repo_full_name):
    """
    获取指定仓库的所有PR
    """
    gh_list = [Github(token) for token in token_list]
    gh = gh_list[0]  # 使用第一个令牌的GitHub实例

    prs = request_github(
        gh, lambda r: gh.get_repo(r).get_pulls(state='all', sort='created', direction='desc'),
        (repo_full_name, )
    )
    if prs == None:
        logger.warning(f"No PRs found for repository: {repo_full_name}")
        return []
    
    pr_num_list = []
    for pr in tqdm(prs):
        pr_num_list.append(pr.number)
    
    logger.info(f"Fetching PRs for repository: {repo_full_name}, total: {len(pr_num_list)}")
    pr_list = []
    
    # 用 ThreadPoolExecutor 并行化处理 PR
    with ThreadPoolExecutor(max_workers=3 * len(gh_list)) as executor:
        # 分配任务到令牌 gh
        future_to_pr = {executor.submit(fetch_pr_info, gh_list[i % len(gh_list)], repo_full_name, pr_num): pr_num for i, pr_num in enumerate(pr_num_list)}

        for future in tqdm(as_completed(future_to_pr), total=len(future_to_pr), desc=f"Processing {repo_full_name}"):
            result = future.result()  # 获取线程结束后的结果
            if 'error' in result:
                logging.error(f"Error fetching PR {result['pr_number']} for repository {repo_full_name}: {result['error']}")
            pr_list.append(result)

    return pr_list

def get_pr_comments_graphql(token: str, repo_full_name: str, pr_num: int) -> list[list]:
    """
    使用graphql获取指定pr的评论信息
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    repo_owner, repo_name = repo_full_name.split('/')
    query = """
    query ($owner: String!, $name: String!, $prNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
                comments(first: 100, after: $cursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        author {
                            login
                        }
                        createdAt
                    }
                }
            }
        }
        rateLimit {
            remaining
            resetAt
        }
    }
    """
    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "prNumber": pr_num,
        "cursor": None  # 用于分页
    }
    comments = []
    has_next = True
    while has_next:
        try:
            response = session.post(
                GITHUB_GRAPHQL_ENDPOINT,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"请求出错：{e}，等待后重试...")
            sleep(2)
            continue

        # 检查 rateLimit 信息
        rate_info = data.get("data", {}).get("rateLimit")
        if rate_info:
            remaining = rate_info.get("remaining", 0)
            reset_at_str = rate_info.get("resetAt")
            if remaining == 0 and reset_at_str:
                reset_time = datetime.fromisoformat(reset_at_str.rstrip("Z")).replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                sleep_seconds = (reset_time - now).total_seconds() + 5  # 加 5 秒缓冲
                sleep_seconds = max(sleep_seconds, 0)
                print(f"Rate limit hit. 等待 {int(sleep_seconds)} 秒直到 {reset_time} 后重试...")
                sleep(sleep_seconds)
                continue

        if "errors" in data:
            print("GraphQL 错误:", data["errors"])
            break

        pr_data = data['data']['repository']['pullRequest']
        if pr_data is None:
            # print(f"PR #{pr_num} 不存在或获取失败。")
            break

        comments_data = pr_data.get("comments")
        if not comments_data:
            break

        nodes = comments_data.get("nodes") or []
        for node in nodes:
            author = node.get("author", {})
            author_login = author.get("login") if author else None
            created_at = node.get("createdAt")
            if created_at:
                comments.append([author_login, created_at])

        page_info = comments_data.get("pageInfo") or {}
        has_next = page_info.get("hasNextPage", False)
        variables["cursor"] = page_info.get("endCursor")
        
    return comments

def get_pr_files_graphql(token: str, repo_full_name: str, pr_num: int) -> list[dict]:
    """
    使用graphql获取指定pr的文件变更信息
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    repo_owner, repo_name = repo_full_name.split('/')
    query = """
    query ($owner: String!, $name: String!, $prNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
                files(first: 100, after: $cursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        node {
                            path
                            additions
                            deletions
                            changeType  # ADDED, MODIFIED, REMOVED, RENAMED, COPIED, CHANGED
                        }
                    }
                }
            }
        }
        rateLimit {
            remaining
            resetAt
        }
    }
    """

    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "prNumber": pr_num,
        "cursor": None
    }

    files = []
    has_next = True

    while has_next:
        try:
            response = session.post(
                GITHUB_GRAPHQL_ENDPOINT,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"请求出错：{e}，等待后重试...")
            sleep(2)
            continue

        # 检查 rateLimit 信息
        rate_info = data.get("data", {}).get("rateLimit")
        if rate_info:
            remaining = rate_info.get("remaining", 0)
            reset_at_str = rate_info.get("resetAt")
            if remaining == 0 and reset_at_str:
                reset_time = datetime.fromisoformat(reset_at_str.rstrip("Z")).replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                sleep_seconds = (reset_time - now).total_seconds() + 5  # 加 5 秒缓冲
                sleep_seconds = max(sleep_seconds, 0)
                print(f"Rate limit hit. 等待 {int(sleep_seconds)} 秒直到 {reset_time} 后重试...")
                sleep(sleep_seconds)
                continue

        if "errors" in data:
            print("GraphQL 错误:", data["errors"])
            return []

        pr_data = data.get("data", {}).get("repository", {}).get("pullRequest")
        if pr_data is None:
            # print(f"PR #{pr_num} 不存在或获取失败。")
            break

        files_data = pr_data.get("files")
        if not files_data:
            # print(f"[Warning] PR #{pr_num} 没有 files 字段")
            break

        file_edges = files_data.get("edges") or []
        for edge in file_edges:
            node = edge.get("node")
            if node:
                file_info = {
                    "filename": node["path"],
                    "status": node["changeType"].lower(),
                    "additions": node["additions"],
                    "deletions": node["deletions"],
                    "changes": node["additions"] + node["deletions"]
                }
                files.append(file_info)

        page_info = pr_data["files"]["pageInfo"] or {}
        has_next = page_info.get("hasNextPage", False)
        variables["cursor"] = page_info.get("endCursor")

    return files

def get_pr_reviews_graphql(token: str, repo_full_name: str, pr_num: int) -> list[list]:
    """
    使用graphql获取指定pr的review信息
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    repo_owner, repo_name = repo_full_name.split('/')
    query = """
    query ($owner: String!, $name: String!, $prNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
                reviewThreads(first: 100, after: $cursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        comments(first: 50) {
                            nodes {
                                author {
                                login
                                }
                                createdAt
                            }
                        }
                    }
                }
            }
        }
        rateLimit {
            remaining
            resetAt
        }
    }
    """
    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "prNumber": pr_num,
        "cursor": None
    }

    reviews = []
    has_next = True

    while has_next:
        try:
            response = session.post(
                GITHUB_GRAPHQL_ENDPOINT,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"请求出错：{e}，等待后重试...")
            sleep(2)
            continue
        
        # 检查 rateLimit 信息
        rate_info = data.get("data", {}).get("rateLimit")
        if rate_info:
            remaining = rate_info.get("remaining", 0)
            reset_at_str = rate_info.get("resetAt")
            if remaining == 0 and reset_at_str:
                reset_time = datetime.fromisoformat(reset_at_str.rstrip("Z")).replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                sleep_seconds = (reset_time - now).total_seconds() + 5  # 加 5 秒缓冲
                sleep_seconds = max(sleep_seconds, 0)
                print(f"Rate limit hit. 等待 {int(sleep_seconds)} 秒直到 {reset_time} 后重试...")
                sleep(sleep_seconds)
                continue

        if "errors" in data:
            print("GraphQL 错误:", data["errors"])
            return []

        pr_data = data.get("data", {}).get("repository", {}).get("pullRequest")
        if pr_data is None:
            # print(f"PR #{pr_num} 不存在或获取失败。")
            break

        review_threads_data = pr_data.get("reviewThreads")
        if not review_threads_data:
            # print(f"[Warning] PR #{pr_num} 无 reviewThreads 数据")
            break
        thread_nodes = review_threads_data.get("nodes", [])
        for thread in thread_nodes:
            comments_data = thread.get("comments", {})
            comment_nodes = comments_data.get("nodes", [])
            for comment in comment_nodes:
                author = comment.get("author", {}).get("login")
                created_at = comment.get("createdAt")
                reviews.append([author, created_at])

        page_info = review_threads_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        variables["cursor"] = page_info.get("endCursor")

    return reviews

def get_pr_commits_graphql(token: str, repo_full_name: str, pr_num: int) -> list[str]:
    """
    使用graphql获取指定pr的所有commit的sha值
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    repo_owner, repo_name = repo_full_name.split('/')

    query = """
    query ($owner: String!, $name: String!, $prNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
                commits(first: 50, after: $cursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        commit {
                            oid
                        }
                    }
                }
            }
        }
        rateLimit {
            remaining
            resetAt
        }
    }
    """

    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "prNumber": pr_num,
        "cursor": None
    }

    commits = []
    has_next = True

    while has_next:
        try:
            response = session.post(
                GITHUB_GRAPHQL_ENDPOINT,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"请求出错：{e}，等待后重试...")
            sleep(2)
            continue

        # 检查 rateLimit 信息
        rate_info = data.get("data", {}).get("rateLimit")
        if rate_info:
            remaining = rate_info.get("remaining", 0)
            reset_at_str = rate_info.get("resetAt")
            if remaining == 0 and reset_at_str:
                reset_time = datetime.fromisoformat(reset_at_str.rstrip("Z")).replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                sleep_seconds = (reset_time - now).total_seconds() + 5  # 加5秒缓冲
                sleep_seconds = max(sleep_seconds, 0)
                print(f"Rate limit hit. 等待 {int(sleep_seconds)} 秒直到 {reset_time} 后重试...")
                sleep(sleep_seconds)
                continue

        if "errors" in data:
            print("GraphQL 错误:", data["errors"])
            return []

        pr_data = data.get("data", {}).get("repository", {}).get("pullRequest")
        if pr_data is None:
            # print(f"PR #{pr_num} 不存在或获取失败。")
            break

        commits_data = pr_data.get("commits")
        if not commits_data:
            # print(f"[Warning] PR #{pr_num} 的 commits 字段为 None")
            break
        nodes = commits_data.get("nodes") or []
        for node in nodes:
            sha = node.get("commit", {}).get("oid")
            if sha:
                commits.append(sha)

        page_info = commits_data.get("pageInfo") or {}
        has_next = page_info.get("hasNextPage", False)
        variables["cursor"] = page_info.get("endCursor")

    return commits

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )

    # # 获取所有仓库的pr
    # with open("data/paddle_repos.json", "r", encoding="utf-8") as f:
    #     repos = json.load(f)
    # # pr_list = []
    # for repo in repos:
    #     # 获取每个仓库的PR信息
    #     prs = get_repo_prs(repo['full_name'])
    #     # if prs:
    #     #     pr_list.extend(prs)
    #     repo_owner, repo_name = repo['full_name'].split('/')
    #     with open(f"data/paddle_prs/{repo_owner}_{repo_name}_prs.json", "w", newline="", encoding="utf-8") as f:
    #         json.dump(prs, f, indent=4, ensure_ascii=False)
    # # with open("data/paddle_prs.json", "w", newline="", encoding="utf-8") as f:
    # #     json.dump(pr_list, f, indent=4, ensure_ascii=False)

    # # 获取指定pr的评论
    # comments = get_pr_comments_graphql(token_list[0], "PaddlePaddle/PaddleOCR", 1)
    # with open("cache/test_pr_comments.json", "w", newline="", encoding="utf-8") as f:
    #     json.dump(comments, f, indent=4, ensure_ascii=False)

    # 获取指定pr的文件变更
    files = get_pr_files_graphql(token_list[0], "PaddlePaddle/PaddleOCR", 15154)
    with open("cache/test_pr_files.json", "w", newline="", encoding="utf-8") as f:
        json.dump(files, f, indent=4, ensure_ascii=False)

    # # 获取指定pr的reviews
    # reviews = get_pr_reviews_graphql(token_list[0], "PaddlePaddle/PaddleOCR", 15154)
    # with open("cache/test_pr_reviews.json", "w", newline="", encoding="utf-8") as f:
    #     json.dump(reviews, f, indent=4, ensure_ascii=False)

    # # 获取指定pr的commit shas
    # commit_shas = get_pr_commits_graphql(token_list[0], "PaddlePaddle/PaddleOCR", 15154)
    # with open("cache/test_pr_commits.json", "w", newline="", encoding="utf-8") as f:
    #     json.dump(commit_shas, f, indent=4, ensure_ascii=False)