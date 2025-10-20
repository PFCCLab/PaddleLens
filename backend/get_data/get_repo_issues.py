import time
import json
from turtle import update
import comm
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import logging
import requests
from github import Github
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from time import sleep

from get_data.get_repo_prs import get_pr_comments_graphql, get_pr_files_graphql, get_pr_reviews_graphql, get_pr_commits_graphql
from utils.request_github import request_github
from config import GITHUB_TOKEN

logger = logging.getLogger(__name__)
GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
token_list = [
    GITHUB_TOKEN,
]

def fetch_issue_info(gh, repo_full_name, issue_num):
    """
    获取指定issue的详细信息
    """
    issue = request_github(gh, lambda n: gh.get_repo(repo_full_name).get_issue(number=n), (issue_num,))

    try:
        issue_info = {
            'repo': issue.repository.full_name,
            'number': issue.number,
            'title': issue.title,
            'body': issue.body,
            'state': issue.state,
            'user': issue.user.login if issue.user else None,
            'closed_by': issue.closed_by.login if issue.closed_by else None,
            'created_at': issue.created_at.isoformat(),
            'updated_at': issue.updated_at.isoformat(),
            'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
        }
        # 获取comments
        issue_info['comments_count'] = []
        if issue.comments > 0:
            # comments = issue.get_comments()
            comments = request_github(gh, issue.get_comments, ())
            comments_list = []
            for comment in comments:
                comment_author = comment.user.login if comment.user else None
                comments_list.append(comment_author)
            issue_info['comments_count'] = comments_list
        # 获取labels
        issue_info['labels'] = []
        if issue.labels:
            labels_list = []
            for label in issue.labels:
                labels_list.append(label.name)
            issue_info['labels'] = labels_list
        return issue_info
    except Exception as e:
        logger.error(f"Error fetching issue {issue_num}: {e}")
        return {
            'repo': repo_full_name,
            'issue_number': issue_num,
            'error': str(e)
            }

def fetch_issue_info_graphql(token, repo_full_name, issue_num):
    """
    使用GitHub GraphQL获取指定issue的信息（替代 REST API）
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    repo_owner, repo_name = repo_full_name.split('/')
    query = """
    query ($owner: String!, $name: String!, $issueNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            issue(number: $issueNumber) {
                number
                title
                body
                state
                createdAt
                updatedAt
                closedAt
                author {
                    login
                }
                labels(first: 10) {
                    nodes {
                        name
                    }
                }
                comments(first: 100, after: $cursor) {
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
            }
        }
    }
    """

    variables = {
        "owner": repo_owner,
        "name": repo_name,
        "issueNumber": issue_num,
        "cursor": None  # 用于分页
    }

    response = requests.post(GITHUB_GRAPHQL_ENDPOINT, headers=headers, json={'query': query, 'variables': variables})
    if response.status_code != 200:
        return {"error": f"GraphQL query failed: {response.text}", "issue_number": issue_num}

    data = response.json()
    try:
        issue = data['data']['repository']['issue']
        if issue is None:
            return {"error": "Issue not found", "issue_number": issue_num}

        issue_info = {
            "repo": repo_full_name,
            "number": issue["number"],
            "title": issue["title"],
            "body": issue["body"],
            "state": issue["state"],
            "user": issue["author"]["login"] if issue["author"] else None,
            "closed_by": None,  # GraphQL 暂无
            "created_at": issue["createdAt"],
            "updated_at": issue["updatedAt"],
            "closed_at": issue["closedAt"],
            "comments_count": [
                c["author"]["login"] if c["author"] else None for c in issue["comments"]["nodes"]
            ],
            "labels": [label["name"] for label in issue["labels"]["nodes"]]
        }

        return issue_info
    except Exception as e:
        logger.error(f"Error fetching issue {issue_num}: {e}")
        return {
            'repo': repo_full_name,
            'issue_number': issue_num,
            'error': str(e)
            }
    
def get_repo_prs_n(repo_full_name):
    """
    获取指定仓库的所有PR的number, 用于识别issue编号
    """
    gh = Github(token_list[0])

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

    return pr_num_list

def get_repo_issues(repo_full_name):
    """
    获取指定仓库的所有issue
    """
    gh_list = [Github(token) for token in token_list]
    gh = gh_list[0]  # 使用第一个令牌的GitHub实例

    issues = request_github(
        gh, lambda r: gh.get_repo(r).get_issues(state='all', sort='created', direction='desc'),
        (repo_full_name, )
    ) 
    
    if issues == None:
        logger.warning(f"No issues found for repository: {repo_full_name}")
        return []
    
    issue_num_now = 0
    for issue in issues:
        issue_num_now = issue.number
        break

    issue_num_list = [i + 1 for i in range(issue_num_now)]
    # 去除其中的pr
    pr_num_list = get_repo_prs_n(repo_full_name)
    issue_num_list = [num for num in issue_num_list if num not in pr_num_list]
    
    logger.info(f"Fetching issues for repository: {repo_full_name}, total: {len(issue_num_list)}")
    issue_list = []
    with ThreadPoolExecutor(max_workers=3 * len(gh_list)) as executor:
        # 分配任务到令牌 gh
        future_to_issue = {executor.submit(fetch_issue_info, gh_list[i % len(gh_list)], repo_full_name, issue_num): issue_num for i, issue_num in enumerate(issue_num_list)}
        # future_to_issue = {executor.submit(fetch_issue_info_graphql, token_list[i % len(token_list)], repo_full_name, issue_num): issue_num for i, issue_num in enumerate(issue_num_list)}

        for future in tqdm(as_completed(future_to_issue), total=len(future_to_issue), desc=f"Processing {repo_full_name}"):
            issue_info = future.result()
            if 'error' in issue_info:
                logging.error(f"Error fetching issue {issue_info['issue_number']} for repository {repo_full_name}: {issue_info['error']}")
            issue_list.append(issue_info)
    return issue_list

def get_issue_comments_graphql(token: str, repo_full_name: str, issue_num: int) -> list[list]:
    """
    使用graphql获取指定issue的评论信息
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

    owner, name = repo_full_name.split('/')
    query = """
    query ($owner: String!, $name: String!, $issueNumber: Int!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            issue(number: $issueNumber) {
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
        "owner": owner,
        "name": name,
        "issueNumber": issue_num,
        "cursor": None
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

        try:
            issue_data = data.get("data", {}).get("repository", {}).get("issue")
        except Exception as e:
            issue_data = None
        if issue_data is None:
            print(f"Issue #{issue_num} 不存在或获取失败。")
            break

        comments_data = issue_data.get("comments")
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

def update_repo_issues_graphql(token: str, repo_full_name: str, since: str, until: str) -> list[dict]:
    """
    使用 graphql 增量获取指定repo中的 Issue 和 PR
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

    # owner, name = repo_full_name.split("/")
    query = """
    query ($queryString: String!, $cursor: String) {
        search(query: $queryString, type: ISSUE, first: 100, after: $cursor) {
            pageInfo {
                hasNextPage
                endCursor
            }
            nodes {
                __typename
                ... on Issue {
                    number
                    title
                    body
                    state
                    author {
                        login
                    }
                    timelineItems(last: 1, itemTypes: [CLOSED_EVENT]) {
                        nodes {
                            ... on ClosedEvent {
                                actor {
                                    login
                                }
                            }
                        }
                    }
                    createdAt
                    updatedAt
                    closedAt
                    labels(first: 10) {
                        nodes {
                            name
                        }
                    }
                }
                ... on PullRequest {
                    number
                    title
                    body
                    state
                    merged
                    author {
                        login
                    }
                    mergedBy {
                        login
                    }
                    createdAt
                    updatedAt
                    closedAt
                    additions
                    deletions
                    changedFiles
                }
            }
        }
        rateLimit {
            remaining
            resetAt
        }
    }
    """

    query_string = f'repo:{repo_full_name} updated:{since}..{until}'
    variables = {
        "queryString": query_string,
        "cursor": None
    }

    results = []
    detail_tasks = []
    has_next = True

    pbar = tqdm(desc=f"Fetching issues&prs from {repo_full_name}", unit="issue", dynamic_ncols=True)

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

        if "errors" in data:
            print("GraphQL 错误:", data["errors"])
            break

        search_data = data.get("data", {}).get("search", {})
        page_info = search_data["pageInfo"]
        nodes = search_data.get("nodes", [])

        for item in nodes:
            if item["__typename"] == "Issue":
                closed_by = item["timelineItems"]["nodes"][0]["actor"]["login"] if item["timelineItems"]["nodes"] else None
                item_info = {
                    "repo": repo_full_name,
                    "type": item["__typename"],  # Issue
                    "number": item["number"],
                    "title": item["title"],
                    "body": item["body"],
                    "state": item["state"],
                    "user": item["author"]["login"] if item["author"] else None,
                    "closed_by": closed_by,
                    "created_at": item["createdAt"],
                    "updated_at": item["updatedAt"],
                    "closed_at": item.get("closedAt", None),
                    "labels": [label["name"] for label in item["labels"]["nodes"]],
                }

            elif item["__typename"] == "PullRequest":
                item_info = {
                    "repo": repo_full_name,
                    "type": item["__typename"],  # PullRequest
                    "number": item["number"],
                    "title": item["title"],
                    "body": item["body"],
                    "state": item["state"],
                    "merged": item.get("merged", False),
                    "user": item["author"]["login"] if item["author"] else None,
                    "merged_by": item["mergedBy"]["login"] if item.get("mergedBy") else None,
                    "created_at": item["createdAt"],
                    "updated_at": item["updatedAt"],
                    "closed_at": item.get("closedAt", None),
                    "additions": item.get("additions", 0),
                    "deletions": item.get("deletions", 0),
                    "changed_files": item.get("changedFiles", 0),
                }
            else:
                continue
            detail_tasks.append((item["__typename"], item["number"], item_info)) # 加入任务池，后续并发采集comments等信息
            results.append(item_info)
            pbar.update(1)

        has_next = page_info["hasNextPage"]
        variables["cursor"] = page_info["endCursor"]

    pbar.close()

    # 并发补足详情信息（comment、commits、reviews、files）
    def enrich_details(typename: str, number: int, item_dict: dict):
        if typename == "Issue":
            item_dict["comment_by"] = get_issue_comments_graphql(token, repo_full_name, number)
        elif typename == "PullRequest":
            item_dict["commits"] = get_pr_commits_graphql(token, repo_full_name, number)
            item_dict["files"] = get_pr_files_graphql(token, repo_full_name, number)
            item_dict["comment_by"] = get_pr_comments_graphql(token, repo_full_name, number)
            item_dict["review_by"] = get_pr_reviews_graphql(token, repo_full_name, number)

    with ThreadPoolExecutor(max_workers=9) as executor:
        futures = [
            executor.submit(enrich_details, typename, number, base_info)
            for typename, number, base_info in detail_tasks
        ]
        for future in tqdm(as_completed(futures), total=len(futures), dynamic_ncols=True):
            try:
                future.result()
            except Exception as e:
                typename, number, base_info = detail_tasks[futures.index(future)]
                print("Fetching item details failed:", e, f"Type: {typename}, Number: {number}")
    return results

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )
    
    # # 获取所有仓库的issue
    # with open("data/paddle_repos.json", "r", encoding="utf-8") as f:
    #     repos = json.load(f)
    # # issue_list = []
    # for repo in repos:
    #     # 获取每个仓库的issue信息
    #     issues = get_repo_issues(repo['full_name'])
    #     # if issues:
    #     #     issue_list.extend(issues)
    #     repo_owner, repo_name = repo['full_name'].split('/')
    #     with open(f"data/paddle_issues/{repo_owner}_{repo_name}_issues.json", "w", newline="", encoding="utf-8") as f:
    #         json.dump(issues, f, indent=4, ensure_ascii=False)
    # # with open("data/paddle_issues.json", "w", newline="", encoding="utf-8") as f:
    # #     json.dump(issue_list, f, indent=4, ensure_ascii=False)

    # 更新指定repo的issue(包含pr)
    res = update_repo_issues_graphql(token_list[0], "PaddlePaddle/PaddleOCR", "2025-10-01", "2025-10-15")
    with open("cache/test_issues.json", "w", newline="", encoding="utf-8") as f:
        json.dump(res, f, indent=4, ensure_ascii=False)

    # # 获取指定issue的comments
    # res = get_issue_comments_graphql(token_list[0], "PaddlePaddle/PaddleOCR", 1)
    # with open("cache/test_issue_comments.json", "w", newline="", encoding="utf-8") as f:
    #     json.dump(res, f, indent=4, ensure_ascii=False)