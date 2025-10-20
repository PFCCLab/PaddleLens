import json
import os
import datetime

class GovernanceAnalyzer:
    """
    分析飞桨的治理规则得分
    """
    def __init__(self, repo: str = "PaddlePaddle/Paddle"):
        self.repo = repo
        self.date = datetime.datetime(1970, 1, 1).strftime("%Y-%m-%d") # 初始化为1970-01-01
        self.scores = {
            "usage": {
                "installation_guide": 0,
                "usage_guide": 0,
                "security_policy": 0,
                "license": 0
            },
            "contribution": {
                "contribution_guidelines": {
                    "contribution_types": 0,
                    "cla": 0,
                    "communication_way": 0,
                    "mentorship": 0,
                    "local_environment_setup": 0,
                },
                "contribution_submission": {
                    "writing_standards": 0,
                    "submission_standards": 0,
                    "code_of_conduct": 0,
                },
                "contribution_acceptance": {
                    "review_standards": 0,
                    "review_process": 0,
                    "ci_description": 0
                }
            },
            "organization": {
                "role_management": {
                    "role_definition": 0,
                    "role_assignment_standards": 0,
                    "role_assignment_process": 0
                },
                "release_management": 0
            }
        }
    
    def analyze_governance(self):
        files = [
            os.path.join("data/governance_scores", f)
            for f in os.listdir("data/governance_scores")
            if f.endswith(".json")
        ]
        if not files:
            raise FileNotFoundError("找不到评分文件。")
        latest_file = max(files, key=os.path.getctime)

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tmp = latest_file.split("/")[-1].replace(".json", "")
        self.date = tmp[:4] + "-" + tmp[4:6] + "-" + tmp[6:8]
        self.scores = data

        results = {
            "date": self.date,
            "scores": self.scores,
        }
            
        return results