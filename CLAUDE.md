# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指引。

## 项目概述

ZhihuTopicCrawler 是一个基于 Python 的知乎爬虫工具，通过一系列按编号顺序执行的脚本，依次抓取话题、问题、回答、评论和用户资料。

**注意：** 自 2025/03/28 起，知乎对 API 进行了加密，导致 `scraping3_answer_meta_by_questionID.py` 无法使用。scraping1 模块已更新为使用新的 `/api/v5.1/` 接口。

## 运行脚本

每个脚本独立运行，无构建系统、测试套件或包管理配置。

```bash
# 直接运行各爬虫模块
python codes/scraping1_questions_by_topicID.py
python codes/scraping2_question_meta_by_questionID.py
# ... 以此类推
```

**运行前准备：** 每个脚本的 headers 字典（或 `get_url_text.py` 中）需要填入从浏览器获取的有效 `user-agent` 和 `cookie`。建议使用小号，爬取可能触发验证码或账号限制。

## 依赖（无 requirements.txt）

`requests`、`pandas`、`beautifulsoup4`，以及标准库模块（`json`、`time`、`datetime`、`re`、`os`）。

## 架构 — 流水线流程

脚本按顺序执行，每一阶段的输出 CSV 作为下一阶段的输入：

```
scraping1（话题 → 问题列表）
    → data/question_list.csv
        → scraping2（问题 → 元数据）
            → data/question_meta_info.csv
                → scraping3 ⚠️ 已失效（问题 → 回答）
                    → data/answers_of_question/question_{QID}.csv
                        → scraping4（回答 → 评论）
                            → data/comments_of_question/question_{QID}.csv
                        → scraping4.5（合并所有回答 + 提取用户token）
                            → data/all_answers.csv, data/user_tokens.csv
                                → scraping5（用户token → 用户资料）
                                    → data/author_meta_info.csv
```

- **`get_url_text.py`** — 所有爬虫共用的 HTTP 请求工具，存放 cookie/user-agent 配置。
- **`scraping1`** — 通过 `/api/v5.1/topics/{topicID}/feeds/` 接口抓取话题页面的 5 种 feed（精华、时间线、热门动态、热门问题、最新问题）。每个板块上限约 1000 条。
- **`scraping2`** — 通过 BeautifulSoup 解析 HTML meta 标签获取问题元数据。约 250 个请求后可能触发乱码。
- **`scraping3`** — **已废弃。** 原使用 `/api/v4/questions/{q_id}/feeds` 获取回答，知乎已加密该接口。
- **`scraping4`** — 抓取根评论（`/api/v4/answers/{id}/root_comments`）和子评论（`/api/v4/comment_v5/comment/{id}/child_comment`）。为避免检测，一次只处理一个问题。
- **`scraping4.5`** — 纯数据处理：用 pandas 合并回答 CSV 并提取唯一用户 token。
- **`scraping5`** — 通过解析 HTML 和内嵌 JSON（`<script id="js-initialData">`）抓取用户资料，自动检测已封禁账号。

## 关键实现模式

- **频率控制：** 每约 30 个请求暂停一次，并保存中间结果作为断点。
- **增量爬取：** 脚本检测已有 CSV，追加并去重，而非从头重新爬取。
- **验证码检测：** 连续错误计数器（`error_num > 5`）触发提前终止。
- **所有输出存放在 `data/`** 目录下，CSV 格式，回答和评论按问题分文件存储。
