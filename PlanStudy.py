"""
This example describes how to use the workflow interface to stream chat.
"""

import os
# Our official coze sdk for Python [cozepy](https://github.com/coze-dev/coze-py)
from cozepy import COZE_CN_BASE_URL

# Get an access_token through personal access token or oauth.
coze_api_token = 'pat_OCu71tW8MD9hjLPvRrJiSVtZdWibwLkHkY7AWRvGrWDz1BcBfMVJGKuCd6URmZFS'
# The default access is api.coze.com, but if you need to access api.coze.cn,
# please use base_url to configure the api endpoint to access
coze_api_base = COZE_CN_BASE_URL

from cozepy import Coze, TokenAuth, Stream, WorkflowEvent, WorkflowEventType  # noqa

# Init the Coze client through the access_token.
coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)

# Create a workflow instance in Coze, copy the last number from the web link as the workflow's ID.
workflow_id = '7584382854248742921'



# # The stream interface will return an iterator of WorkflowEvent. Developers should iterate
# # through this iterator to obtain WorkflowEvent and handle them separately according to
# # the type of WorkflowEvent.
# def handle_workflow_iterator(stream: Stream[WorkflowEvent]):
#     for event in stream:
#         if event.event == WorkflowEventType.MESSAGE:
#             print("got message", event.message)
#         elif event.event == WorkflowEventType.ERROR:
#             print("got error", event.error)
#         elif event.event == WorkflowEventType.INTERRUPT:
#             handle_workflow_iterator(
#                 coze.workflows.runs.resume(
#                     workflow_id=workflow_id,
#                     event_id=event.interrupt.interrupt_data.event_id,
#                     resume_data="hey",
#                     interrupt_type=event.interrupt.interrupt_data.type,
#                 )
#             )


# handle_workflow_iterator(
#     coze.workflows.runs.stream(
#         workflow_id=workflow_id,
#     )
# )

import requests
import json
 
def run_workflow(api_key, workflow_id, parameters):
    url = "https://api.coze.cn/v1/workflow/run"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "workflow_id": workflow_id,
        "parameters": parameters,
        "is_async": False  # 同步执行
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None
 
# 使用示例
# 尝试从环境变量获取JSON文件名，否则使用默认文件名
import os

# 导入sys模块用于命令行参数处理
import sys

# 首先检查命令行参数
json_filename = None
if len(sys.argv) > 1:
    json_filename = sys.argv[1]

# 如果没有命令行参数，从环境变量获取
if not json_filename:
    json_filename = os.environ.get('PARAMETERS_FILE')

# 如果没有设置环境变量，尝试使用学员命名的参数文件
if not json_filename:
    # 尝试查找以"_parameters.json"结尾的文件
    for filename in os.listdir('.'):
        if filename.endswith('_parameters.json'):
            json_filename = filename
            break

# 如果还是没有找到，使用默认参数
parameters = None

try:
    if json_filename:
        with open(json_filename, 'r', encoding='utf-8') as f:
            parameters = json.load(f)
        print(f"成功从{json_filename}文件中读取参数")
    else:
        raise FileNotFoundError("没有找到参数文件")
except FileNotFoundError:
    print("参数文件不存在，使用默认参数")
    # 使用默认参数
    parameters = {
        "Examination_System": "1",
        "Grade": "1",
        "Grade_Range": "1",
        "Intended_Institution": "G5",
        "Intended_Major": "数学",
        "ielts": "6.5",
        "Planned_Year": "1",
        "Strong_Subject_Categ": "1",
        "Student_Name": "乐乐",
        "Study_Region": "1"
    }
except json.JSONDecodeError:
    print("参数文件格式错误，使用默认参数")
    # 使用默认参数
    parameters = {
        "Examination_System": "1",
        "Grade": "1",
        "Grade_Range": "1",
        "Intended_Institution": "G5",
        "Intended_Major": "数学",
        "ielts": "6.5",
        "Planned_Year": "1",
        "Strong_Subject_Categ": "1",
        "Student_Name": "乐乐",
        "Study_Region": "1"
    }

# 映射数字编码到实际文本描述
parameter_mappings = {
    "Examination_System": {
        "1": "ALEVEL",
        "2": "IB",
        "3": "AP",
        "4": "其他"
    }
}

# 将参数中的数字编码转换为实际文本
translated_params = parameters.copy()
for param_name, mapping in parameter_mappings.items():
    if param_name in translated_params and translated_params[param_name] in mapping:
        translated_params[param_name] = mapping[translated_params[param_name]]

for param_name in ("Grade_Range", "Strong_Subject_Categ", "Planned_Year", "Study_Region"):
    if param_name in translated_params and translated_params[param_name] != "":
        translated_params[param_name] = int(translated_params[param_name])

# 打印转换后的参数供调试
print("转换后的参数:", json.dumps(translated_params, ensure_ascii=False, indent=2))

# 使用转换后的参数调用工作流
result = run_workflow(coze_api_token, workflow_id, translated_params)
def _find_best_text(obj):
    best = ""
    def _walk(x):
        nonlocal best
        if isinstance(x, str):
            s = x.strip()
            if ('\n' in s or len(s) > 200) and len(s) > len(best):
                best = s
        elif isinstance(x, dict):
            for v in x.values():
                _walk(v)
        elif isinstance(x, list):
            for v in x:
                _walk(v)
    _walk(obj)
    return best

def extract_markdown(result):
    if not result:
        return ""
    
    # 尝试从标准 Coze 响应结构中提取
    # 结构通常是: {"code": 0, "data": "{\"data\": \"markdown content\", ...}", ...}
    if isinstance(result, dict) and "data" in result:
        data_field = result["data"]
        if isinstance(data_field, str):
            try:
                # 尝试解析内部 JSON 字符串
                inner_data = json.loads(data_field)
                if isinstance(inner_data, dict) and "data" in inner_data:
                    return inner_data["data"]
            except json.JSONDecodeError:
                pass
    
    # 如果上述特定结构匹配失败，使用启发式查找
    return _find_best_text(result)

text = extract_markdown(result)
content_to_export = text if text else json.dumps(result, ensure_ascii=False, indent=2)
# 生成文件名，处理空值情况
intended_institution = parameters.get('Intended_Institution','')
filename = f"{parameters.get('Student_Name','学生')}_{intended_institution if intended_institution else '院校'}_{parameters.get('Intended_Major','专业')}.md"
with open(filename, "w", encoding="utf-8") as f:
    f.write(content_to_export)
with open(filename, "r", encoding="utf-8") as f:
    print(f.read())
