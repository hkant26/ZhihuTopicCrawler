# ZhihuTopicCrawler

一个知乎话题、问题、用户信息的爬虫

**⚠️ 2025/3/28 知乎加密了 API 接口，代码 s3.py（爬取问题下的回答内容）已不可用😭**

## **项目简介**

> 此知乎爬虫仅用于学习和研究目的。在未经知乎许可的情况下，请勿将其用于商业用途或大规模数据抓取，否则可能会违反知乎的使用条款和法律法规。
>
> 本项目从前人的爬虫代码出发，在此基础上做了大量修改，使之适用于目前的知乎 API，并添加了数据更新功能，从而实现对某一话题的数据追踪。他们是[机灵鹤 (Smart Crane)](https://smartcrane.tech/)、[Di Zhou](https://di-zhou.github.io/)，感谢两位老师。
>
> 在使用中若遇到任何问题欢迎以任何形式反馈，但作者能力很有限，反馈了也不一定能解决😇。

一个社科小萌新编写的知乎话题爬虫，它能：

1. 根据知乎话题 ID 爬取该话题标签下的**大部分**问题和专栏，支持多个话题爬取 [为什么不是全部问题](#scraping1_questions_by_topicidpy)
2. 根据问题列表爬取问题的元信息
3. ~~根据问题 ID 爬取该问题下所有的答案及答案对应的作者信息~~（⚠️ 已失效）
4. 根据用户主页 URL 爬取用户元信息
5. 根据问题 ID 和答案 ID 爬取对应评论区内容（一次只能抓取一个问题）

## **项目结构**

```
ZhihuTopicCrawler/
├── codes/                          # 爬虫脚本目录
│   ├── get_url_text.py             # HTTP 请求工具（共用模块）
│   ├── scraping1_questions_by_topicID.py      # 话题 → 问题列表
│   ├── scraping2_question_meta_by_questionID.py # 问题 → 元数据
│   ├── scraping3_answer_meta_by_questionID.py   # 问题 → 回答 ⚠️ 已失效
│   ├── scraping4_comments_by_answerID.py        # 回答 → 评论
│   ├── scraping4.5_data_processing.py           # 数据合并 + 用户token提取
│   └── scraping5_author_meta_by_authorID.py     # 用户token → 用户资料
├── tests/                          # 单元测试目录
│   ├── __init__.py
│   ├── test_get_url_text.py
│   ├── test_scraping1.py
│   ├── test_scraping2.py
│   ├── test_scraping3.py
│   ├── test_scraping4.py
│   ├── test_scraping4_5.py
│   └── test_scraping5.py
├── data/                           # 输出数据目录（运行后生成）
│   ├── question_list.csv
│   ├── question_meta_info.csv
│   ├── all_answers.csv
│   ├── user_tokens.csv
│   ├── author_meta_info.csv
│   ├── answers_of_question/        # 每个问题的回答（按问题ID分文件）
│   └── comments_of_question/       # 每个问题的评论（按问题ID分文件）
└── images/                         # README 图片资源
```

## **数据流水线**

脚本按顺序执行，每一阶段的输出 CSV 作为下一阶段的输入：

```
scraping1（话题 → 问题列表）
    → data/question_list.csv
        → scraping2（问题 → 元数据）
            → data/question_meta_info.csv
                → scraping3 ⚠️ 已失效（问题 → 回答）
                    → data/answers_of_question/question_{QID}.csv
                        → scraping4（回答 → 评论）
                        │   → data/comments_of_question/question_{QID}.csv
                        → scraping4.5（合并回答 + 提取用户token）
                            → data/all_answers.csv + data/user_tokens.csv
                                → scraping5（用户token → 用户资料）
                                    → data/author_meta_info.csv
```

## **快速开始**

### 环境准备

```bash
# 安装依赖
pip install requests pandas beautifulsoup4

# 创建数据输出目录
mkdir -p data/answers_of_question data/comments_of_question
```

### 配置 Cookie

> [!IMPORTANT]
>
> 使用前必须在 `codes/get_url_text.py` 中更新 `user-agent` 和 `cookie`
>
> **强烈建议注册一个小号并使用小号的 cookie，防止主号被封或出现全乱码 (￣▽￣)**

1. 打开浏览器，登录知乎（建议使用小号）
2. 按 F12 打开开发者工具 → Network 面板
3. 随意访问一个知乎页面，复制请求中的 `user-agent` 和 `cookie`
4. 将复制的值填入 `codes/get_url_text.py` 的 `headers` 字典中

### 运行爬虫

```bash
cd codes/

# 1. 爬取话题下的问题列表（修改脚本中的 topicID_list）
python3 scraping1_questions_by_topicID.py

# 2. 爬取问题元数据
python3 scraping2_question_meta_by_questionID.py

# 3. 爬取问题下的回答（⚠️ 当前已失效）
# python3 scraping3_answer_meta_by_questionID.py

# 4. 爬取评论（需先有回答数据）
python3 scraping4_comments_by_answerID.py

# 4.5 合并数据 + 提取用户token
python3 scraping4.5_data_processing.py

# 5. 爬取用户资料
python3 scraping5_author_meta_by_authorID.py
```

### 运行测试

```bash
# 在项目根目录下运行全部 69 个单元测试
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## **代码说明**

### **get_url_text.py**

所有爬虫模块共用的 HTTP 请求工具，封装了 `requests.get` 并统一管理请求头。cookie 失效或触发乱码时需在此处更新。

### **scraping1_questions_by_topicID.py**

根据知乎话题 ID 爬取该话题标签下的大部分问题和专栏，支持多个话题爬取。通过 `/api/v5.1/topics/{topicID}/feeds/` 接口遍历话题页的 5 个板块（精华推荐、时间线、热门动态、热门问题、最新问题）。

- **输入:** 话题 ID（如 `火影忍者` 的 ID 为 `19555130`，可从话题页 URL 中找到）
- **输出:** `data/question_list.csv`（字段：type, id, title, url, date）

> [!IMPORTANT]
> 由于知乎限制，各板块最多只能展示 1000 条数据，因此无法获取话题下的全部问题。代码会对讨论、等待回答板块分别按热门排序和时间排序爬取，以尽可能多地获取不重复数据。可通过爬取多个相似话题标签来最大化数据覆盖度。

### **scraping2_question_meta_by_questionID.py**

根据问题列表逐个访问问题页面，通过解析 HTML meta 标签提取问题元数据。

- **输入:** `data/question_list.csv`（可设置筛选条件）
- **输出:** `data/question_meta_info.csv`（字段：q_id, q_content, followerCount, viewCount, answerCount, topicTag, created_date）

> [!IMPORTANT]
> 知乎反爬机制可能将返回文本加密为乱码。之前约爬取 250 条后出现乱码，需手动更新 cookie。2024/11/16 后似乎已不再出现，但建议持续关注。

### **scraping3_answer_meta_by_questionID.py**

> [!IMPORTANT]
>
> **⚠️ 2025/3/28：知乎更新了加密，该脚本已不可用，请等待更新。**

根据问题 ID 调用知乎 API 获取所有回答及作者信息。支持增量更新和断点续爬。

- **输入:** `data/question_meta_info.csv`（可设置筛选条件）
- **输出:** `data/answers_of_question/question_{QID}.csv`（字段：q_id, a_content, a_date, a_upvote, a_comment, a_id, au_name, au_gender, au_urltoken, au_followerCount, au_headline）

> [!IMPORTANT]
>
> 1. 爬一段时间会触发验证码，需手动更新 `begin_index` 从报错位置继续爬取
> 2. 回答数多的问题可在标记位置添加中途 URL 实现断点续爬
> 3. 建议随时观察输出中是否出现乱码
> 4. 支持增量更新：已存在的问题会按时间排序只获取新回答
> 5. 若按时间排序更新时发生报错，需删除对应 CSV 重新爬取

### **scraping4_comments_by_answerID.py**

根据问题 ID 爬取所有回答下的根评论和子评论（嵌套回复），可还原完整的评论区回复关系。需先运行 `scraping3` 获取回答数据。

- **输入:** 问题 ID（需要 `data/answers_of_question/question_{QID}.csv` 已存在）
- **输出:** `data/comments_of_question/question_{QID}.csv`（字段：answer_id, comment_type, reply_comment_id, reply_root_comment_id, comment_id, comment_content, comment_date, comment_upvote, child_comment_count, author_name, author_url_token, author_gender, author_headline）

> [!IMPORTANT]
> 强烈推荐一次只爬取一个问题，爬取时间较长容易触发验证码。可通过多次运行爬取多个问题的评论区。

### **scraping4.5_data_processing.py**

纯数据处理脚本：将 `scraping3` 生成的所有回答 CSV 合并为 `data/all_answers.csv`，并提取不重复的用户 URL Token 列表 `data/user_tokens.csv`。

> 简单修改即可对评论区数据进行合并和用户清单提取。

### **scraping5_author_meta_by_authorID.py**

根据用户 URL Token 访问用户主页，解析页面中内嵌的 JSON 数据获取用户详细资料。自动检测并跳过已封禁账号，支持增量爬取（自动跳过已爬取的用户）。

- **输入:** `data/user_tokens.csv`
- **输出:** `data/author_meta_info.csv`（字段：user_token, name, gender, IP_address, voteupCount, thankedCount, followerCount, favoritedCount, productCount, VIPs, identity, top_writer）

> [!IMPORTANT]
> 知乎乱码不影响用户信息获取，但约爬取 1000~2000 条后会触发验证码，需手动验证后重新运行。

## **关键实现模式**

| 模式 | 说明 |
|------|------|
| **频率控制** | 每约 30 个请求暂停一次，并保存中间结果作为断点 |
| **增量爬取** | 脚本检测已有 CSV，追加并去重，而非从头重新爬取 |
| **验证码检测** | 连续错误计数器（`error_num > 5`）触发提前终止 |
| **数据存储** | 所有输出存放在 `data/` 目录下，CSV 格式，回答和评论按问题 ID 分文件存储 |

## **依赖**

- Python 3.9+
- `requests` — HTTP 请求
- `pandas` — 数据处理与 CSV 读写
- `beautifulsoup4` — HTML 解析（scraping2, scraping5）

```bash
pip install requests pandas beautifulsoup4
```
