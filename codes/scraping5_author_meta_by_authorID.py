"""
scraping5_author_meta_by_authorID.py — 根据用户Token获取用户资料

功能：遍历 scraping4.5 提取的用户 Token 列表，逐个访问用户主页，
      通过解析页面中内嵌的 JSON 数据获取用户详细资料。

前置条件：需先运行 scraping4.5_data_processing.py 生成 data/user_tokens.csv

输入：data/user_tokens.csv（由 scraping4.5 生成）
输出：data/author_meta_info.csv，包含字段：
      user_token, name, gender, IP_address, voteupCount, thankedCount,
      followerCount, favoritedCount, productCount, VIPs, identity, top_writer

解析方式：从用户主页 HTML 中提取 <script id="js-initialData"> 标签内的 JSON，
          该 JSON 包含用户的完整信息。

已知问题：
    - 约爬取 1000~2000 个用户后会触发验证码
    - 知乎乱码不影响用户 Token 的提取和用户页面的访问
    - 已封禁账号会自动检测并跳过

最后运行时间：2024/11/16 15:05
"""

import os
import time
import json
import pandas as pd
from bs4 import BeautifulSoup as bs
from get_url_text import get_url_text


def get_tokens(sourse_filename, data_store_file):
    """
    读取用户 Token 列表，并过滤掉已爬取过的用户。

    处理流程：
    1. 读取 user_tokens.csv 获取全部用户 Token
    2. 若输出文件已存在，读取已爬取的 Token 并做差集
    3. 若输出文件不存在，创建空文件并写入表头

    参数:
        sourse_filename (str): 用户 Token 列表文件路径（scraping4.5 输出）
        data_store_file (str): 用户资料输出文件路径

    返回:
        list: 待爬取的用户 Token 列表（已排除已爬取用户）
    """
    df = pd.read_csv(sourse_filename, header=None)
    token_list = df.iloc[:, 0].tolist()
    print(f"Total {len(token_list)} users")

    if not os.path.exists(data_store_file):
        a = pd.DataFrame(
            [],
            columns=[
                "user_token",
                "name",
                "gender",
                "IP_address",
                "voteupCount",
                "thankedCount",
                "followerCount",
                "favoritedCount",
                "productCount",
                "VIPs",
                "identity",
                "top_writer",
            ],
        )
        a.to_csv(data_store_file, index=False, header=True)
        print(f"Create new file: {data_store_file}")
    else:
        df_exist = pd.read_csv(data_store_file)
        token_exist = df_exist["user_token"].tolist()
        token_list = list(set(token_list) - set(token_exist))

    print(f"Find {len(token_list)} new users")
    return token_list


def get_author_info(user_text, token):
    """
    从用户主页 HTML 中解析用户详细资料。

    解析步骤：
    1. 用 BeautifulSoup 定位 <script id="js-initialData"> 标签
    2. 提取其中的 JSON 文本
    3. 从 JSON 中的 initialState.entities.users[token] 获取用户数据

    提取的字段：
    - 基础信息：token, name, gender, IP 归属地
    - 互动数据：获赞数, 被喜欢数, 粉丝数, 被收藏数
    - 创作数据：回答数 + 文章数
    - 身份信息：VIP 数量, 是否有身份认证徽章, 是否为优秀回答者

    参数:
        user_text (str): 用户主页的 HTML 文本
        token (str): 用户的 URL Token

    返回:
        list: 用户资料列表（12 个字段），解析失败时返回 None
    """
    try:
        json_text = bs(user_text, "html.parser").find("script", attrs={"id": "js-initialData"}).text
        json_data = json.loads(json_text)["initialState"]["entities"]["users"][token]

        token = json_data["urlToken"]
        name = json_data["name"]
        gender = json_data["gender"]  # 0=未知, 1=男, 2=女
        IP_address = json_data["ipInfo"][5:]  # 去掉 "IP 属地" 前缀
        voteupCount = json_data["voteupCount"]
        thankedCount = json_data["thankedCount"]
        followerCount = json_data["followerCount"]
        favoritedCount = json_data["favoritedCount"]
        productCount = json_data["answerCount"] + json_data["articlesCount"]
        VIPs = json_data["vipInfo"]["isVip"] + json_data["kvipInfo"]["isVip"]

        badge_types = {badge["type"] for badge in json_data["badgeV2"]["mergedBadges"]}
        identity = 1 if "identity" in badge_types else 0
        top_writer = 1 if "best" in badge_types else 0

        return [
            token,
            name,
            gender,
            IP_address,
            voteupCount,
            thankedCount,
            followerCount,
            favoritedCount,
            productCount,
            VIPs,
            identity,
            top_writer,
        ]
    except:
        print(f"{token} Text Error !")
        return None


def save_data(user_info_list, filename):
    """
    将用户资料追加保存到 CSV 文件（追加模式，不覆盖已有数据）。

    参数:
        user_info_list (list): 用户资料列表
        filename (str): 输出 CSV 文件路径
    """
    df = pd.DataFrame(
        user_info_list,
        columns=[
            "user_token",
            "name",
            "gender",
            "IP_address",
            "voteupCount",
            "thankedCount",
            "followerCount",
            "favoritedCount",
            "productCount",
            "VIPs",
            "identity",
            "top_writer",
        ],
    )

    df.to_csv(filename, index=False, mode="a", header=False)


# 运行前提：先运行 scraping4.5_data_processing.py 生成 user_tokens.csv
# 知乎乱码不会影响获取用户信息

if __name__ == "__main__":
    #TODO: 输入文件名
    token_list = get_tokens(
        sourse_filename="data/user_tokens.csv",
        data_store_file="data/author_meta_info.csv"
    )
    user_info_list = []

    error_num = 0
    for i, token in enumerate(token_list):
        if token:
            url = f"https://www.zhihu.com/people/{str(token)}"
            user_text = get_url_text(url)

            if user_text and ("该账号已" in user_text or "该用户已" in user_text):
                user_info = [token] + ["None"] * 11
                user_info_list.append(user_info)
                save_data(user_info_list, "data/author_meta_info.csv")
                user_info_list = []
                print(f"⚠️⚠️⚠️{token}已被封禁⚠️⚠️⚠️")
                continue

            user_info = get_author_info(user_text, token)

            if user_info:
                error_num = 0
                user_info_list.append(user_info)
            else:
                error_num += 1  # 判断连续错误，达到5个时认为出现验证码错误

        if error_num >= 5:
            print(f"⚠️⚠️⚠️需要填写验证码并重新运行⚠️⚠️⚠️")
            break

        if i % 30 == 0:
            time.sleep(0.5)
            save_data(user_info_list, "data/author_meta_info.csv")
            user_info_list = []

    save_data(user_info_list, "data/author_meta_info.csv")

    print("Finish!")
