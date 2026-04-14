"""
get_url_text.py — HTTP 请求工具模块

功能：封装 HTTP GET 请求，统一管理请求头（user-agent 和 cookie）。
      所有爬虫模块（scraping1~5）均通过本模块发送请求。

使用前准备：
    1. 打开浏览器，登录知乎（建议使用小号，避免主号被封）
    2. 按 F12 打开开发者工具 → Network 面板
    3. 随意访问一个知乎页面，复制请求中的 user-agent 和 cookie
    4. 将复制的值填入下方 headers 字典中

注意事项：
    - cookie 有时效性，失效后需要重新从浏览器获取
    - 若返回乱码或触发验证码，也需要更新 cookie
"""

import requests


def get_url_text(url):
    """
    发送 HTTP GET 请求并返回响应文本。

    参数:
        url (str): 目标请求地址

    返回:
        str: 响应的文本内容（HTML 或 JSON 字符串）
        None: 请求失败时隐式返回 None
    """
    headers = {
        "user-agent": "填写从浏览器获取的user-agent",
        "cookie": "填写从浏览器获取的cookie",
    }

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.text
    except requests.HTTPError as e:
        print(e)
        print("HTTPError")
    except requests.RequestException as e:
        print(e)
    except:
        print("Unknown Error !")
