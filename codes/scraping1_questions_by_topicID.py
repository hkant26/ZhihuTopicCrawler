"""
scraping1_questions_by_topicID.py — 根据话题ID抓取问题列表

功能：从知乎话题页面抓取该话题下的所有问题和专栏文章。
      通过遍历话题页面的5个板块（精华、时间线、热门动态、热门问题、最新问题），
      尽可能多地收集问题数据。每个板块上限约1000条。

输入：话题 ID（在知乎话题页面 URL 中获取，如 https://www.zhihu.com/topic/19555130）
输出：data/question_list.csv，包含字段：type, id, title, url, date

API 接口（v5.1）：
    - /feeds/essence/v2        — 讨论（精华推荐）
    - /feeds/timeline_activity/v2 — 讨论（按时间线）
    - /feeds/top_activity/v2   — 精华
    - /feeds/top_question/v2   — 等待回答（热门问题）
    - /feeds/new_question/v2   — 等待回答（最新问题）

最后运行时间：2024/11/16 12:32
"""


import os
import json
import pandas as pd
from datetime import datetime
from get_url_text import get_url_text


def parseJson(text):
    """
    解析知乎 API 返回的 JSON 数据，提取问题/专栏信息。

    JSON 结构中每条数据的 target.type 决定了内容类型：
    - "answer"   → 该条目来自某个回答，从中提取其所属问题的信息
    - "question" → 直接是一个问题
    - "article"  → 专栏文章

    参数:
        text (str): API 返回的 JSON 字符串

    返回:
        str: 下一页的请求 URL（用于分页翻页），无数据时返回 None
    """
    json_data = json.loads(text)
    lst = json_data["data"]
    nextUrl = json_data["paging"]["next"]

    if not lst:
        return

    for item in lst:
        type = item["target"]["type"]

        if type == "answer":
            cn_type = "问题_来自回答"
            question = item["target"]["question"]
            id = question["id"]
            title = question["title"]
            url = "https://www.zhihu.com/question/" + str(id)
            question_date = datetime.fromtimestamp(question["created"]).strftime(
                "%Y-%m-%d"
            )
            sml_list = [cn_type, id, title, url, question_date]
            q_list.append(sml_list)

        elif type == "question":
            cn_type = "问题"
            question = item["target"]
            id = question["id"]
            title = question["title"]
            url = "https://www.zhihu.com/question/" + str(id)
            question_date = datetime.fromtimestamp(question["created"]).strftime(
                "%Y-%m-%d"
            )
            sml_list = [cn_type, id, title, url, question_date]
            q_list.append(sml_list)

        elif type == "article":
            cn_type = "专栏"
            zhuanlan = item["target"]
            id = zhuanlan["id"]
            title = zhuanlan["title"]
            url = zhuanlan["url"]
            article_date = datetime.fromtimestamp(zhuanlan["created"]).strftime(
                "%Y-%m-%d"
            )
            sml_list = [cn_type, id, title, url, article_date]
            q_list.append(sml_list)

    return nextUrl


def save_data(q_list, filename):
    """
    将问题列表保存为 CSV 文件，支持增量更新。

    处理流程：
    1. 将内存中的数据转为 DataFrame
    2. 按 id 去重并按日期排序
    3. 若文件已存在，读取旧数据合并后再去重（实现增量更新）
    4. 保存到 CSV

    参数:
        q_list (list): 问题数据列表，每条为 [type, id, title, url, date]
        filename (str): 输出 CSV 文件路径
    """

    df = pd.DataFrame(q_list, columns=["type", "id", "title", "url", "date"])
    # 根据id去重，并按照时间排序
    df = df.drop_duplicates(subset=["id"]).sort_values(by="date")

    # 若文件已存在，则读取原文件，合并后去重，实现文件更新

    if os.path.exists(filename):
        df_original = pd.read_csv(filename)
        df = pd.concat([df_original, df], ignore_index=True)
        df = df.drop_duplicates(subset=["id"]).sort_values(by="date")

    df.to_csv(filename, index=False, header=True, encoding="utf-8")

    print(f"共保存{len(df)}条数据到{filename}")


def crawl_1(topicID):
    """
    抓取"讨论"板块的问题。

    包含两个子接口：
    - essence（精华推荐排序）
    - timeline_activity（按时间线排序）
    两者可能有重复，后续 save_data 会去重。

    参数:
        topicID (str): 知乎话题 ID
    """
    # 子接口1：精华推荐排序
    url = (
        "https://www.zhihu.com/api/v5.1/topics/"
        + topicID
        + "/feeds/essence/v2?offset=0&limit=50"
    )
    while url:
        try:
            text = get_url_text(url)
            url = parseJson(text)
        except:
            print(f"目前已有{len(q_list)}条数据")
            break

    # 子接口2：按时间线排序
    url = (
        "https://www.zhihu.com/api/v5.1/topics/"
        + topicID
        + "/feeds/timeline_activity/v2?offset=0&limit=50"
    )
    while url:
        try:
            text = get_url_text(url)
            url = parseJson(text)
        except:
            print(f"目前已有{len(q_list)}条数据")
            break

    print("crawl_讨论: 完成")


def crawl_2(topicID):
    """
    抓取"精华"板块的问题（热门动态排序）。

    参数:
        topicID (str): 知乎话题 ID
    """
    url = (
        "https://www.zhihu.com/api/v5.1/topics/"
        + topicID
        + "/feeds/top_activity/v2?offset=0&limit=50"
    )
    while url:
        try:
            text = get_url_text(url)
            url = parseJson(text)
        except:
            print(f"目前已有{len(q_list)}条数据")
            break
    print("crawl_精华: 完成")


def crawl_3(topicID):
    """
    抓取"等待回答"板块的问题。

    包含两个子接口：
    - top_question（热门问题排序）
    - new_question（最新问题排序）

    参数:
        topicID (str): 知乎话题 ID
    """
    # 子接口1：热门问题排序
    url = (
        "https://www.zhihu.com/api/v5.1/topics/"
        + topicID
        + "/feeds/top_question/v2?offset=0&limit=50"
    )
    while url:
        try:
            text = get_url_text(url)
            url = parseJson(text)
        except:
            print(f"目前已有{len(q_list)}条数据")
            break

    # 子接口2：最新问题排序
    url = (
        "https://www.zhihu.com/api/v5.1/topics/"
        + topicID
        + "/feeds/new_question/v2?offset=0&limit=50"
    )
    while url:
        try:
            text = get_url_text(url)
            url = parseJson(text)
        except:
            print(f"目前已有{len(q_list)}条数据")
            break

    print("crawl_等待回答: 完成")


if __name__ == "__main__":
    # 漩涡鸣人: 20204759
    # 春野樱: 20135411
    #TODO 指定要爬取的话题ID
    topicID_list = ["20204759", "20135411"]
    q_list = []  # parseJson 通过闭包向此列表追加数据

    for topicID in topicID_list:
        crawl_1(topicID)
        crawl_2(topicID)
        crawl_3(topicID)
        save_data(q_list, "data/question_list.csv")
