import json

def normalize_email(email):
    return email.strip().lower()

def normalize_name(name):
    return name.strip().lower()

def has_two_segments(name):
    return len(name.strip().split()) >= 2

def get_community_developers(commits):
    # 初始化数据结构
    email_to_group = {}
    groups = []  # 每个元素 {'names': set(), 'emails': set(), 'count': int}

    for commit in commits:
        name = commit.get("author")
        email = commit.get("author_email")
        if not name or not email:
            continue
        norm_email = normalize_email(email)
        norm_name = normalize_name(name)

        if norm_email in email_to_group:
            idx = email_to_group[norm_email]
            groups[idx]["names"].add(norm_name)
            groups[idx]["emails"].add(norm_email)
            groups[idx]["count"] += 1
        else:
            idx = len(groups)
            groups.append({
                "names": {norm_name},
                "emails": {norm_email},
                "count": 1,
            })
            email_to_group[norm_email] = idx

    # 合并具有相同名称的开发者
    merged = [False] * len(groups)
    name_to_indices = {}
    for i, group in enumerate(groups):
        for name in group["names"]:
            if has_two_segments(name):
                name_to_indices.setdefault(name, set()).add(i)

    for i, group in enumerate(groups):
        if merged[i]:
            continue
        to_merge = set()
        for name in group["names"]:
            if has_two_segments(name):
                to_merge.update(name_to_indices.get(name, set()))
        to_merge.discard(i)
        for j in to_merge:
            if merged[j]:
                continue
            group["names"].update(groups[j]["names"])
            group["emails"].update(groups[j]["emails"])
            group["count"] += groups[j]["count"]
            merged[j] = True

    groups = [g for i, g in enumerate(groups) if not merged[i]]

    # 迭代合并通过email重叠的组
    changed = True
    while changed:
        changed = False
        email_to_index = {}
        new_groups = []
        for group in groups:
            target_idx = None
            for email in group["emails"]:
                if email in email_to_index:
                    target_idx = email_to_index[email]
                    break
            if target_idx is None:
                target_idx = len(new_groups)
                new_groups.append({
                    "names": set(),
                    "emails": set(),
                    "count": 0,
                })
            new_groups[target_idx]["names"].update(group["names"])
            new_groups[target_idx]["emails"].update(group["emails"])
            new_groups[target_idx]["count"] += group["count"]
            for email in group["emails"]:
                email_to_index[email] = target_idx
        if len(new_groups) < len(groups):
            changed = True
        groups = new_groups

    # 筛选非百度开发者
    community_dvprs = []
    for group in groups:
        is_baidu = any("baidu.com" in email or "paddle" in email for email in group["emails"])
        if not is_baidu:
            for name in group["names"]:
                community_dvprs.append(name)
    return community_dvprs


if __name__ == "__main__":
    developers = {}
    repo = "PaddlePaddle/Paddle"
    owner, name = repo.split("/")

    with open(f"../data/paddle_commits/{owner}_{name}_commits.json", "r", encoding="utf-8") as f:
        commits = json.load(f)

    community_dvprs = get_community_developers(commits)