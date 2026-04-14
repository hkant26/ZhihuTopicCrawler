import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

import scraping1_questions_by_topicID as s1


SAMPLE_JSON_ANSWER = json.dumps({
    "data": [{
        "target": {
            "type": "answer",
            "question": {
                "id": 12345,
                "title": "Test Question From Answer",
                "created": 1700000000
            }
        }
    }],
    "paging": {"next": "https://zhihu.com/api/next"}
})

SAMPLE_JSON_QUESTION = json.dumps({
    "data": [{
        "target": {
            "type": "question",
            "id": 67890,
            "title": "Direct Question",
            "created": 1700100000
        }
    }],
    "paging": {"next": "https://zhihu.com/api/next"}
})

SAMPLE_JSON_ARTICLE = json.dumps({
    "data": [{
        "target": {
            "type": "article",
            "id": 99999,
            "title": "Test Article",
            "url": "https://zhuanlan.zhihu.com/p/99999",
            "created": 1700200000
        }
    }],
    "paging": {"next": "https://zhihu.com/api/next"}
})

SAMPLE_JSON_EMPTY = json.dumps({
    "data": [],
    "paging": {"next": None}
})


class TestParseJson(unittest.TestCase):

    def setUp(self):
        s1.q_list = []

    def tearDown(self):
        if hasattr(s1, 'q_list'):
            del s1.q_list

    def test_answer_type(self):
        next_url = s1.parseJson(SAMPLE_JSON_ANSWER)
        self.assertEqual(len(s1.q_list), 1)
        self.assertEqual(s1.q_list[0][0], '问题_来自回答')
        self.assertEqual(s1.q_list[0][1], 12345)
        self.assertIsNotNone(next_url)

    def test_question_type(self):
        s1.parseJson(SAMPLE_JSON_QUESTION)
        self.assertEqual(len(s1.q_list), 1)
        self.assertEqual(s1.q_list[0][0], '问题')
        self.assertEqual(s1.q_list[0][1], 67890)

    def test_article_type(self):
        s1.parseJson(SAMPLE_JSON_ARTICLE)
        self.assertEqual(len(s1.q_list), 1)
        self.assertEqual(s1.q_list[0][0], '专栏')
        self.assertEqual(s1.q_list[0][3], 'https://zhuanlan.zhihu.com/p/99999')

    def test_empty_data_returns_none(self):
        result = s1.parseJson(SAMPLE_JSON_EMPTY)
        self.assertEqual(len(s1.q_list), 0)
        self.assertIsNone(result)

    def test_url_construction_for_question(self):
        s1.parseJson(SAMPLE_JSON_ANSWER)
        self.assertEqual(s1.q_list[0][3], 'https://www.zhihu.com/question/12345')

    def test_date_formatting(self):
        s1.parseJson(SAMPLE_JSON_ANSWER)
        date_str = s1.q_list[0][4]
        self.assertRegex(date_str, r'\d{4}-\d{2}-\d{2}')

    def test_multiple_items(self):
        multi = json.dumps({
            "data": [
                {"target": {"type": "question", "id": 1, "title": "Q1", "created": 1700000000}},
                {"target": {"type": "question", "id": 2, "title": "Q2", "created": 1700100000}},
            ],
            "paging": {"next": None}
        })
        s1.parseJson(multi)
        self.assertEqual(len(s1.q_list), 2)


class TestSaveData(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_csv(self):
        filepath = os.path.join(self.tmpdir, 'test.csv')
        data = [['问题', 1, 'Title', 'http://url', '2024-01-01']]
        s1.save_data(data, filepath)
        self.assertTrue(os.path.exists(filepath))

    def test_deduplicates_by_id(self):
        import pandas as pd
        filepath = os.path.join(self.tmpdir, 'test.csv')
        data = [
            ['问题', 1, 'Title A', 'http://a', '2024-01-01'],
            ['问题', 1, 'Title B', 'http://b', '2024-01-02'],
        ]
        s1.save_data(data, filepath)
        df = pd.read_csv(filepath)
        self.assertEqual(len(df), 1)

    def test_merges_existing_file(self):
        import pandas as pd
        filepath = os.path.join(self.tmpdir, 'test.csv')
        data1 = [['问题', 1, 'Title1', 'http://1', '2024-01-01']]
        s1.save_data(data1, filepath)
        data2 = [['问题', 2, 'Title2', 'http://2', '2024-01-02']]
        s1.save_data(data2, filepath)
        df = pd.read_csv(filepath)
        self.assertEqual(len(df), 2)

    def test_sorts_by_date(self):
        import pandas as pd
        filepath = os.path.join(self.tmpdir, 'test.csv')
        data = [
            ['问题', 2, 'Later', 'http://2', '2024-06-01'],
            ['问题', 1, 'Earlier', 'http://1', '2024-01-01'],
        ]
        s1.save_data(data, filepath)
        df = pd.read_csv(filepath)
        self.assertEqual(df.iloc[0]['id'], 1)


class TestCrawl(unittest.TestCase):

    def setUp(self):
        s1.q_list = []

    def tearDown(self):
        if hasattr(s1, 'q_list'):
            del s1.q_list

    @patch('scraping1_questions_by_topicID.get_url_text')
    def test_crawl_1_populates_q_list(self, mock_get):
        mock_get.side_effect = [
            SAMPLE_JSON_ANSWER, SAMPLE_JSON_EMPTY,
            SAMPLE_JSON_QUESTION, SAMPLE_JSON_EMPTY,
        ]
        s1.crawl_1('12345')
        self.assertGreaterEqual(len(s1.q_list), 2)

    @patch('scraping1_questions_by_topicID.get_url_text')
    def test_crawl_handles_error(self, mock_get):
        mock_get.return_value = None
        s1.crawl_1('12345')
        self.assertEqual(len(s1.q_list), 0)


if __name__ == '__main__':
    unittest.main()
