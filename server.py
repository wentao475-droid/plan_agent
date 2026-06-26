#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python服务器脚本，用于接收HTML页面发送的JSON数据并执行PlanStudy.py
"""

import http.server
import socketserver
import json
import mimetypes
import os
import subprocess
import sys

# 设置服务器端口
PORT = 8003

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def extract_planning_json(text):
    """Return a compact JSON string when stdout contains a structured plan."""
    value = (text or '').strip()
    if not value:
        return ''

    try:
        parsed = json.loads(value)
        if is_structured_plan(parsed):
            return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    fragmented = parse_fragmented_plan(value)
    if is_structured_plan(fragmented):
        return json.dumps(fragmented, ensure_ascii=False)

    start = value.find('{')
    end = value.rfind('}')
    if start >= 0 and end > start:
        try:
            parsed = json.loads(value[start:end + 1])
            if is_structured_plan(parsed):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return ''
    return ''

def parse_fragmented_plan(text):
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

    plan = {'school_recommend': [], 'timeline': [], 'risk_plan': []}
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
        elif {'positioning', 'strategy', 'key_risks'}.intersection(fragment):
            plan['summary'] = fragment
        elif 'school_name' in fragment:
            if str(fragment.get('school_name') or '').strip():
                plan['school_recommend'].append(fragment)
        elif {'stage', 'time_range'}.intersection(fragment):
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
    return plan

def is_structured_plan(value):
    return isinstance(value, dict) and (
        'school_recommend' in value or
        (
            'student_profile' in value and
            ('timeline' in value or 'risk_plan' in value or 'bg_suggestion' in value)
        )
    )

def extract_error_message(stdout_text, stderr_text):
    value = (stdout_text or '').strip()
    if value:
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                message = parsed.get('msg') or parsed.get('message')
                if message:
                    return message
        except json.JSONDecodeError:
            pass
    return (stderr_text or '').strip()

def is_error_artifact(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(4096).strip()
        parsed = json.loads(content)
        return isinstance(parsed, dict) and parsed.get('code') not in (None, 0)
    except Exception:
        return False

class RequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/process':
            # 获取请求体大小
            content_length = int(self.headers['Content-Length'])
            
            # 读取请求体数据
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # 解析URL编码的表单数据
            import urllib.parse
            form_data = urllib.parse.parse_qs(post_data)
            
            # 检查是否有JSON数据
            if 'json_data' not in form_data:
                self.send_error(400, '缺少JSON数据')
                return
            
            try:
                # 获取JSON数据
                json_data = form_data['json_data'][0]
                parameters = json.loads(json_data)
                
                # 获取学员姓名作为文件名
                student_name = parameters.get('Student_Name', '学员')
                filename = f"{student_name}_parameters.json"
                
                # 将JSON数据保存为文件
                file_path = os.path.join(SCRIPT_DIR, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(parameters, f, ensure_ascii=False, indent=4)
                
                # 执行PlanStudy.py脚本
                result = self.run_plan_study(file_path)
                
                # 返回执行结果
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                
                # 从stdout中提取方案内容（PlanStudy.py会将最终内容打印到stdout）
                md_content = result.get('stdout', '')
                planning_json = extract_planning_json(md_content)
                is_success = result.get('returncode') == 0
                
                response = {
                    'status': 'success' if is_success else 'error',
                    'filename': filename,
                    'result': result,
                    'md_content': md_content,
                    'planning_json': planning_json,
                    'message': extract_error_message(md_content, result.get('stderr', ''))
                }
                
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
            except json.JSONDecodeError:
                self.send_error(400, 'JSON格式错误')
            except Exception as e:
                self.send_error(500, f'服务器错误: {str(e)}')
        else:
            self.send_error(404, '页面未找到')
    
    def run_plan_study(self, json_file):
        """运行PlanStudy.py脚本"""
        try:
            # 构造命令，传递参数文件路径作为命令行参数
            cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'PlanStudy.py'), json_file]
            
            # 设置环境变量
            env = os.environ.copy()
            
            # 执行脚本并捕获输出
            result = subprocess.run(
                cmd,
                cwd=SCRIPT_DIR,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 返回执行结果
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except Exception as e:
            return {
                'stdout': '',
                'stderr': f'执行脚本时发生错误: {str(e)}',
                'returncode': 1
            }
    
    def send_error(self, code, message=None):
        """重写send_error方法，支持中文错误信息"""
        try:
            # 直接构造响应，避免父类的编码问题
            self.send_response(code)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            error_message = f"Error {code}: {message if message else 'Unknown error'}"
            self.wfile.write(error_message.encode('utf-8'))
        except Exception as e:
            # 如果还是出错，发送最基本的错误信息
            try:
                self.send_response(code)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"Error {code}".encode('utf-8'))
            except:
                pass
    
    def get_plans_list(self):
        """获取方案列表"""
        try:
            # 列出当前目录下所有方案文件
            plans = []
            for filename in os.listdir(SCRIPT_DIR):
                is_plan_file = (
                    filename.endswith('.md') or
                    (filename.endswith('.json') and filename != 'plans.json' and not filename.endswith('_parameters.json'))
                )
                if is_plan_file:
                    file_path = os.path.join(SCRIPT_DIR, filename)
                    if os.path.isfile(file_path):
                        if is_error_artifact(file_path):
                            continue
                        # 获取文件信息
                        file_info = os.stat(file_path)
                        plans.append({
                            'filename': filename,
                            'size': file_info.st_size,
                            'mtime': file_info.st_mtime
                        })
            
            # 按修改时间降序排序
            plans.sort(key=lambda x: x['mtime'], reverse=True)
            
            # 返回方案列表
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(plans, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f'获取方案列表失败: {str(e)}')
    
    def view_plan_content(self):
        """查看方案内容"""
        try:
            # 解析URL参数
            import urllib.parse
            params = urllib.parse.parse_qs(self.path.split('?')[1] if '?' in self.path else '')
            
            if 'filename' not in params:
                self.send_error(400, '缺少文件名参数')
                return
            
            filename = params['filename'][0]
            file_path = os.path.join(SCRIPT_DIR, filename)
            
            # 检查文件是否存在且是方案文件
            if not os.path.exists(file_path) or not (filename.endswith('.md') or filename.endswith('.json')):
                self.send_error(404, '文件不存在')
                return
            
            # 返回文件内容
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        except Exception as e:
            self.send_error(500, f'查看方案内容失败: {str(e)}')
    
    def download_plan_file(self):
        """下载方案文件"""
        try:
            # 解析URL参数
            import urllib.parse
            params = urllib.parse.parse_qs(self.path.split('?')[1] if '?' in self.path else '')
            
            if 'filename' not in params:
                self.send_error(400, '缺少文件名参数')
                return
            
            filename = params['filename'][0]
            file_path = os.path.join(SCRIPT_DIR, filename)
            
            # 检查文件是否存在且是方案文件
            if not os.path.exists(file_path) or not (filename.endswith('.md') or filename.endswith('.json')):
                self.send_error(404, '文件不存在')
                return
            
            # 返回文件内容，设置为下载
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f'下载方案文件失败: {str(e)}')

    def serve_asset(self):
        """Serve local static assets."""
        try:
            import urllib.parse

            asset_name = urllib.parse.unquote(self.path.split('?', 1)[0][len('/assets/'):])
            assets_dir = os.path.join(SCRIPT_DIR, 'assets')
            file_path = os.path.abspath(os.path.join(assets_dir, asset_name))
            assets_root = os.path.abspath(assets_dir)

            if not file_path.startswith(assets_root + os.sep) or not os.path.isfile(file_path):
                self.send_error(404, 'Asset not found')
                return

            content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()

            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, f'Asset error: {str(e)}')
    
    def do_GET(self):
        """处理GET请求"""
        request_path = self.path.split('?', 1)[0]

        if request_path in ('/', '/plan_study_form.html', '/plan_study_form'):
            # 返回HTML页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # 读取并返回HTML文件
            html_path = os.path.join(SCRIPT_DIR, 'plan_study_form.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
        elif request_path in ('/view_plans.html', '/view_plans'):
            # 返回查看方案页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # 读取并返回HTML文件
            html_path = os.path.join(SCRIPT_DIR, 'view_plans.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
        elif self.path.startswith('/plan_report'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html_path = os.path.join(SCRIPT_DIR, 'plan_report.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
        elif self.path.startswith('/plans'):
            # 获取方案列表
            self.get_plans_list()
        elif self.path.startswith('/assets/'):
            self.serve_asset()
        elif self.path.startswith('/view_plan'):
            # 查看方案内容
            self.view_plan_content()
        elif self.path.startswith('/download_plan'):
            # 下载方案文件
            self.download_plan_file()
        else:
            self.send_error(404, '页面未找到')

def run_server():
    """启动服务器"""
    with socketserver.TCPServer(('', PORT), RequestHandler) as httpd:
        print(f"服务器已启动，监听端口 {PORT}")
        print(f"请在浏览器中访问 http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")

if __name__ == "__main__":
    run_server()
