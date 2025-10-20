import datetime
import json

from utils.manage_data_update_time import get_now_date
from health.fetcher.fetch_releases import fetch_total_releases
from health.fetcher.fetch_dependents import fetch_dependents_from_html


DATA_DIR = "data"

class HealthAnalyzer:
    """
    分析飞桨项目的健康度
    """
    def __init__(self, repo: str, days: int = 90):
        """
        初始化
        """
        owner, name = repo.split("/")
        # 检查repo是否在飞桨里
        with open(f"{DATA_DIR}/paddle_repos.json", 'r', encoding='utf-8') as f:
            paddle_repos = json.load(f)
        repo_list = [r["full_name"] for r in paddle_repos]
        if repo not in repo_list:
            raise ValueError("目前仅支持分析PaddlePaddle和PFCCLab组织下的仓库，请检查仓库名是否正确")
        nowdate = get_now_date()
        nowdate = datetime.datetime.fromisoformat(nowdate).replace(tzinfo=datetime.timezone.utc)

        self.owner = owner
        self.repo_name = name
        self.dir = f"{owner}_{name}"
        self.days = days
        self.recent = nowdate - datetime.timedelta(days=days)
        self.scores = {
            "vigor": {
                "communication activity": {
                    "number of comments": {
                        "total": 0,
                        "recent": 0,
                    },
                    "number of issues": {
                        "total": 0,
                        "recent": 0,
                    },
                },
                "development activity": {
                    "core developer activity": {
                        "number of core developer reviews": {
                            "total": 0,
                            "recent": 0,
                        },
                    },
                    "overall development activity": {
                        "number of pull requests": {
                            "total": 0,
                            "recent": 0,
                        },
                        "number of commits": {
                            "total": 0,
                            "recent": 0,
                        },
                        "requirement completion ratio": {
                            "number of requirement issues closed": {
                                "total": 0,
                                "recent": 0,
                            },
                            "number of requirement issues": {
                                "total": 0,
                                "recent": 0,
                            },
                            "ratio": {
                                "total": 0,
                                "recent": 0,
                            },
                        },
                    },
                },
                "release activity": {
                    "number of releases": {
                        "total": 0,
                        "recent": 0,
                    },
                },
            },
            "organization": {
                "size": {
                    "number of contributors": {
                        "total": 0,
                        "recent": 0,
                    },
                    "number of core contributors": 0,
                },
                "diversity": {
                    "company": "Check from OSS Insight",
                    "experience": {
                        "acceptence rate of pull requests": {
                            "number of merged pull requests": {
                                "total": 0,
                                "recent": 0,
                            },
                            "number of pull requests": {
                                "total": 0,
                                "recent": 0,
                            },
                            "ratio": {
                                "total": 0,
                                "recent": 0,
                            },
                        },
                        "close rate of issues": {
                            "number of issues closed": {
                                "total": 0,
                                "recent": 0,
                            },
                            "number of issues": {
                                "total": 0,
                                "recent": 0,
                            },
                            "ratio": {
                                "total": 0,
                                "recent": 0,
                            },
                        },
                    },
                },
                "rules": {
                    "guidance": [
                        "process maturity",
                        "new-comer guidance",
                    ],
                    "incentive system": [
                        "level of gamification",
                        "recognition mechanism",
                        "financial support",
                        "dynamic developer roles",
                    ],
                },
            },
            "resilience": {
                "attraction": {
                    "new contributor rate": {
                        "number of new contributors": 0,
                        "number of contributors": 0,
                        "ratio": 0,
                    }
                },
                "retention": {
                    "contributor retention rate": {
                        "number of retention contributors": 0,
                        "number of contributors before": 0,
                        "ratio": 0,
                    }
                },
            },
            "services": {
                "value": {
                    "popularity": {
                        "stars": 0,
                        "forks": 0,
                        "watches": 0,
                        "dependents": {
                            "repositories": 0,
                            "packages": 0,
                        },
                    }
                }
            },
        }

    
    def analyze_health(self):
        """
        分析健康度，返回健康度结果。
        """

        # 读取本地数据
        with open(f"{DATA_DIR}/paddle_issues/{self.dir}_issues.json", 'r', encoding='utf-8') as f:
            issues = json.load(f)
        with open(f"{DATA_DIR}/paddle_prs/{self.dir}_prs.json", 'r', encoding='utf-8') as f:
            prs = json.load(f)
        with open(f"{DATA_DIR}/paddle_commits/{self.dir}_commits.json", 'r', encoding='utf-8') as f:
            commits = json.load(f)

        #  ---vigor---
        #  1)communication activity
        #    a)number of comments
        total_issue_comments = sum(len(issue.get("comment_by", [])) for issue in issues)
        total_pr_comments = sum(len(pr.get("comment_by", [])) for pr in prs)
        self.scores["vigor"]["communication activity"]["number of comments"]["total"] = total_issue_comments + total_pr_comments
        recent_issue_comments = 0
        for issue in issues:
            recent_issue_comments += sum(1 for comment in issue.get("comment_by", [])
                if datetime.datetime.fromisoformat(comment[1][:10]).date() >= self.recent.date()
            )
        recent_pr_comments = 0
        for pr in prs:
            recent_pr_comments += sum(1 for comment in pr.get("comment_by", [])
                if datetime.datetime.fromisoformat(comment[1][:10]).date() >= self.recent.date()
            )
        self.scores["vigor"]["communication activity"]["number of comments"]["recent"] = recent_issue_comments + recent_pr_comments
        #    b)number of issues
        total_issues = len(issues)
        self.scores["vigor"]["communication activity"]["number of issues"]["total"] = total_issues
        recent_issues = sum(1 for issue in issues if datetime.datetime.fromisoformat(issue.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        self.scores["vigor"]["communication activity"]["number of issues"]["recent"] = recent_issues

        #  2)development activity
        #    a)core developer activity-number of core developer reviews
        total_reviews = sum(len(pr.get("review_by", [])) for pr in prs)
        self.scores["vigor"]["development activity"]["core developer activity"]["number of core developer reviews"]["total"] = total_reviews
        recent_reviews = 0
        for pr in prs:
            recent_reviews += sum(1 for review in pr.get("review_by", [])
                if datetime.datetime.fromisoformat(review[1][:10]).date() >= self.recent.date()
            )
        self.scores["vigor"]["development activity"]["core developer activity"]["number of core developer reviews"]["recent"] = recent_reviews
        #    b)overall development activity
        #       i)number of pull requests
        total_prs = len(prs)
        self.scores["vigor"]["development activity"]["overall development activity"]["number of pull requests"]["total"] = total_prs
        recent_prs = sum(1 for pr in prs if datetime.datetime.fromisoformat(pr.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        self.scores["vigor"]["development activity"]["overall development activity"]["number of pull requests"]["recent"] = recent_prs
        #       ii)number of commits
        total_commits = len(commits)
        self.scores["vigor"]["development activity"]["overall development activity"]["number of commits"]["total"] = total_commits
        recent_commits = sum(1 for commit in commits if datetime.datetime.fromisoformat(commit.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        self.scores["vigor"]["development activity"]["overall development activity"]["number of commits"]["recent"] = recent_commits
        #       iii)requirement completion ratio
        requirement_issues = [
            issue for issue in issues
            if any("feat" in label for label in issue.get("labels", []))
        ]
        total_requirement_issues = len(requirement_issues)
        total_closed_requirement_issues = sum(1 for issue in requirement_issues if issue.get("state", "") == "closed")
        self.scores["vigor"]["development activity"]["overall development activity"]["requirement completion ratio"]["number of requirement issues"]["total"] = total_requirement_issues
        self.scores["vigor"]["development activity"]["overall development activity"]["requirement completion ratio"]["number of requirement issues closed"]["total"] = total_closed_requirement_issues
        self.scores["vigor"]["development activity"]["overall development activity"]["requirement completion ratio"]["ratio"]["total"] = total_closed_requirement_issues / total_requirement_issues if total_requirement_issues > 0 else 0
        recent_requirement_issues = sum(1 for issue in requirement_issues if datetime.datetime.fromisoformat(issue.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        recent_closed_requirement_issues = sum(1 for issue in requirement_issues if issue.get("state", "") == "closed" and datetime.datetime.fromisoformat(issue.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        self.scores["vigor"]["development activity"]["overall development activity"]["requirement completion ratio"]["number of requirement issues"]["recent"] = recent_requirement_issues
        self.scores["vigor"]["development activity"]["overall development activity"]["requirement completion ratio"]["number of requirement issues closed"]["recent"] = recent_closed_requirement_issues
        self.scores["vigor"]["development activity"]["overall development activity"]["requirement completion ratio"]["ratio"]["recent"] = recent_closed_requirement_issues / recent_requirement_issues if recent_requirement_issues > 0 else 0

        #  3)release activity
        total_release_count, recent_release_count = fetch_total_releases(self.owner, self.repo_name, self.days)
        self.scores["vigor"]["release activity"]["number of releases"]["total"] = total_release_count
        self.scores["vigor"]["release activity"]["number of releases"]["recent"] = recent_release_count

        #  ---organization---
        #  1)size
        #    a)number of contributors
        all_contributors = set(commit["author"] for commit in commits)
        self.scores["organization"]["size"]["number of contributors"]["total"] = len(all_contributors)
        recent_contributors = set(commit["author"] for commit in commits
            if datetime.datetime.fromisoformat(commit.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date()
        )
        self.scores["organization"]["size"]["number of contributors"]["recent"] = len(recent_contributors)
        #    b)number of core contributors
        core_contributors = set(commit["committer"] for commit in commits)
        core_contributors.discard("GitHub")
        self.scores["organization"]["size"]["number of core contributors"] = len(core_contributors)

        #  2)diversity
        #    a)acceptence rate of pull requests
        total_merged_prs = sum(1 for pr in prs if pr.get("merged", False) == True)
        self.scores["organization"]["diversity"]["experience"]["acceptence rate of pull requests"]["number of merged pull requests"]["total"] = total_merged_prs
        self.scores["organization"]["diversity"]["experience"]["acceptence rate of pull requests"]["number of pull requests"]["total"] = total_prs
        self.scores["organization"]["diversity"]["experience"]["acceptence rate of pull requests"]["ratio"]["total"] = total_merged_prs / total_prs if total_prs > 0 else 0
        recent_merged_prs = sum(1 for pr in prs if pr.get("merged", False) == True and datetime.datetime.fromisoformat(pr.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        self.scores["organization"]["diversity"]["experience"]["acceptence rate of pull requests"]["number of merged pull requests"]["recent"] = recent_merged_prs
        self.scores["organization"]["diversity"]["experience"]["acceptence rate of pull requests"]["number of pull requests"]["recent"] = recent_prs
        self.scores["organization"]["diversity"]["experience"]["acceptence rate of pull requests"]["ratio"]["recent"] = recent_merged_prs / recent_prs if recent_prs > 0 else 0
        #    b)close rate of issues
        total_closed_issues = sum(1 for issue in issues if issue.get("state", "") == "closed")
        self.scores["organization"]["diversity"]["experience"]["close rate of issues"]["number of issues closed"]["total"] = total_closed_issues
        self.scores["organization"]["diversity"]["experience"]["close rate of issues"]["number of issues"]["total"] = total_issues
        self.scores["organization"]["diversity"]["experience"]["close rate of issues"]["ratio"]["total"] = total_closed_issues / total_issues if total_issues > 0 else 0
        recent_closed_issues = sum(1 for issue in issues if issue.get("state", "") == "closed" and datetime.datetime.fromisoformat(issue.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() >= self.recent.date())
        self.scores["organization"]["diversity"]["experience"]["close rate of issues"]["number of issues closed"]["recent"] = recent_closed_issues
        self.scores["organization"]["diversity"]["experience"]["close rate of issues"]["number of issues"]["recent"] = recent_issues
        self.scores["organization"]["diversity"]["experience"]["close rate of issues"]["ratio"]["recent"] = recent_closed_issues / recent_issues if recent_issues > 0 else 0

        #  ---resilience---
        #  1)attraction
        previous_contributors = set(commit["author"] for commit in commits
            if datetime.datetime.fromisoformat(commit.get("created_at", "1970-01-01T00:00:00+00:00")[:10]).date() < self.recent.date()
        )
        new_contributors = recent_contributors - previous_contributors
        self.scores["resilience"]["attraction"]["new contributor rate"]["number of new contributors"] = len(new_contributors)
        self.scores["resilience"]["attraction"]["new contributor rate"]["number of contributors"] = len(recent_contributors)
        self.scores["resilience"]["attraction"]["new contributor rate"]["ratio"] = len(new_contributors) / len(recent_contributors) if len(recent_contributors) > 0 else 0
        #  2)retention
        retention_contributors = recent_contributors & previous_contributors
        self.scores["resilience"]["retention"]["contributor retention rate"]["number of retention contributors"] = len(retention_contributors)
        self.scores["resilience"]["retention"]["contributor retention rate"]["number of contributors before"] = len(previous_contributors)
        self.scores["resilience"]["retention"]["contributor retention rate"]["ratio"] = len(retention_contributors) / len(previous_contributors) if len(previous_contributors) > 0 else 0

        #  ---services---
        #  value-popularity
        with open(f"{DATA_DIR}/paddle_repos.json", 'r', encoding='utf-8') as f:
            paddle_repos = json.load(f)
        repo_info = next((r for r in paddle_repos if r["full_name"] == f"{self.owner}/{self.repo_name}"), None)
        if repo_info:
            self.scores["services"]["value"]["popularity"]["stars"] = repo_info.get("stargazers_count", 0)
            self.scores["services"]["value"]["popularity"]["forks"] = repo_info.get("forks_count", 0)
            self.scores["services"]["value"]["popularity"]["watches"] = repo_info.get("watchers_count", 0)

        total_dependents_count = fetch_dependents_from_html(self.owner, self.repo_name)
        self.scores["services"]["value"]["popularity"]["dependents"] = total_dependents_count

        return {
            "date": get_now_date(),
            "scores": self.scores
        }

if __name__ == "__main__":

    repo = "PaddlePaddle/Paddle"
    analyzer = HealthAnalyzer(repo)
    results = analyzer.analyze_health()
    print(results)