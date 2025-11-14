from os import read
import re
import json
from tqdm import tqdm
from openai import OpenAI
import logging
from config import OPENAI_BASE_URL, OPENAI_API_KEY, MODEL

logger = logging.getLogger(__name__)

# 创建客户端
client = OpenAI(
    base_url=OPENAI_BASE_URL, 
    api_key=OPENAI_API_KEY
    )

def clean_markdown(text: str) -> str:
    """
    清洗markdown形式的文本内容，去除不必要的格式和特殊字符
    """
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)  # 双层嵌套徽章
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)             # 单层徽章图标
    text = re.sub(r'!\w+', '', text)                        # 去除 !Contributors 这种独立符号
    text = re.sub(r'<img[^>]*>', '', text, flags=re.DOTALL) # 去除图片标签
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL) # 去除代码块（```之间的内容）
    text = re.sub(r'`[^`]*`', '', text) # 去除行内代码（`之间的内容）
    text = re.sub(r'\[([^\[\]]+)\]\([^\(\)]+\)', r'\1', text) # 去除Markdown链接格式[text](url)
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text) # 去除加粗文本（**或__之间的内容）
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text) # 去除斜体文本（*或_之间的内容）
    text = re.sub(r'<.*?>', '', text) # 去除 HTML 标签
    text = re.sub(r'http\S+|www\.\S+', '', text) # 去除链接（http或www开头的内容）
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9 \n]', '', text) # 清掉特殊字符（保留 \n 结构）
    text = re.sub(r'[ \t\r\f]+', ' ', text)  # 去除多余的空格并去掉首尾空格，保留\n
    text = re.sub(r'\n', '.', text) # 替换\n
    return text

# 总结项目类型
def get_domain(description: str, readme: str) -> str:
    """
    使用LLM模型总结文本领域
    """
    readme_content = clean_markdown(readme) if readme else ""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert in software architecture and development, with deep knowledge of different types of open-source software projects.\n"
                "You know the following ML(machine learning) domains:\n"
                "agent, nlp, cv, audio, time series, ir, graph, security, tabular data, frameworks, MLOps platforms, model management, data processing pipelines, AutoML, deployment tools, academic (e.g., physics, economics), reinforcement learning, educational tools, probabilistic methods, miscellaneous utilities, docs.\n"
            },
            {
                "role": "user",
                "content": "According to the description and readme of following github repository, determine the domain it belongs to. Multiple selections are allowed from these domains, and respond with the category name. If the text does not fit into any of these categories(maybe some repos not related to ML), respond with 'others'.\n"
                "Respond **only** in the following format:\n"
                "<category_name>(, <category_name>, <category_name>)\n"
                "\n"
                "Where <category_name> is one of the categories such as cv, deployment tools, etc.\n"
                "\n"
                f"Description: {description}"
                f"Readme: {readme_content}"
                "\n"
            }
        ]
    )
    content = response.choices[0].message.content or "others"
    return content.strip()

# 总结pr类型
def get_pr_type(pr_title: str, pr_body: str) -> str:
    """
    使用LLM模型总结PR类型
    """
    pr_body_cleaned = clean_markdown(pr_body) if pr_body else ""
    pr_body_cleaned = pr_body_cleaned[:2000]  # 截断，防止过长
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert in software development and project management, with deep knowledge of different types of pull requests (PRs) in software projects.\n"
                "You know the following PR types:\n"
                "1) Bug fix\n"
                "2) Documentation\n"
                "3) Test\n"
                "4) Build\n"
                "5) Enhancement\n"
                "6) New feature\n"
            },
            {
                "role": "user",
                "content": "According to the title and body of the following PR, determine the type of PR it is."
                "Only one type is allowed, and if you cannot determine the type, respond with 'Others'."
                "Respond **only** in the following format:\n"
                "<type_name>\n"
                "\n"
                "Where <type_name> is one of the types such as Bug fix, Documentation, etc.\n"
                "\n"
                f"Title: {pr_title}\n"
                f"Body: {pr_body_cleaned}\n"
            }
        ]
    )
    content = response.choices[0].message.content or "Others"
    return content.strip()

# 总结commit message类型
def get_commit_type(commit_message: str) -> int:
    """
    使用LLM模型总结commit message类型
    """
    commit_message_cleaned = clean_markdown(commit_message) if commit_message else ""
    commit_message_cleaned = commit_message_cleaned[:1000]  # 截断，防止过长
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an expert in software development and project management, with deep knowledge of different types of commit messages in software projects.\n"
                "You know the following commit message types:\n"
                "1) what, to summarize the changes in this commit, including 1)Summarize Code Object Change 2)Describe Implementation Principle 3)Illustrate Function\n"
                "2) why, to describe the reasons for the changes, including 1)Describe Issue 2)Illustrate Requirement 3)Describe Objective 4)Imply Necessity\n"
            },
            {
                "role": "user",
                "content": "According to the following commit message, determine the type of commit it is."
                "Only one type is allowed, and if you cannot determine the type, respond with '7'."
                "Respond **only** in the following format:\n"
                "<type_number>\n"
                "\n"
                "Where <type_number> is one of the numbers: 0: missing what and why; 1: why only; 2: what only; 3: both what and why\n"
                "\n"
                f"Commit message: {commit_message_cleaned}\n"
            }
        ]
    )
    content = response.choices[0].message.content or "0"
    try:
        type_number = int(content.strip())
        if type_number not in range(4):
            type_number = 0
    except ValueError:
        type_number = 0
    return type_number

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.WARNING,
    )

    # 测试清洗函数
    sample_text = """
    # Sample Project

    ![badge](https://img.shields.io/badge/Example-Badge-blue)
    
    This is a sample project with some **bold text** and *italic text*.
    
    ```python
    print("Hello, World!")
    ```
    
    [Link to GitHub](https://github.com/example/sample-project)
    ![Contributors](https://img.shields.io/badge/Contributors-10-brightgreen)
    <img src="https://example.com/image.png" alt="Sample Image">
    """
    cleaned_text = clean_markdown(sample_text)
    print(f"Cleaned Text:{cleaned_text}")

    with open('data/paddle_repos_readme.json', 'r', encoding='utf-8') as f:
        repos = json.load(f)
    results = []
    for repo in tqdm(repos):
        readme = repo.get('readme', '')
        description = ""
        readme = clean_markdown(readme)
        domain = get_domain(description, readme)
        # print(f"Repo: {repo['name']}, Domain: {domain}")
        results.append({
            'name': repo['repo'],
            'domain': domain
        })
    with open('data/paddle_repos_domain.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
