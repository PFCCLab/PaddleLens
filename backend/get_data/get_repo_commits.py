import time
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from time import sleep
from datetime import datetime, timezone
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import logging
from typing import *
from github import Github, GithubException

from utils.request_github import request_github
from config import GITHUB_TOKEN

GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"

logger = logging.getLogger(__name__)
token_list = [
    GITHUB_TOKEN,
]

def load_commit_objects(file_path):
    """
    将git log获取的commit基本信息转换为json
    """
    commits = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                # 将每一行的JSON对象加载为Python字典
                line = line.strip().rstrip(',')
                commit = json.loads(line)
                commits.append(commit)
    return commits

def extract_modified_filename(change_str):
    """
    修改文件名的文件保留新的文件名
    如'demo/components/{pir_translate.py => pir_program_test.py}'
    """
    start = change_str.find('=>') + 3  # Skip '=> ' to get to the new filename
    end = change_str.find('}', start)

    new_filename = change_str[start:end].strip()

    base_path = change_str[:change_str.find('{')].strip()
    return f"{base_path}{new_filename}"

def parse_commit_logs1(file_path):
    """
    解析git log --name-status获取的commit信息
    """
    commit_data = {}
    current_sha = None
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("STARTOFTHECOMMIT"):
                current_sha = line.split(": ")[1]
                commit_data[current_sha] = {'files': []}
            else:
                if line:
                    parts = line.split()
                    if len(parts) == 2:
                        status, filename = parts[0], parts[1]
                        if status == 'A':
                            status = 'added'
                        elif status == 'M':
                            status = 'modified'
                        else:
                            status = 'removed'
                        commit_data[current_sha]['files'].append({
                            'filename': filename,
                            'status': status,
                        })
                    elif len(parts) == 3:
                        status, filename = parts[0], parts[2]
                        commit_data[current_sha]['files'].append({
                            'filename': filename,
                            'status': 'modified',
                        })
    return commit_data

def parse_commit_logs2(file_path):
    """
    解析git log --numstat获取的commit信息
    """
    commit_data = {}
    current_sha = None
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("STARTOFTHECOMMIT"):
                current_sha = line.split(": ")[1]
                commit_data[current_sha] = {'files': []}
            else:
                if line:
                    parts = line.split()
                    # print(line)
                    additions = int(parts[0]) if parts[0].isdigit() else 0
                    deletions = int(parts[1]) if parts[1].isdigit() else 0
                    # filename = extract_modified_filename(parts[2]) if "=>" in parts[2] else parts[2]
                    commit_data[current_sha]['files'].append({
                        # 'filename': filename,
                        'additions': additions,
                        'deletions': deletions,
                        'changes': additions + deletions
                        })
    return commit_data

def get_login_for_commit(gh, repo_full_name, sha):
    """
    获取指定commit的作者和提交者的login
    """
    try:
        repo = gh.get_repo(repo_full_name)
        commit = repo.get_commit(sha)
        return {
            "sha": sha,
            "author": commit.author.login if commit.author else None,
            "committer": commit.committer.login if commit.committer else None
        }
    except Exception as e:
        return {"sha": sha, "error": str(e)}

def update_logins(repo_full_name, commit_list):
    """
    用pygithub获取commit的author和committer的login，替换当前可能不准确的author和committer
    """
    gh_list = [Github(token) for token in token_list]
    updated_list = []
    sha_to_commit = {commit["sha"]: commit for commit in commit_list}

    tasks = []
    with ThreadPoolExecutor(max_workers=3 * len(gh_list)) as executor:
        for i, sha in enumerate(sha_to_commit):
            tasks.append(executor.submit(get_login_for_commit, gh_list[i % len(gh_list)], repo_full_name, sha))

        for future in tqdm(as_completed(tasks), total=len(tasks), desc=f"Fetching logins for {repo_full_name}"):
            result = future.result()
            sha = result["sha"]
            commit = sha_to_commit[sha]
            if "error" in result:
                logger.warning(f"Login fetch failed for {sha}: {result['error']}")
            else:
                commit["author"] = result["author"]
                commit["committer"] = result["committer"]
            updated_list.append(commit)

    return updated_list

def get_repo_commits(repo_full_name):
    """ 
    使用Shell脚本获取指定仓库的所有commit
    该方法使用git log命令获取commit信息，并将其转换为JSON格式。
    适用于需要处理大量仓库的情况，速度较快。
    """
    logger.info(f"Processing repository: {repo_full_name}")

    # 定义Shell脚本的内容，使用传入的仓库名称
    shell_script = f"""
    FULL_NAME="{repo_full_name}"
    REPO_URL="https://github.com/$FULL_NAME.git"
    FILE_NAME=$(echo $FULL_NAME | tr '/' '_')
    
    # 指定目录，clone repo
    DEST_DIR="./tmp_repo"
    mkdir -p $DEST_DIR
    CLONE_PATH="$DEST_DIR/$FILE_NAME"
    git clone $REPO_URL $CLONE_PATH

    # 获取commit日志
    cd $CLONE_PATH
    git log --pretty=format:'{{"repo": "{repo_full_name}", "sha": "%H", "created_at": "%ad", "author": "%an", "committer": "%cn", "message": "%f"}},' --date=iso | sed "$ s/,$//" > ../${{FILE_NAME}}_commits.json
    git log --name-status --pretty=format:'STARTOFTHECOMMIT: %H'> ../${{FILE_NAME}}_commits1.log
    git log --numstat --pretty=format:'STARTOFTHECOMMIT: %H'> ../${{FILE_NAME}}_commits2.log

    # 返回当前目录
    cd ../.. 
    """

    # 执行Shell命令
    try:
        subprocess.run(shell_script, shell=True, check=True, capture_output=True, text=True)
        # print("Execution completed.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}")

    commits_file = f"tmp_repo/{repo_full_name.replace('/', '_')}_commits.json"
    commits1_file = f"tmp_repo/{repo_full_name.replace('/', '_')}_commits1.log"
    commits2_file = f"tmp_repo/{repo_full_name.replace('/', '_')}_commits2.log"
    commits = load_commit_objects(commits_file)
    commit_details_1 = parse_commit_logs1(commits1_file)
    commit_details_2 = parse_commit_logs2(commits2_file)

    # 合并信息
    commit_list = []
    for commit in commits:
        sha = commit['sha']
        files_1 = commit_details_1.get(sha, {}).get('files', [])
        files_2 = commit_details_2.get(sha, {}).get('files', [])

        for i in range(len(files_1)):
            file_1 = files_1[i]
            file_2 = files_2[i] if i < len(files_2) else {}
            file_1.update(file_2)

        commit['files'] = files_1
        commit_list.append(commit)
    
    # 用pygithub获取commit的author和committer的login，替换当前可能不准确的author和committer
    # commit_list = update_logins(repo_full_name, commit_list)

    # 删除tmp_repo目录
    subprocess.run(f"rm -rf tmp_repo", shell=True, check=True)
    # print(f"Merged data for {repo_owner_repo} into {output_filename}")
    return commit_list

def get_repo_commits_gh(gh, repo_full_name):
    """
    使用github api获取指定仓库的所有commit，相对较慢
    """
    commits = request_github(
        gh, lambda r: gh.get_repo(r).get_commits(),
        (repo_full_name, )
    )
    logger.info(f"Fetching commits for repository: {repo_full_name}, total: {commits.totalCount}")

    commit_list = []
    for commit in tqdm(commits):
        try:
            commit_info = {
                'repo': repo_full_name,
                'sha': commit.sha,
                'message': commit.commit.message,
                'created_at': commit.commit.author.date.isoformat(),
                'author': commit.author.login if commit.author else None,
                'committer': commit.committer.login if commit.committer else None,
            }
            commit_files = commit.files
            if commit_files:
                commit_info['files'] = []
                for file in commit_files:
                    file_info = {
                        'filename': file.filename,
                        'status': file.status,
                        'additions': file.additions,
                        'deletions': file.deletions,
                        'changes': file.changes,
                        # 'patch': file.patch if hasattr(file, 'patch') else None
                    }
                    commit_info['files'].append(file_info)
            else:
                commit_info['files'] = []
            commit_list.append(commit_info)
        except Exception as e:
            logger.error(f"Error processing commit {commit.sha} in repository {repo_full_name}: {e}")
            commit_list.append({
                'repo': repo_full_name,
                'sha': commit.sha,
                'error': str(e)
            })
            continue
    return commit_list

def get_commit_files(token: str, repo_full_name: str, commit_sha: str) -> list[dict]:
    """
    获取指定 commit 的文件变更信息
    """
    gh = Github(token)
    commit_obj = request_github(
        gh, lambda r, sha: gh.get_repo(r).get_commit(sha),
        (repo_full_name, commit_sha),
    )

    if not commit_obj:
        return []

    file_list = []
    for f in commit_obj.files:
        file_list.append({
            "filename": f.filename,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "changes": f.changes,
        })

    return file_list

def update_repo_commits(token: str, repo_full_name: str, since: str, until: str) -> list[dict]:
    """
    用rest api获取指定仓库的commit信息
    """
    gh = Github(token)
    owner, name = repo_full_name.split("/")

    since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    until_dt = datetime.fromisoformat(until).replace(tzinfo=timezone.utc)

    logger.info(f"Fetching commits for repository: {repo_full_name} from {since_dt} to {until_dt}")
    repo = request_github(
        gh, lambda r: gh.get_repo(r),
        (repo_full_name, )
    )
    if not repo:
        return []

    commits = request_github(
        gh, lambda since, until: repo.get_commits(since=since, until=until),
        (since_dt, until_dt)
    )

    if not commits:
        return []
    try:
        commits = list(commits)
    except GithubException as e:
        logger.warning(f"GitHub error when listing commits for {repo_full_name}: "
                       f"{getattr(e, 'data', {}).get('message', str(e))}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error converting commits to list for {repo_full_name}: {e}")
        return []


    results = []
    
    # 使用多线程获取每个commit的详细信息
    def fetch_commit_details(commit):
        try:
            commit_info = {
                'repo': repo_full_name,
                'sha': commit.sha,
                'message': commit.commit.message,
                'created_at': commit.commit.author.date.isoformat(),
                'author': commit.author.login if commit.author else None,
                'committer': commit.committer.login if commit.committer else None,
            }
            try:
                commit_files = commit.files
                commit_info['files'] = [{
                    'filename': f.filename,
                    'status': f.status,
                    'additions': f.additions,
                    'deletions': f.deletions,
                    'changes': f.changes
                } for f in commit_files] if commit_files else []
            except Exception:
                commit_info['files'] = []
            return commit_info
        except Exception as e:
            logger.error(f"Error processing commit {commit.sha} in repository {repo_full_name}: {e}")
            return {
                'repo': repo_full_name,
                'sha': commit.sha,
                'error': str(e)
            }
    with ThreadPoolExecutor(max_workers=9) as executor:
        future_to_commit = {executor.submit(fetch_commit_details, commit): commit for commit in commits}
        for future in tqdm(as_completed(future_to_commit), total=len(future_to_commit), desc=f"Fetching commit details from {repo_full_name}", dynamic_ncols=True):
            commit_info = future.result()
            results.append(commit_info)

    return results

if __name__ == "__main__":

    # repos = None
    # with open("data/paddle_repos.json", "r", encoding="utf-8") as f:
    #     repos = json.load(f)

    # for repo in tqdm(repos):
    #     commits = get_repo_commits(repo['full_name'])
    #     repo_owner, repo_name = repo['full_name'].split('/')
    #     output_filename = f"data/paddle_commits/{repo_owner}_{repo_name}_commits.json"
    #     # with open(output_filename, 'w', encoding='utf-8') as f:
    #     #     json.dump(commits, f, indent=4)

    # 方法2：用github api获取
    # token = '' # 添加你的GitHub token
    # gh = Github(token)
    # for repo in repos:
    #     commits = get_repo_commits_gh(gh, repo['full_name'])
    #     repo_owner, repo_name = repo['full_name'].split('/')
    #     output_filename = f"data/paddle_commits/{repo_owner}_{repo_name}_commits.json"
    #     with open(output_filename, 'w', encoding='utf-8') as f:
    #         json.dump(commits, f, indent=4)

    # 更新指定repo的commit
    res = update_repo_commits(token_list[0], "PaddlePaddle/FastDeploy", "2025-10-01", "2025-10-15")
    with open("cache/test_commits.json", "w", newline="", encoding="utf-8") as f:
        json.dump(res, f, indent=4, ensure_ascii=False)