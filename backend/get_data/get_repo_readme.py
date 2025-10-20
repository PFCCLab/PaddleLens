import time
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import requests
from github import Github

from utils.request_github import request_github
from config import GITHUB_TOKEN

logger = logging.getLogger(__name__)
token_list = [
    GITHUB_TOKEN,
]

def fetch_readme(gh: Github, repo_full_name: str) -> str:
    """
    从GitHub爬取指定仓库的README内容
    """
    try:
        repo = request_github(gh, gh.get_repo, (repo_full_name,))
        readme = request_github(gh, repo.get_readme)
        readme_content = readme.decoded_content.decode("utf-8")
        return readme_content
    except Exception as e:
        logger.error(f"Error fetching README for {repo_full_name}: {e}")
        return ""

def get_repo_readme(repo_full_name: str) -> str:
    """
    获取单个仓库的README文件内容
    """
    gh = Github(token_list[0])  # 使用第一个token
    result = fetch_readme(gh, repo_full_name)
    return result

def get_readmes(repo_list: list[str]) -> dict[str, str]:
    """
    获取多个仓库的README内容，使用多线程
    repo_list: list of repo_full_name
    """
    gh_list = [Github(token) for token in token_list]
    results = {}

    with ThreadPoolExecutor(max_workers=3 * len(gh_list)) as executor:
        future_to_repo = {
            executor.submit(fetch_readme, gh_list[i % len(gh_list)], repo_full_name): repo_full_name for i, repo_full_name in enumerate(repo_list)
        }

        for future in tqdm(as_completed(future_to_repo), total=len(future_to_repo), desc="Fetching README content"):
            try:
                readme_content = future.result()
                results[future_to_repo[future]] = readme_content
            except Exception as e:
                logger.error(f"Unhandled error for {future_to_repo[future]}: {e}")
                results[future_to_repo[future]] = ""

    return results

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )

    # # 获取单个仓库的README
    # readme = get_repo_readme("PaddlePaddle/Paddle")
    # print(f"README content for PaddlePaddle/Paddle:\n{readme[:500]}...")  # 打印前500个字符
    
    # 获取一系列仓库的readme
    with open("cache/paddle_repos.json", "r", encoding="utf-8") as f:
        repos = json.load(f)
    repo_list = [repo['full_name'] for repo in repos]
    readmes = get_readmes(repo_list)
    with open("cache/paddle_repos_readme.json", "w", encoding="utf-8") as f:
        json.dump(readmes, f, indent=4, ensure_ascii=False)