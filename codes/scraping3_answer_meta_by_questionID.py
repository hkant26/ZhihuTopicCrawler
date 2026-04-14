"""
scraping3_answer_meta_by_questionID.py — 根据问题ID获取回答内容及元数据

⚠️ 已失效：自 2025/03/28 起，知乎对该 API 接口进行了加密，本脚本暂时无法使用。

功能：遍历 scraping2 生成的问题元数据列表，逐个问题调用知乎 API 获取所有回答。
      支持增量更新（已爬取的问题按时间排序只获取新回答）和断点续爬。

输入：data/question_meta_info.csv（由 scraping2 生成）
输出：data/answers_of_question/question_{QID}.csv（每个问题一个文件），包含字段：
      q_id, a_content, a_date, a_upvote, a_comment, a_id,
      au_name, au_gender, au_urltoken, au_followerCount, au_headline

API 接口：/api/v4/questions/{q_id}/feeds?include=content,author.follower_count

已知问题：
    - 爬取一段时间后会触发知乎验证码机制，导致 HTTPError
    - 需要手动更新 begin_index 从报错位置继续爬取
    - 若按时间排序更新时发生报错，需删除该问题对应的 CSV 重新爬取

最后运行时间：2025/1/9 1:39
"""

import re
import os
import json
import time
import pandas as pd
from datetime import datetime
from get_url_text import get_url_text


def get_q_list(filename):
    """
    从问题元数据 CSV 中读取问题列表，并按条件筛选。

    默认筛选条件：回答数 > 5（过滤回答过少的问题）。
    返回结果从后往前排列，以便优先爬取较新的问题。

    参数:
        filename (str): 问题元数据 CSV 文件路径

    返回:
        dict: {问题ID: 问题标题} 字典，按倒序排列
    """
    df = pd.read_csv(filename, encoding="utf-8")
    df = df[df["answerCount"] > 5]  # 默认爬取回答数大于5的问题
    # df = df[df["created_date"] >= "2024-10-15"]  # 可选要更新的问题的时间范围

    questions_dict = dict(zip(df["q_id"].astype("int64").tolist(), df["q_content"].tolist()))

    print(f"共有 {len(questions_dict)} 个回答数大于5且不重复的问题")

    return dict(reversed(questions_dict.items()))   # 从后往前爬


def parse_data(url, q_id):
    """
    请求知乎 API 并解析一页回答数据。

    从 API 返回的 JSON 中提取每条回答的：
    - 回答内容（去除 HTML 标签）
    - 回答日期、点赞数、评论数、回答 ID
    - 作者姓名、性别、URL Token、粉丝数、个人简介

    参数:
        url (str): API 请求地址
        q_id (int): 当前问题 ID

    返回:
        tuple: (回答数据列表, 下一页URL, 是否为最后一页)
    """
    text = get_url_text(url)

    try:
        parsed = json.loads(text)
        json_data = parsed["data"]
        next_url = parsed["paging"]["next"]
        is_end = parsed["paging"]["is_end"]
    except Exception as e:
        print(f"Error: {url}")
        print(e)

    one_q_all_answer = []

    for item in json_data:
        one_answer_list = []

        question_id = q_id
        target = item["target"]
        author = target["author"]
        answer_content = re.sub("<[^<]+?>", "", target["content"])
        answer_date = datetime.fromtimestamp(target["created_time"]).strftime(
            "%Y-%m-%d"
        )
        answer_upvote = target["voteup_count"]
        answer_comment = target["comment_count"]
        answer_id = target["id"]
        author_name = author["name"]
        author_gender = author["gender"]  # 1=男, 0=未知, 2=女
        author_url_token = author["url_token"]
        author_follower_count = author["follower_count"]
        author_headline = author["headline"]

        one_answer_list = [
            question_id,
            answer_content,
            answer_date,
            answer_upvote,
            answer_comment,
            answer_id,
            author_name,
            author_gender,
            author_url_token,
            author_follower_count,
            author_headline,
        ]
        one_q_all_answer.append(one_answer_list)

    return one_q_all_answer, next_url, is_end


def save_data(answer_info, q_id):
    """
    将某个问题的回答数据保存为 CSV 文件，支持增量更新。

    若该问题的 CSV 已存在，读取旧数据后合并，按 a_id 去重。

    参数:
        answer_info (list): 回答数据列表
        q_id (int): 问题 ID（用于生成文件名）
    """

    filename = f"data/answers_of_question/question_{str(q_id)}.csv"

    df = pd.DataFrame(
        answer_info,
        columns=[
            "q_id",
            "a_content",
            "a_date",
            "a_upvote",
            "a_comment",
            "a_id",
            "au_name",
            "au_gender",
            "au_urltoken",
            "au_followerCount",
            "au_headline",
        ],
    )
    if os.path.exists(filename):
        df_original = pd.read_csv(filename)
        df = pd.concat([df_original, df], ignore_index=True)
        df = df.drop_duplicates(subset=["a_id"]).sort_values(by="a_date")

    df.to_csv(filename, index=False, header=True)


if __name__ == "__main__":
    # TODO: 指定问题列表
    questions_dict = get_q_list("data/question_meta_info.csv")
    q_id_list = list(questions_dict.keys())

    # 也可手动输入问题 ID 以获取回答数据，整数类型
    # q_list = [24324127, 24399025]

    # 爬一段时间会触发知乎的验证码机制导致HTTPError报错，需要手动重新设置开始位置
    begin_index = 0  # 将发生报错的问题序号更新到这里即可
    for i, q_id in enumerate(q_id_list[begin_index:]):
        q_content = questions_dict.get(q_id, "None")

        print(f"\nquestion {i+begin_index} {q_content} Begin, qid: {q_id}")

        url = f"https://www.zhihu.com/api/v4/questions/{str(q_id)}/feeds?include=content%2Cauthor.follower_count"

        if_question_exist = os.path.exists(f"data/answers_of_question/question_{str(q_id)}.csv")
        get_data_by_time = False

        # ⚠️⚠️⚠️若按时间排序更新数据中发生报错，则需要删除该问题的对应的CSV文件，重新爬取⚠️⚠️

        if if_question_exist:
            data_existing = pd.read_csv(f"data/answers_of_question/question_{str(q_id)}.csv")
            a_id_existing = data_existing["a_id"].values.tolist()

            try:
                data, url, is_end = parse_data(url + "&order=updated", q_id)
                url = url + "&order=updated"
                get_data_by_time = True
            except:
                pass

        # 对于回答数很多的问题，报错时可在此处添加中途url，方便断点续爬
        # url = "" # 放入报错前最后输出的url
        # TODO

        page = 0
        is_end = False
        while not is_end:
            data, url, is_end = parse_data(url, q_id)

            save_data(data, q_id)  # 每页保存，防止中途报错丢失

            if get_data_by_time:
                a_id = [item[5] for item in data]
                if all(item in a_id_existing for item in a_id):
                    break

            page += 1
            if page % 10 == 0:
                time.sleep(0.5)
                try:
                    print(url)
                    print(f"文本示例：{data[-1][1][:15]}")
                except:
                    pass

        print(f"\nquestion {i+begin_index} {q_content} Finish")

    print("Finish!!")
