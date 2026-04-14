import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

import pandas as pd
import scraping3_answer_meta_by_questionID as s3


SAMPLE_ANSWER_JSON = json.dumps({
    "data": [{
        "target": {
            "content": "<p>This is an <b>answer</b></p>",
            "created_time": 1700000000,
            "voteup_count": 150,
            "comment_count": 12,
            "id": 98765,
            "author": {
                "name": "TestUser",
                "gender": 1,
                "url_token": "test-user",
                "follower_count": 500,
                "headline": "Test headline"
            }
        }
    }],
    "paging": {"next": "https://zhihu.com/api/next", "is_end": False}
})

SAMPLE_LAST_PAGE_JSON = json.dumps({
    "data": [{
        "target": {
            "content": "Last answer",
            "created_time": 1700100000,
            "voteup_count": 5,
            "comment_count": 0,
            "id": 11111,
            "author": {
                "name": "User2",
                "gender": 0,
                "url_token": "user2",
                "follower_count": 10,
                "headline": ""
            }
        }
    }],
    "paging": {"next": None, "is_end": True}
})


class TestGetQList(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_filters_by_answer_count(self):
        filepath = os.path.join(self.tmpdir, 'meta.csv')
        df = pd.DataFrame({
            'q_id': [1, 2, 3],
            'q_content': ['Q1', 'Q2', 'Q3'],
            'followerCount': [100, 200, 300],
            'viewCount': [1000, 2000, 3000],
            'answerCount': [3, 10, 20],
            'topicTag': ['t', 't', 't'],
            'created_date': ['2024-01-01', '2024-02-01', '2024-03-01'],
        })
        df.to_csv(filepath, index=False)
        result = s3.get_q_list(filepath)
        self.assertNotIn(1, result)
        self.assertIn(2, result)
        self.assertIn(3, result)

    def test_returns_reversed_dict(self):
        filepath = os.path.join(self.tmpdir, 'meta.csv')
        df = pd.DataFrame({
            'q_id': [10, 20, 30],
            'q_content': ['A', 'B', 'C'],
            'followerCount': [1, 1, 1],
            'viewCount': [1, 1, 1],
            'answerCount': [10, 10, 10],
            'topicTag': ['t', 't', 't'],
            'created_date': ['2024-01-01', '2024-02-01', '2024-03-01'],
        })
        df.to_csv(filepath, index=False)
        result = s3.get_q_list(filepath)
        keys = list(result.keys())
        self.assertEqual(keys[0], 30)


class TestParseData(unittest.TestCase):

    @patch('scraping3_answer_meta_by_questionID.get_url_text')
    def test_extracts_answer_fields(self, mock_get):
        mock_get.return_value = SAMPLE_ANSWER_JSON
        data, next_url, is_end = s3.parse_data('http://test', 999)
        self.assertEqual(len(data), 1)
        self.assertEqual(len(data[0]), 11)
        self.assertEqual(data[0][0], 999)
        self.assertEqual(data[0][5], 98765)
        self.assertFalse(is_end)

    @patch('scraping3_answer_meta_by_questionID.get_url_text')
    def test_strips_html_tags(self, mock_get):
        mock_get.return_value = SAMPLE_ANSWER_JSON
        data, _, _ = s3.parse_data('http://test', 999)
        self.assertNotIn('<p>', data[0][1])
        self.assertNotIn('<b>', data[0][1])
        self.assertIn('answer', data[0][1])

    @patch('scraping3_answer_meta_by_questionID.get_url_text')
    def test_date_formatting(self, mock_get):
        mock_get.return_value = SAMPLE_ANSWER_JSON
        data, _, _ = s3.parse_data('http://test', 999)
        self.assertRegex(data[0][2], r'\d{4}-\d{2}-\d{2}')

    @patch('scraping3_answer_meta_by_questionID.get_url_text')
    def test_is_end_flag(self, mock_get):
        mock_get.return_value = SAMPLE_LAST_PAGE_JSON
        _, _, is_end = s3.parse_data('http://test', 999)
        self.assertTrue(is_end)


class TestSaveData(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('data/answers_of_question', exist_ok=True)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def test_creates_per_question_file(self):
        data = [[999, 'content', '2024-01-01', 10, 2, 100,
                 'Author', 1, 'token', 50, 'headline']]
        s3.save_data(data, 999)
        self.assertTrue(os.path.exists('data/answers_of_question/question_999.csv'))

    def test_merges_and_deduplicates(self):
        data1 = [[999, 'content1', '2024-01-01', 10, 2, 100,
                  'A', 1, 't', 50, 'h']]
        s3.save_data(data1, 999)
        data2 = [[999, 'content2', '2024-01-02', 20, 3, 100,
                  'A', 1, 't', 50, 'h'],
                 [999, 'content3', '2024-01-03', 5, 1, 200,
                  'B', 0, 't2', 10, 'h2']]
        s3.save_data(data2, 999)
        df = pd.read_csv('data/answers_of_question/question_999.csv')
        self.assertEqual(len(df), 2)


if __name__ == '__main__':
    unittest.main()
