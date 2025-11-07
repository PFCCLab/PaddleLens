import subprocess
import re
import json
import os

def find_renamed_from(path):
    """
    找到 path 对应的第一次 rename 操作中的来源 old_path。
    返回旧路径 old_path（若存在），否则返回 None。
    """
    cmd = ["git", "log", "--follow", "--name-status", "-M", "--", path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("Error running git log in rename check:", result.stderr.strip())
        return None

    lines = result.stdout.splitlines()
    for line in lines:
        if line.startswith("R") and '\t' in line:
            parts = line.strip().split('\t')
            if len(parts) == 3 and parts[2] == path:
                return parts[1]  # old_path
    return None

def extract_git_history(file_path):
    cmd = ["git", "log", "--reverse", "-p", "--date=iso", "--", file_path]
    # cmd = ["git", "log", "--reverse", "--follow", "-m", "-p", "--date=iso", "--", file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print("Error running git:", result.stderr)
        return

    lines = result.stdout.splitlines()
    history = []
    entry = {}
    diff_lines = []
    parsing_diff = False

    for line in lines:
        if line.startswith("commit "):
            if entry:
                entry["diff"] = "\n".join(diff_lines)
                history.append(entry)
                entry = {}
                diff_lines = []
                parsing_diff = False
            entry["commit"] = line.split()[1]
        elif line.startswith("Author: "):
            entry["author"] = line[len("Author: "):]
        elif line.startswith("Date: "):
            entry["date"] = line[len("Date: "):].strip()
        elif line.startswith("    ") and not parsing_diff:
            # commit message
            entry["message"] = line.strip()
        elif line.startswith("diff --git"):
            parsing_diff = True
        elif parsing_diff:
            diff_lines.append(line)

    # 最后一条提交
    if entry:
        entry["diff"] = "\n".join(diff_lines)
        history.append(entry)

    return history

def print_history(history):
    for entry in history:
        print("="*80)
        print(f"Commit : {entry['commit']}")
        print(f"Author : {entry['author']}")
        print(f"Date   : {entry['date']}")
        print(f"Message: {entry['message']}")
        print("Diff:")
        print(entry['diff'])
        print()

def extract_commits_with_keyword(input_file, output_file, keywords):
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 每个 commit 分割块（80个=）
    commits = content.split("=" * 80)

    matched = []
    for commit in commits:
        for kw in keywords:
            if kw in commit:
                matched.append(commit.strip())
                break

    with open(output_file, "w", encoding="utf-8") as f:
        for m in matched:
            f.write("=" * 80 + "\n")
            f.write(m + "\n\n")  # 添加两个换行保持结构

def extract_full_history_with_renames(start_path):
    """
    自动递归提取所有路径演化下的历史，包括 rename 之前的文件名。
    合并历史（按路径顺序）。
    """

    path = start_path
    visited = set()
    all_history = []

    while path and path not in visited:
        print(f"▶️ trace history: {path}")
        visited.add(path)

        history = extract_git_history(path)
        if history:
            all_history = history + all_history  # prepend: 新历史放前面

        old_path = find_renamed_from(path)
        if old_path:
            path = old_path
        else:
            break

    return all_history

if __name__ == "__main__":

    file_path = "doc/fluid/advanced_guide/addon_development/contribute_code/index_cn.rst"  # 替换为你想查看的文件路径
    # history = extract_git_history(file_path)
    history = extract_full_history_with_renames(file_path)
    # print_history(history)
    with open("../../../data/paddle/docs/tmp1_history.txt", "w", encoding="utf-8") as f:
        for entry in history:
            f.write("="*80 + "\n")
            f.write(f"Commit : {entry['commit']}\n")
            f.write(f"Author : {entry['author']}\n")
            f.write(f"Date   : {entry['date']}\n")
            f.write(f"Message: {entry['message']}\n")
            f.write("Diff:\n")
            f.write(entry['diff'] + "\n")
            f.write("\n")

    # 遍历目录下的所有文件
    # base_dir = "site/en/community/contribute"
    # output_dir = "../../data/tensorflow/docs"

    # os.makedirs(output_dir, exist_ok=True)

    # for root, dirs, files in os.walk(base_dir):
    #     for file in files:
    #         if not file.endswith(".md"):  # 只分析 markdown
    #             continue
    #         file_path = os.path.join(root, file)
    #         relative_path = os.path.relpath(file_path, start=base_dir)

    #         history = extract_git_history(relative_path)
    #         if history is None:  # 加入保护
    #             print(f"Skipping: {relative_path} (not under git or error)")
    #             continue

    #         out_file_name = relative_path.replace("/", "_").replace(".md", "")
    #         with open(os.path.join(output_dir, out_file_name + "_history.txt"), "w", encoding="utf-8") as f:
    #             for entry in history:
    #                 f.write("="*80 + "\n")
    #                 f.write(f"Commit : {entry['commit']}\n")
    #                 f.write(f"Author : {entry['author']}\n")
    #                 f.write(f"Date   : {entry['date']}\n")
    #                 f.write(f"Message: {entry['message']}\n")
    #                 f.write("Diff:\n")
    #                 f.write(entry['diff'] + "\n")
    #                 f.write("\n")

    # extract_commits_with_keyword(
    #     input_file="../../../data/paddle/docs/doc_history.txt",
    #     output_file="../../../data/paddle/docs/doc_filtered_history.txt",
    #     keywords=["contribute_to_paddle", "contribute_to_paddle_cn"]
    # )