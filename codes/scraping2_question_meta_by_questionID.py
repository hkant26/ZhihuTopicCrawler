"""
scraping2_question_meta_by_questionID.py — 根据问题ID获取问题元数据

功能：遍历 scraping1 生成的问题列表，逐个访问问题页面，
      通过解析 HTML 中的 meta 标签提取问题的详细元数据。

输入：data/question_list.csv（由 scraping1 生成）
输出：data/question_meta_info.csv，包含字段：
      q_id, q_content, followerCount, viewCount, answerCount, topicTag, created_date

解析方式：使用 BeautifulSoup 解析问题页面 HTML 中的结构化数据标签（itemprop 属性）

已知问题：
    - 约爬取 250 条后可能触发乱码（知乎服务端动态加密），需手动更新 cookie
    - 2024/11/16 更新：似乎已不再出现乱码，但建议持续关注

最后运行时间：2024/11/16 12:51
"""


import os
import time
import pandas as pd
from bs4 import BeautifulSoup as bs
from get_url_text import get_url_text


def get_question_list(filename):
    """
    从问题列表 CSV 中读取并筛选问题。

    筛选逻辑（可根据需要调整）：
    - 排除专栏类型（type != "专栏"），只保留问题类内容
    - 按日期过滤（此处为 2024-10-14 之后）

    参数:
        filename (str): 问题列表 CSV 文件路径

    返回:
        list: 筛选后的问题数据列表，每条为 [type, id, title, url, date]
    """
    df = pd.read_csv(filename)
    # 可添加筛选条件
    df = df[df["type"] != "专栏"]
    df = df[df["date"] >= "2024-10-14"]
    q_list = df.values.tolist()
    return q_list


def get_question_data(html_text):
    """
    从问题页面的 HTML 中解析元数据。

    通过 BeautifulSoup 提取以下 HTML 标签中的信息：
    - <meta itemprop="name">          → 问题标题
    - <strong class="NumberBoard-itemValue"> → 关注者数（第1个）、浏览量（第2个）
    - <meta itemprop="answerCount">   → 回答数
    - <meta itemprop="keywords">      → 话题标签
    - <meta itemprop="dateCreated">   → 创建日期

    参数:
        html_text (str): 问题页面的 HTML 文本

    返回:
        list: [q_id, 问题内容, 关注者数, 浏览量, 回答数, 话题标签, 创建日期]
              解析失败时各字段填充 "UnknownError"
    """

    try:
        bsobj = bs(html_text, "html.parser")

        qContent = bsobj.find("meta", attrs={"itemprop": "name"})["content"]
        number_boards = bsobj.find_all("strong", attrs={"class": "NumberBoard-itemValue"})
        followerCount = number_boards[0]["title"]
        viewCount = number_boards[1]["title"]
        answerCount = bsobj.find("meta", attrs={"itemprop": "answerCount"})["content"]
        topicTag = bsobj.find("meta", attrs={"itemprop": "keywords"})["content"]
        date = bsobj.find("meta", attrs={"itemprop": "dateCreated"})["content"]

        return [q_id, qContent, followerCount, viewCount, answerCount, topicTag, date[:10]]

    except:
        print("Unknown Error !")
        return [
            q_id,
            "UnknownError",
            "UnknownError",
            "UnknownError",
            "UnknownError",
            "UnknownError",
            "UnknownError",
        ]


def save_data(q_info_list, filename):
    """
    将问题元数据保存为 CSV 文件，支持增量更新。

    处理流程：
    1. 若文件已存在，读取旧数据并合并
    2. 删除解析失败的记录（q_content == "UnknownError"）
    3. 按 q_id 去重（保留最新一条）
    4. 统一日期格式并按创建日期排序

    参数:
        q_info_list (list): 问题元数据列表
        filename (str): 输出 CSV 文件路径
    """
    df = pd.DataFrame(
        q_info_list,
        columns=[
            "q_id",
            "q_content",
            "followerCount",
            "viewCount",
            "answerCount",
            "topicTag",
            "created_date"
        ],
    )
    if os.path.exists(filename):
        df_old = pd.read_csv(filename)
        df = pd.concat([df_old, df], ignore_index=True)
        df = df[df["q_content"] != "UnknownError"]  # 删除已经被删除的问题
        df = df.drop_duplicates(subset=["q_id"], keep="last")
        df["created_date"] = df["created_date"].str.replace("-", "/")
        df["created_date"] = pd.to_datetime(df["created_date"])
        df = df.sort_values(by=["created_date"])

    df.to_csv(filename, index=False, header=True, encoding="utf-8")


# 代码一次只能跑250条，之后会变乱码，需要手动去浏览器更新cookie
# 2024/11/16更新：似乎不会再变乱码了，建议保持关注
if __name__ == "__main__":
    #TODO 指定问题列表
    q_list = get_question_list("data/question_list.csv")
    print(f"共{len(q_list)}个问题")
    q_info_list = []

    #TODO 可设置开始和结束位置，用于在出错中断时重新爬取
    # 例：q_list[100:] 表示从第 101 条开始
    for i, item in enumerate(q_list[:]):
        q_id = item[1]

        url = f"https://www.zhihu.com/question/{str(q_id)}"
        text = get_url_text(url)
        q_info = get_question_data(text)
        q_info_list.append(q_info)

        if i % 30 == 0:
            print(q_info[1])
            save_data(q_info_list, "data/question_meta_info.csv")
            q_info_list = []
            time.sleep(1)
            print(f"已保存{i+1}条数据")

    save_data(q_info_list, "data/question_meta_info.csv")

    print("Finish!!")
