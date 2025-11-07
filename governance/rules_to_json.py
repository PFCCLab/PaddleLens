import pandas as pd
import json


# 读取 Excel 文件中的 Sheet2
excel_file = 'data/paddle-rules.xlsx'  # 替换为你的文件名
df = pd.read_excel(excel_file, sheet_name='Sheet2')

# 将空白值统一转换为 None
df = df.where(pd.notnull(df), None)

# 将 Timestamp 类型转换为字符串，但保留 None（null 值）
df = df.applymap(lambda x: x.isoformat() if isinstance(x, pd.Timestamp) else x)

# 转换为 JSON 序列化列表
data_list = df.to_dict(orient='records')
json_output = json.dumps(data_list, ensure_ascii=False, indent=4)

# print(json_output)
with open('data/paddle-rules.json', 'w', encoding='utf-8') as f:
    f.write(json_output)