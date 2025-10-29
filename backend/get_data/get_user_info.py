import time
import json
from tqdm import tqdm
import logging
from github import Github

from utils.request_github import request_github

logger = logging.getLogger(__name__)
GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
token_list = [
    # '',  # 添加github token
]


def get_user_info(gh, username):
    """
    获取指定用户的基本信息
    """
    logger.info(f"Fetching user info for {username}")
    dvpr = request_github(gh, gh.get_user, (username,))
    if not dvpr:
        logger.error(f"User {username} not found.")
        raise ValueError(f"Github 用户不存在，请重新输入")
    info = {
        "username": username,
        "name": dvpr.name or '',
        "company": dvpr.company or '',
        "location": dvpr.location or '',
        "email": dvpr.email or '',
        "public_repos": dvpr.public_repos,
        "followers": dvpr.followers,
        "following": dvpr.following,
        "created_at": dvpr.created_at.isoformat(),
        "updated_at": dvpr.updated_at.isoformat()
    }
    return info

def get_user_repos(gh, username):
    """ 
    获取指定用户的所有仓库信息
    """
    logger.info(f"Fetching repositories for {username}")
    repos = request_github(gh, lambda u: gh.get_user(u).get_repos(), (username,))
    # repos = gh.get_user(username).get_repos()
    repo_list = []
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
            "watchers_count": repo.watchers_count,
            "forks_count": repo.forks_count,
            "size": repo.size,
            "language": repo.language,
            "topics": repo.topics,
        }
        if repo.fork:
            repo_info['parent'] = repo.parent.full_name if repo.parent else None
        else:
            repo_info['parent'] = None
        repo_list.append(repo_info)
    return repo_list

if __name__ == "__main__":

    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )

    gh = Github(token_list[0])
    # username = 'Aurelius84'
    username = 'dune0310421'

    # 获取开发者基本信息
    info = get_user_info(gh, username)
    logger.info(f"User info for {username}: {info}")

    # 获取开发者repo信息
    repos = get_user_repos(gh, username)
    filename = f"data/developer/{username}/{username}_repos.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(repos, f, ensure_ascii=False, indent=4) 