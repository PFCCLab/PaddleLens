import time
import json
from tqdm import tqdm
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from github import Github
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from time import sleep

from utils.request_github import request_github
from get_data.get_repo_readme import get_repo_readme
from utils.content_processor import get_domain
from config import GITHUB_TOKEN

logger = logging.getLogger(__name__)
GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"

def get_org_repos(gh: Github, org_name: str) -> list[dict]:
    """
    使用github rest api获取指定组织的所有仓库(速度较慢，不推荐使用)
    """
    org = request_github(gh, gh.get_organization, (org_name,))
    if not org:
        logger.error(f"Organization {org_name} not found.")
        return []

    repos = org.get_repos()  # 获取组织的所有仓库
    repo_list = []

    logger.info(f"Fetching repositories for organization: {org_name}, total: {repos.totalCount}")
    for repo in tqdm(repos):
        repo_info = {
            "full_name": repo.full_name,
            "private": repo.private,
            "description": repo.description,
            "fork": repo.fork,
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
            "archived": repo.archived,
            "stargazers_count": repo.stargazers_count,
            "watchers_count": repo.subscribers_count,
            "forks_count": repo.forks_count,
            "size": repo.size,
            "language": repo.language,
            "topics": repo.topics,
        }

        repo_list.append(repo_info)

    return repo_list

def get_org_repos_graphql(token: str, org_name: str, until: str) -> list[dict]:
    """
    使用GraphQL获取指定组织的所有仓库
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

    query = """
    query($org: String!, $cursor: String) {
        organization(login: $org) {
            repositories(first: 100, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                totalCount
                nodes {
                    nameWithOwner
                    isPrivate
                    description
                    isFork
                    isArchived
                    createdAt
                    updatedAt
                    stargazerCount
                    forkCount
                    primaryLanguage {
                        name
                    }
                    repositoryTopics(first: 10) {
                        nodes {
                            topic { name }
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

    variables = {"org": org_name, "cursor": None}
    repo_list = []
    detail_tasks = []
    has_next = True

    pbar = tqdm(desc=f"Fetching repos from {org_name}", unit="repo", dynamic_ncols=True)

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
            print(f"请求出错：{e}, 正在等待后重试...")
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

        org_data = data.get("data", {}).get("organization", {})
        if not org_data:
            print("未获取到组织数据")
            break

        repos_data = org_data["repositories"]
        nodes = repos_data["nodes"]

        for repo in nodes:
            # 跳过私有仓库
            if repo["isPrivate"]:
                continue
            # 跳过指定时间之后创建的仓库
            until_dt = datetime.fromisoformat(until).replace(tzinfo=timezone.utc) if until else None
            if until_dt and repo["createdAt"] > until_dt.isoformat():
                continue

            repo_info = {
                "full_name": repo["nameWithOwner"],
                "private": repo["isPrivate"],
                "description": repo["description"],
                "fork": repo["isFork"],
                "created_at": repo["createdAt"],
                "updated_at": repo["updatedAt"],
                "archived": repo["isArchived"],
                "stargazers_count": repo["stargazerCount"],
                "forks_count": repo["forkCount"],
                "language": repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else None,
                "topics": [t["topic"]["name"] for t in repo["repositoryTopics"]["nodes"]],
                # 省略 watchers_count，GraphQL获取不了
            }
            # 单独线程获取watchers_count
            detail_tasks.append((repo_info["full_name"], repo_info))
            repo_list.append(repo_info)
            pbar.update(1)
        has_next = repos_data["pageInfo"]["hasNextPage"]
        variables["cursor"] = repos_data["pageInfo"]["endCursor"]

    pbar.close()

    def fetch_repo_detail(full_name: str, repo_info: dict):
        try:
            url = f"https://api.github.com/repos/{full_name}"
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
            repo_info["watchers_count"] = data.get("subscribers_count", 0)
            # repo_info["size"] = data.get("size", 0)
        except Exception as e:
            print(f"Failed to fetch repo detail for {full_name}: {e}")
            repo_info["watchers_count"] = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(fetch_repo_detail, full_name, repo_info)
            for full_name, repo_info in detail_tasks
        ]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching repo details", dynamic_ncols=True):
            try:
                future.result()
            except Exception as e:
                print("Error in fetching repo detail:", e)

    return repo_list

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )

    # gh = Github(GITHUB_TOKEN)
    # 获取paddle相关所有repo
    # repos = get_org_repos(gh, "PaddlePaddle")
    # repos.extend(get_org_repos(gh, "PFCCLab"))
    # repos.extend(get_org_repos(gh, "baidu"))
    repos = get_org_repos_graphql(GITHUB_TOKEN, "PaddlePaddle", until="2025-10-17")
    repos.extend(get_org_repos_graphql(GITHUB_TOKEN, "PFCCLab", until="2025-10-17"))
    with open("data/paddle_repos1.json", "w", newline="", encoding="utf-8") as f:
        json.dump(repos, f, indent=4, ensure_ascii=False)