"""
This example describes how to use the workflow interface to stream chat.
"""

import os
import re
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
        print(f"请求错误: {e}", file=sys.stderr)
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
        print(f"成功从{json_filename}文件中读取参数", file=sys.stderr)
    else:
        raise FileNotFoundError("没有找到参数文件")
except FileNotFoundError:
    print("参数文件不存在，使用默认参数", file=sys.stderr)
    # 使用默认参数
    parameters = {
        "Examination_System": "1",
        "Grade": "1",
        "Grade_Range": "1",
        "Intended_Institution": "G5",
        "Intended_Major": "数学",
        "language_status": "雅思6.5",
        "Planned_Year": "1",
        "Strong_Subject_Categ": "1",
        "Student_Name": "乐乐",
        "Study_Region": "1"
    }
except json.JSONDecodeError:
    print("参数文件格式错误，使用默认参数", file=sys.stderr)
    # 使用默认参数
    parameters = {
        "Examination_System": "1",
        "Grade": "1",
        "Grade_Range": "1",
        "Intended_Institution": "G5",
        "Intended_Major": "数学",
        "language_status": "雅思6.5",
        "Planned_Year": "1",
        "Strong_Subject_Categ": "1",
        "Student_Name": "乐乐",
        "Study_Region": "1"
    }

# 兼容旧版参数文件，工作流请求统一只使用 language_status。
if 'language_status' not in parameters and 'ielts' in parameters:
    parameters['language_status'] = parameters.get('ielts', '')
parameters.pop('ielts', None)

# 映射数字编码到实际文本描述
parameter_mappings = {
    "Grade": {
        "9": "1",
        "10": "2",
        "11": "3",
        "12": "4"
    },
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
print("转换后的参数:", json.dumps(translated_params, ensure_ascii=False, indent=2), file=sys.stderr)

# 使用转换后的参数调用工作流
result = run_workflow(coze_api_token, workflow_id, translated_params)
if isinstance(result, dict) and result.get('code') not in (None, 0):
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1)

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

def _strip_json_fence(text):
    value = str(text or '').strip()
    fence_match = re.match(r'^```(?:json)?\s*(.*?)\s*```$', value, re.S | re.I)
    return fence_match.group(1).strip() if fence_match else value

def _try_parse_json(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None

    text = _strip_json_fence(value)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None

def _parse_fragmented_plan(value):
    if not isinstance(value, str):
        return None

    text = _strip_json_fence(value)
    decoder = json.JSONDecoder()
    fragments = []
    position = 0

    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text) or text[position] not in '[{':
            break
        try:
            fragment, position = decoder.raw_decode(text, position)
            fragments.append(fragment)
        except json.JSONDecodeError:
            break

    if len(fragments) < 2:
        return None

    plan = {
        'school_recommend': [],
        'timeline': [],
        'risk_plan': []
    }
    profile_keys = {
        'grade', 'examination_system', 'grade_range', 'strong_subject_categ',
        'planned_year', 'study_region', 'intended_institution', 'intended_major'
    }

    for fragment in fragments:
        if isinstance(fragment, list):
            first = next((item for item in fragment if isinstance(item, dict)), None)
            if first and ('school_name' in first or 'program_name' in first):
                plan['school_recommend'] = fragment
            elif first and ('stage' in first or 'time_range' in first):
                plan['timeline'] = fragment
            elif first and ('risk' in first or 'impact' in first or 'solution' in first):
                plan['risk_plan'] = fragment
            elif all(isinstance(item, str) for item in fragment):
                plan['missing_fields'] = fragment
        elif not isinstance(fragment, dict):
            continue
        elif isinstance(fragment.get('school_recommend'), list):
            plan.update(fragment)
        elif isinstance(fragment.get('student_profile'), dict):
            plan.update(fragment)
        elif profile_keys.intersection(fragment):
            plan['student_profile'] = fragment
        elif 'positioning' in fragment or 'strategy' in fragment or 'key_risks' in fragment:
            plan['summary'] = fragment
        elif 'school_name' in fragment:
            if str(fragment.get('school_name') or '').strip():
                plan['school_recommend'].append(fragment)
        elif 'stage' in fragment or 'time_range' in fragment:
            if fragment.get('stage') or fragment.get('tasks') or fragment.get('time_range'):
                plan['timeline'].append(fragment)
        elif {'academic', 'language', 'activities', 'materials'}.intersection(fragment):
            plan['bg_suggestion'] = fragment
        elif {'risk', 'impact', 'solution'}.intersection(fragment):
            if fragment.get('risk') or fragment.get('impact') or fragment.get('solution'):
                plan['risk_plan'].append(fragment)

    remainder = text[position:].strip()
    if remainder:
        first_line = remainder.splitlines()[0].strip()
        if first_line and not first_line.lower().startswith(('got it', 'first,', 'wait,')):
            plan['disclaimer'] = first_line

    return plan if _looks_like_plan_json(plan) else None

def _looks_like_plan_json(value):
    return isinstance(value, dict) and (
        'school_recommend' in value or
        (
            'student_profile' in value and
            ('timeline' in value or 'risk_plan' in value or 'bg_suggestion' in value)
        )
    )

def extract_plan_json(result):
    candidates = []

    def _walk(obj):
        if isinstance(obj, dict):
            if 'planning_json' in obj:
                candidates.append(obj['planning_json'])
            if 'data' in obj:
                candidates.append(obj['data'])
            if _looks_like_plan_json(obj):
                candidates.append(obj)
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for value in obj:
                _walk(value)
        elif isinstance(obj, str) and '{' in obj and '}' in obj:
            candidates.append(obj)

    _walk(result)

    for candidate in candidates:
        parsed = _try_parse_json(candidate)
        if not parsed:
            parsed = _parse_fragmented_plan(candidate)
        if not parsed:
            continue
        if 'planning_json' in parsed:
            nested = _try_parse_json(parsed.get('planning_json'))
            if _looks_like_plan_json(nested):
                return nested
        if 'data' in parsed:
            nested = _try_parse_json(parsed.get('data'))
            if _looks_like_plan_json(nested):
                return nested
        if _looks_like_plan_json(parsed):
            return parsed
    return None

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
plan_json = extract_plan_json(result)
content_to_export = json.dumps(plan_json, ensure_ascii=False, indent=2) if plan_json else (text if text else json.dumps(result, ensure_ascii=False, indent=2))
# 生成文件名，处理空值情况
intended_institution = parameters.get('Intended_Institution','')
extension = 'json' if plan_json else 'md'
filename = f"{parameters.get('Student_Name','学生')}_{intended_institution if intended_institution else '院校'}_{parameters.get('Intended_Major','专业')}.{extension}"
with open(filename, "w", encoding="utf-8") as f:
    f.write(content_to_export)
with open(filename, "r", encoding="utf-8") as f:
    print(f.read())
