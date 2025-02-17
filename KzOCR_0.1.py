import tkinter as tk
from tkinter import scrolledtext, messagebox
import base64
import json
import os
import ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from PIL import ImageGrab
import keyboard
import tempfile
import requests
import random
import json
from hashlib import md5

# 阿里云OCR配置
APP_CODE = "9b1c13fc02f54c96a3b33ff437f646ae"
REQUEST_URL = "https://gjbsb.market.alicloudapi.com/ocrservice/advanced"

class ScreenSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_ui()
        self.selection = None

    def setup_ui(self):
        """创建全屏半透明选择界面"""
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.root.attributes("-topmost", True)
        self.root.config(cursor="crosshair")

        self.canvas = tk.Canvas(self.root, bg="gray", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = self.root.winfo_pointerx()
        self.start_y = self.root.winfo_pointery()
        self.rect = None

    def on_drag(self, event):
        cur_x = self.root.winfo_pointerx()
        cur_y = self.root.winfo_pointery()
        
        if not self.rect:
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, cur_x, cur_y,
                outline="red", width=2, fill=""
            )
        else:
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = self.root.winfo_pointerx()
        end_y = self.root.winfo_pointery()
        
        # 确保坐标顺序正确
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        self.selection = (x1, y1, x2, y2)
        self.root.destroy()

    def get_selection(self):
        self.root.mainloop()
        return self.selection

class OCRApp:
    def __init__(self, master):
        self.master = master
        master.title("OCR文字识别工具")
        master.geometry("800x600")

        self.create_widgets()
        keyboard.add_hotkey("F4", self.start_screenshot_process)
        keyboard.add_hotkey("F5", self.start_baidu_translate)  # 新增F5热键

    def create_widgets(self):
        # 按钮框架
        button_frame = tk.Frame(self.master)
        button_frame.pack(padx=10, pady=5, fill=tk.X)

        # 截图识别按钮
        btn_ocr = tk.Button(button_frame, text="截图识别F4", command=self.start_screenshot_process)
        btn_ocr.pack(side=tk.LEFT, padx=5)
        
        # 翻译按钮
        btn_trans = tk.Button(button_frame, text="截图识别F5", command=self.start_baidu_translate)
        btn_trans.pack(side=tk.LEFT, padx=5)

        # 结果显示区域
        self.result_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD)
        self.result_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = tk.Label(self.master, textvariable=self.status_var, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.update_status("就绪（F4截图识别，F5翻译）")

    def update_status(self, message):
        self.status_var.set(message)
        self.master.update()

    def start_screenshot_process(self):
        try:
            self.update_status("请选择截图区域...")
            
            # 显示区域选择界面
            selector = ScreenSelector()
            selection = selector.get_selection()
            
            if not selection:
                self.update_status("已取消截图")
                return

            # 截取选定区域
            self.update_status("正在截取屏幕...")
            screenshot = ImageGrab.grab(bbox=selection)
            
            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                screenshot.save(tmp.name, "PNG")
                tmp_path = tmp.name

            # OCR识别
            self.update_status("正在识别文字...")
            result = self.ocr_request(tmp_path)
            
            # 清理临时文件
            os.unlink(tmp_path)
            
            # 显示结果
            self.show_result(result)
            self.update_status("识别完成")

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.update_status("发生错误")

# 修改翻译功能部分（baidu_api）
    def start_baidu_translate(self):
        """百度翻译实现"""
        try:
            text = self.result_area.get("1.0", tk.END).strip()
            if not text:
                self.update_status("没有需要翻译的内容")
                return

            self.update_status("正在翻译...")
            
            # 百度API配置
            appid = '20250217002276476'  #自己的id
            appkey = '4Bw2B2NDwVKb3nZikcM8' #自己的key
            url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
            
            # 自动判断翻译方向
            from_lang = 'auto'
            to_lang = 'zh'  # 默认翻译成中文
            
            # 如果检测到是中文，则翻译成英文
            if any('\u4e00' <= char <= '\u9fff' for char in text):
                to_lang = 'en'

            # 生成签名
            salt = random.randint(32768, 65536)
            sign_str = appid + text + str(salt) + appkey
            sign = md5(sign_str.encode()).hexdigest()

            # 构建请求参数
            payload = {
                'appid': appid,
                'q': text,
                'from': from_lang,
                'to': to_lang,
                'salt': salt,
                'sign': sign
            }

            # 发送请求
            response = requests.post(url, data=payload)
            result = response.json()

            # 处理结果
            if 'error_code' in result:
                error_msg = f"翻译错误 {result['error_code']}"
                if result['error_code'] == '54001':
                    error_msg += " (签名无效，请检查密钥)"
                raise Exception(error_msg)

            # 拼接翻译结果
            translated_text = '\n'.join([item['dst'] for item in result['trans_result']])
            
            # 显示结果
            self.result_area.delete("1.0", tk.END)
            self.result_area.insert(tk.END, translated_text)
            
            # 显示语言方向
            detected_lang = result['from']
            self.update_status(f"翻译完成 {detected_lang} → {to_lang}")

        except Exception as e:
            messagebox.showerror("翻译错误", str(e))
            self.update_status("翻译失败")

    def ocr_request(self, img_path):
        """调用阿里云OCR接口"""
        try:
            # 读取并编码图片
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                if not img_data:
                    raise ValueError("图片文件读取失败")

            # 构建请求参数
            params = {
                "prob": False,
                "charInfo": False,
                "rotate": False,
                "table": False,
                "sortPage": False,
                "noStamp": True,
                "figure": False,
                "row": False,
                "paragraph": False,
                "oricoord": True
            }

            headers = {
                'Authorization': f'APPCODE {APP_CODE}',
                'Content-Type': 'application/json; charset=UTF-8'
            }

            # 发送请求
            data = json.dumps({"img": img_data, **params}).encode('utf-8')
            req = Request(REQUEST_URL, data=data, headers=headers)
            
            # 禁用SSL验证（根据阿里云示例）
            context = ssl._create_unverified_context()
            response = urlopen(req, context=context)
            
            return json.loads(response.read().decode('utf-8'))

        except HTTPError as e:
            error = json.loads(e.read().decode('utf-8'))
            raise Exception(f"API错误: {error.get('error_msg', '未知错误')}")

    def show_result(self, result):
        """解析并显示识别结果"""
        if 'prism_wordsInfo' not in result:
            self.result_area.delete(1.0, tk.END)
            self.result_area.insert(tk.END, "未识别到文字")
            return

        # 提取所有文字内容
        full_text = '\n'.join([word['word'] for word in result['prism_wordsInfo']])
        
        self.result_area.delete(1.0, tk.END)
        self.result_area.insert(tk.END, full_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApp(root)
    
    # 添加退出提示
    def on_closing():
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()
