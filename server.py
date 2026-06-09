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
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # 从stdout中提取MD内容（PlanStudy.py会将MD内容打印到stdout）
                md_content = result.get('stdout', '')
                
                response = {
                    'status': 'success',
                    'filename': filename,
                    'result': result,
                    'md_content': md_content
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
            # 列出当前目录下所有.md文件
            plans = []
            for filename in os.listdir(SCRIPT_DIR):
                if filename.endswith('.md'):
                    file_path = os.path.join(SCRIPT_DIR, filename)
                    if os.path.isfile(file_path):
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
            self.send_header('Content-type', 'application/json')
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
            
            # 检查文件是否存在且是.md文件
            if not os.path.exists(file_path) or not filename.endswith('.md'):
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
            
            # 检查文件是否存在且是.md文件
            if not os.path.exists(file_path) or not filename.endswith('.md'):
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
        if self.path == '/':
            # 返回HTML页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # 读取并返回HTML文件
            html_path = os.path.join(SCRIPT_DIR, 'plan_study_form.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
        elif self.path == '/view_plans.html' or self.path == '/view_plans':
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
