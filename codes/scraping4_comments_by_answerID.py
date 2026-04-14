"""
scraping4_comments_by_answerID.py — 根据问题ID获取所有回答下的评论

功能：给定一个问题 ID，读取该问题下所有回答的 ID（需先运行 scraping3），
      然后逐个回答抓取其根评论和子评论（嵌套回复）。

输入：问题 ID（需要 data/answers_of_question/question_{QID}.csv 已存在）
输出：data/comments_of_question/question_{QID}.csv，包含字段：
      answer_id, comment_type, reply_comment_id, reply_root_comment_id,
      comment_id, comment_content, comment_date, comment_upvote,
      child_comment_count, author_name, author_url_token, author_gender, author_headline

API 接口：
    - 根评论：/api/v4/answers/{answer_id}/root_comments
    - 子评论：/api/v4/comment_v5/comment/{comment_id}/child_comment

注意事项：
    - 强烈建议一次只爬取一个问题，爬取时间较长，容易触发反爬虫机制
    - 连续 5 次请求失败则判定为需要验证码，自动终止

最后运行时间：2024/12/1 23:45
"""


# %%
import re
import os
import json
import time
import pandas as pd
from datetime import datetime
from get_url_text import get_url_text


# %%
def get_answer_id(question_id: str) -> list:
    """
    从本地 CSV 文件中读取指定问题下所有回答的 ID 列表。

    参数:
        question_id (str): 问题 ID

    返回:
        list: 回答 ID 列表。若数据文件不存在则返回空列表。
    """
    file_name = f"data/answers_of_question/question_{question_id}.csv"
    if not os.path.exists(file_name):
        print(
            f"问题 {question_id} 数据文件不存在，请先运行 scraping3.py 爬取问题数据。"
        )
        return []
    df = pd.read_csv(file_name)

    return df["a_id"].tolist()


# %%
def parse_root_comment(json_data: dict, answer_id: str) -> list:
    """
    解析单条根评论的 JSON 数据。

    根评论没有回复目标，因此 reply_comment_id 和 reply_root_comment_id 为空。

    参数:
        json_data (dict): 单条评论的 JSON 数据
        answer_id (str): 所属回答的 ID

    返回:
        list: 评论数据列表，包含 13 个字段
    """
    comment_type = "根评论"
    reply_comment_id = ""
    reply_root_comment_id = ""
    comment_id = json_data["id"]
    comment_content = re.sub(r"<.*?>", "", json_data["content"])
    comment_date = datetime.fromtimestamp(json_data["created_time"]).strftime(
        "%Y-%m-%d"
    )
    comment_upvote = json_data["vote_count"]
    child_comment_count = json_data["child_comment_count"]
    author_name = json_data["author"]["member"]["name"]
    author_url_token = json_data["author"]["member"]["url_token"]
    author_gender = json_data["author"]["member"]["gender"]
    author_headline = json_data["author"]["member"]["headline"]

    return [
        answer_id,
        comment_type,
        reply_comment_id,
        reply_root_comment_id,
        comment_id,
        comment_content,
        comment_date,
        comment_upvote,
        child_comment_count,
        author_name,
        author_url_token,
        author_gender,
        author_headline,
    ]


# %%
def get_root_comments(answer_id: str) -> pd.DataFrame:
    """
    获取某条回答下的所有根评论。

    通过分页遍历 API，每页最多 20 条评论，直到 data 为空列表。
    每 30 页暂停 0.5 秒以降低请求频率。

    参数:
        answer_id (str): 回答 ID

    返回:
        pd.DataFrame: 包含所有根评论的 DataFrame，失败时返回 None
    """
    try:
        comments_list = []

        url = f"https://www.zhihu.com/api/v4/answers/{answer_id}/root_comments?limit=20&offset=0&order_by=score&status=open"
        text = get_url_text(url)
        parsed = json.loads(text)
        json_data = parsed["data"]
        count = 0

        while json_data:
            for item in json_data:
                root_comment_data = parse_root_comment(item, answer_id)
                comments_list.append(root_comment_data)

            url = parsed["paging"]["next"]
            text = get_url_text(url)
            parsed = json.loads(text)
            json_data = parsed["data"]
            count += 1

            if count % 30 == 0:
                time.sleep(0.5)
                print(f"评论示例：{root_comment_data[4][:15]}")

        df_comments = pd.DataFrame(
            comments_list,
            columns=[
                "answer_id",
                "comment_type",
                "reply_comment_id",
                "reply_root_comment_id",
                "comment_id",
                "comment_content",
                "comment_date",
                "comment_upvote",
                "child_comment_count",
                "author_name",
                "author_url_token",
                "author_gender",
                "author_headline",
            ],
        )

        return df_comments
    except:
        print(f"获取 {answer_id} 评论失败")
        return None


# %%
def parse_child_comment(json_data: dict, answer_id: str) -> list:
    """
    解析单条子评论（嵌套回复）的 JSON 数据。

    子评论具有回复目标：
    - reply_comment_id: 直接回复的评论 ID
    - reply_root_comment_id: 所属的根评论 ID

    注意：子评论的点赞字段名为 like_count，与根评论的 vote_count 不同。

    参数:
        json_data (dict): 单条子评论的 JSON 数据
        answer_id (str): 所属回答的 ID

    返回:
        list: 评论数据列表，包含 13 个字段
    """
    comment_type = "子评论"
    reply_comment_id = json_data["reply_comment_id"]
    reply_root_comment_id = json_data["reply_root_comment_id"]
    comment_id = json_data["id"]
    comment_content = json_data["content"]
    comment_date = datetime.fromtimestamp(json_data["created_time"]).strftime(
        "%Y-%m-%d"
    )
    comment_upvote = json_data["like_count"]  # 子评论用 like_count 而非根评论的 vote_count
    child_comment_count = json_data["child_comment_count"]
    author_name = json_data["author"]["name"]
    author_url_token = json_data["author"]["url_token"]
    author_gender = json_data["author"]["gender"]
    author_headline = json_data["author"]["headline"]

    return [
        answer_id,
        comment_type,
        reply_comment_id,
        reply_root_comment_id,
        comment_id,
        comment_content,
        comment_date,
        comment_upvote,
        child_comment_count,
        author_name,
        author_url_token,
        author_gender,
        author_headline,
    ]


# %%
def get_child_comments(comment_item: list) -> pd.DataFrame:
    """
    获取某条根评论下的所有子评论。

    通过分页遍历子评论 API，每页最多 20 条。

    参数:
        comment_item (list): [answer_id, root_comment_id]

    返回:
        pd.DataFrame: 包含所有子评论的 DataFrame，失败时返回 None
    """
    try:
        answer_id, root_comment_id = comment_item
        comments_list = []

        url = f"https://www.zhihu.com/api/v4/comment_v5/comment/{root_comment_id}/child_comment?limit=20&offset=0"
        text = get_url_text(url)
        parsed = json.loads(text)
        json_data = parsed["data"]
        count = 0

        while json_data:
            for item in json_data:
                root_comment_data = parse_child_comment(item, answer_id)
                comments_list.append(root_comment_data)

            url = parsed["paging"]["next"]
            text = get_url_text(url)
            parsed = json.loads(text)
            json_data = parsed["data"]
            count += 1

            if count % 30 == 0:
                time.sleep(0.5)
                print(f"评论示例：{root_comment_data[4][:15]}")

        df_comments = pd.DataFrame(
            comments_list,
            columns=[
                "answer_id",
                "comment_type",
                "reply_comment_id",
                "reply_root_comment_id",
                "comment_id",
                "comment_content",
                "comment_date",
                "comment_upvote",
                "child_comment_count",
                "author_name",
                "author_url_token",
                "author_gender",
                "author_headline",
            ],
        )

        return df_comments
    except:
        print(f"获取 {root_comment_id} 子评论失败")
        return None


# %%
def save_data(df_comments: pd.DataFrame, question_id: str) -> None:
    """
    将评论数据保存为 CSV 文件，支持增量更新。

    若文件已存在，合并旧数据后按 comment_id 去重。

    参数:
        df_comments (pd.DataFrame): 评论数据
        question_id (str): 问题 ID（用于生成文件名）
    """
    filename = f"data/comments_of_question/question_{question_id}.csv"

    df_tosave = df_comments

    if os.path.exists(filename):
        df_original = pd.read_csv(filename)
        df_tosave = pd.concat([df_original, df_tosave], ignore_index=True)
    df_tosave = df_tosave.drop_duplicates(subset=["comment_id"]).sort_values(
        by="comment_date"
    )
    df_tosave.to_csv(filename, index=False, header=True)


# %%
if __name__ == "__main__":
    # 填写要爬取评论的问题 ID
    # 需要提前使用scraping3.py爬取问题信息并保存到data文件夹中，因为要使用问题中的回答 ID
    # 强烈建议一次只运行一个问题，因为爬取评论需要时间较长，容易触发知乎反爬虫机制
    # TODO:
    question_id_list = ["436790259"]
    for question_id in question_id_list:
        answer_id_list = get_answer_id(question_id)
        df_all_comments = pd.DataFrame()

        error_num = 0
        for i, answer_id in enumerate(answer_id_list):
            df_root_comments = get_root_comments(answer_id)

            if df_root_comments is None:
                error_num += 1
            else:
                error_num = 0
                df_all_comments = pd.concat([df_all_comments, df_root_comments])
                save_data(df_all_comments, question_id)
            if error_num > 5:
                print(f"⚠️⚠️⚠️需要填写验证码⚠️⚠️⚠️")
                break

            if i % 30 == 0:
                time.sleep(0.5)

        comment_item_list = df_all_comments[df_all_comments["child_comment_count"] > 0][
            ["answer_id", "comment_id"]
        ].values.tolist()

        for i, comment_item in enumerate(comment_item_list):
            df_child_comments = get_child_comments(comment_item)

            if df_child_comments is None:
                error_num += 1
            else:
                error_num = 0
                df_all_comments = pd.concat([df_all_comments, df_child_comments])

            if error_num > 5:
                print(f"⚠️⚠️⚠️需要填写验证码⚠️⚠️⚠️")
                break

            if i % 30 == 0:
                time.sleep(0.5)
                save_data(df_all_comments, question_id)

        save_data(df_all_comments, question_id)
        print(f"问题 {question_id} 评论数据已保存。")
    print("所有问题评论数据已保存。")
