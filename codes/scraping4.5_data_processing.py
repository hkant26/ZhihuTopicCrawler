"""
scraping4.5_data_processing.py — 数据合并与用户Token提取

功能：将 scraping3 生成的所有问题回答 CSV 合并为一个总文件，
      并从中提取不重复的用户 URL Token，供 scraping5 使用。

输入：data/answers_of_question/ 目录下所有 CSV 文件（由 scraping3 生成）
输出：
    - data/all_answers.csv    — 所有回答的合并数据
    - data/user_tokens.csv    — 去重后的用户 Token 列表（无表头，供 scraping5 直接读取）

备注：知乎返回的乱码不影响用户 Token 的提取，因为 Token 是英文/数字字符串。

最后运行时间：2024/11/16 15:05
"""

import os
import pandas as pd

#TODO:设置好文件路径
folder_path = "data/answers_of_question"

filename_list = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith(".csv")]

# 使用生成器逐个读取，避免一次性加载所有文件到内存
dfs = (pd.read_csv(file) for file in filename_list)

merged_df = pd.concat(dfs, axis=0, ignore_index=True)
user_token_df = merged_df.loc[:, ["au_urltoken", "au_name"]].drop_duplicates(subset=["au_urltoken"])

merged_df.to_csv("data/all_answers.csv", index=False, encoding="utf-8")
# 无表头，因为 scraping5 的 get_tokens 以 header=None 读取
user_token_df.to_csv("data/user_tokens.csv", index=False, encoding="utf-8", header=False)

print(
    f"所有回答已合并保存到 data/all_answers.csv 文件中, 共有 {len(filename_list)} 个问题，包含 {len(merged_df)} 条回答"
)
print(
    f"用户清单已保存到 data/user_tokens.csv 文件中, 共获取 {len(user_token_df)} 个不重复用户token"
)
