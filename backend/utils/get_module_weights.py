import json
import logging
import math
import os

logger = logging.getLogger(__name__)

def module_weights() -> dict:
    """
    获取模块重要度
    """
    if os.path.exists("data/paddle_repos_module_weights.json"):
        with open("data/paddle_repos_module_weights.json", 'r', encoding='utf-8') as f:
            module_weights = json.load(f)
    else:
        module_weights = {}

    return module_weights

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (PID %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO,
    )

    _ = module_weights()
    print('done')