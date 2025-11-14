import numpy as np
import uuid
import datetime
from datetime import date
import pandas as pd
import base64
from typing import Optional
import plotly.graph_objects as go
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from skills.developer_analyzer import DeveloperAnalyzer
from health.health_analyzer import HealthAnalyzer
from collaboration.governance_analyzer import GovernanceAnalyzer

def clean_data(obj):
    """
    递归清理数据，确保所有数据类型都可以被JSON序列化
    """
    if isinstance(obj, go.Figure):
        return clean_data(obj.to_dict()) # plotly图片先转dict，再处理dict中的每一项
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode()
    elif isinstance(obj, (np.integer, np.int32, np.int64, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.ndarray,)):
        return [clean_data(o) for o in obj.tolist()]
    elif isinstance(obj, (pd.Timestamp, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, (pd.Timedelta, datetime.timedelta)):
        return str(obj)
    elif isinstance(obj, (dict,)):
        return {clean_data(k): clean_data(v) for k, v in obj.items()}  # 处理dict中的每一项
    elif isinstance(obj, (list, tuple, set)):  # 处理list/tuple/set中的每一项
        return [clean_data(v) for v in obj]
    else:
        return obj

app = FastAPI()

# 设置跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://localhost:5173",
        "http://paddle-lens.osslab-pku.org",
        "https://paddle-lens.osslab-pku.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {"message": "Welcome to PaddleLens!"}

@app.get("/favicon.ico")
def ignore_favicon():
    return ""

# 程序员能力度量
class UserAnalyzeRequest(BaseModel):
    github_user: str

@app.post("/dvpr_skills/")
def analyze_skills(request_data: UserAnalyzeRequest) -> dict:
    """
    分析开发者技能，返回技能分析结果。
    """
    username = request_data.github_user
    try:
        with DeveloperAnalyzer(username) as analyzer:
            result = analyzer.analyze_skills()
            result = clean_data(result)
            return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误：{str(e)}")

# 项目群体协同-治理度分析

class GovernanceAnalyzeRequest(BaseModel):
    input_date: Optional[date] = None

@app.post("/governance/")
def governance_analysis(request_data: GovernanceAnalyzeRequest) -> dict:
    """
    展示项目治理度，返回治理度分析结果。
    """
    input_date = request_data.input_date
    try:
        analyzer = GovernanceAnalyzer(input_date=input_date)
        result = analyzer.analyze_governance()
        result = clean_data(result)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误：{str(e)}")

# 健康度分析
class RepoAnalyzeRequest(BaseModel):
    github_repo: str

@app.post("/health/")
def health_analysis(request_data: RepoAnalyzeRequest) -> dict:
    """
    分析项目健康度，返回健康度分析结果。
    """
    reponame = request_data.github_repo
    try:
        analyzer = HealthAnalyzer(reponame)
        result = analyzer.analyze_health()
        result = clean_data(result)
        return JSONResponse(content=result)
    except ValueError as e:
        # 捕获 ValueError 并返回 400 Bad Request
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 捕获所有其他异常，并返回 500 Internal Server Error
        raise HTTPException(status_code=500, detail=f"服务器内部错误：{str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)