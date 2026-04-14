import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

import pandas as pd
import scraping4_comments_by_answerID as s4


SAMPLE_ROOT_COMMENT = {
    "id": 111,
    "content": "<b>Great answer!</b>",
    "created_time": 1700000000,
    "vote_count": 5,
    "child_comment_count": 2,
    "author": {
        "member": {
            "name": "Commenter1",
            "url_token": "commenter-1",
            "gender": 1,
            "headline": "Test"
        }
    }
}

SAMPLE_CHILD_COMMENT = {
    "id": 222,
    "reply_comment_id": 111,
    "reply_root_comment_id": 111,
    "content": "I agree",
    "created_time": 1700100000,
    "like_count": 3,
    "child_comment_count": 0,
    "author": {
        "name": "Replier1",
        "url_token": "replier-1",
        "gender": 2,
        "headline": "Reply test"
    }
}


class TestParseRootComment(unittest.TestCase):

    def test_returns_13_fields(self):
        result = s4.parse_root_comment(SAMPLE_ROOT_COMMENT, "A001")
        self.assertEqual(len(result), 13)

    def test_comment_type(self):
        result = s4.parse_root_comment(SAMPLE_ROOT_COMMENT, "A001")
        self.assertEqual(result[1], "根评论")

    def test_reply_ids_empty(self):
        result = s4.parse_root_comment(SAMPLE_ROOT_COMMENT, "A001")
        self.assertEqual(result[2], "")
        self.assertEqual(result[3], "")

    def test_strips_html(self):
        result = s4.parse_root_comment(SAMPLE_ROOT_COMMENT, "A001")
        self.assertNotIn("<b>", result[5])
        self.assertIn("Great answer!", result[5])

    def test_uses_vote_count(self):
        result = s4.parse_root_comment(SAMPLE_ROOT_COMMENT, "A001")
        self.assertEqual(result[7], 5)


class TestParseChildComment(unittest.TestCase):

    def test_returns_13_fields(self):
        result = s4.parse_child_comment(SAMPLE_CHILD_COMMENT, "A001")
        self.assertEqual(len(result), 13)

    def test_comment_type(self):
        result = s4.parse_child_comment(SAMPLE_CHILD_COMMENT, "A001")
        self.assertEqual(result[1], "子评论")

    def test_reply_ids_populated(self):
        result = s4.parse_child_comment(SAMPLE_CHILD_COMMENT, "A001")
        self.assertEqual(result[2], 111)
        self.assertEqual(result[3], 111)

    def test_uses_like_count(self):
        result = s4.parse_child_comment(SAMPLE_CHILD_COMMENT, "A001")
        self.assertEqual(result[7], 3)

    def test_author_flat_structure(self):
        result = s4.parse_child_comment(SAMPLE_CHILD_COMMENT, "A001")
        self.assertEqual(result[9], "Replier1")


class TestGetAnswerId(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('data/answers_of_question', exist_ok=True)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def test_reads_answer_ids(self):
        df = pd.DataFrame({'a_id': [100, 200, 300], 'other': ['a', 'b', 'c']})
        df.to_csv('data/answers_of_question/question_123.csv', index=False)
        result = s4.get_answer_id("123")
        self.assertEqual(result, [100, 200, 300])

    def test_missing_file_returns_empty(self):
        result = s4.get_answer_id("999")
        self.assertEqual(result, [])


class TestGetRootComments(unittest.TestCase):

    @patch('scraping4_comments_by_answerID.get_url_text')
    def test_pagination(self, mock_get):
        page1 = json.dumps({
            "data": [SAMPLE_ROOT_COMMENT],
            "paging": {"next": "http://page2"}
        })
        page2 = json.dumps({
            "data": [],
            "paging": {"next": None}
        })
        mock_get.side_effect = [page1, page2]
        df = s4.get_root_comments("A001")
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 1)
        self.assertIn("comment_id", df.columns)

    @patch('scraping4_comments_by_answerID.get_url_text')
    def test_failure_returns_none(self, mock_get):
        mock_get.return_value = None
        result = s4.get_root_comments("A001")
        self.assertIsNone(result)


class TestGetChildComments(unittest.TestCase):

    @patch('scraping4_comments_by_answerID.get_url_text')
    def test_pagination(self, mock_get):
        page1 = json.dumps({
            "data": [SAMPLE_CHILD_COMMENT],
            "paging": {"next": "http://page2"}
        })
        page2 = json.dumps({
            "data": [],
            "paging": {"next": None}
        })
        mock_get.side_effect = [page1, page2]
        df = s4.get_child_comments(["A001", 111])
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 1)

    @patch('scraping4_comments_by_answerID.get_url_text')
    def test_failure_returns_none(self, mock_get):
        mock_get.return_value = None
        result = s4.get_child_comments(["A001", 111])
        self.assertIsNone(result)


class TestSaveData(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('data/comments_of_question', exist_ok=True)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def test_creates_file(self):
        df = pd.DataFrame([{
            'answer_id': 'A1', 'comment_type': '根评论',
            'reply_comment_id': '', 'reply_root_comment_id': '',
            'comment_id': 100, 'comment_content': 'test',
            'comment_date': '2024-01-01', 'comment_upvote': 5,
            'child_comment_count': 0, 'author_name': 'User',
            'author_url_token': 'user', 'author_gender': 1,
            'author_headline': 'h'
        }])
        s4.save_data(df, "123")
        self.assertTrue(os.path.exists('data/comments_of_question/question_123.csv'))

    def test_deduplicates_by_comment_id(self):
        row = {
            'answer_id': 'A1', 'comment_type': '根评论',
            'reply_comment_id': '', 'reply_root_comment_id': '',
            'comment_id': 100, 'comment_content': 'test',
            'comment_date': '2024-01-01', 'comment_upvote': 5,
            'child_comment_count': 0, 'author_name': 'User',
            'author_url_token': 'user', 'author_gender': 1,
            'author_headline': 'h'
        }
        df1 = pd.DataFrame([row])
        s4.save_data(df1, "123")
        df2 = pd.DataFrame([row])
        s4.save_data(df2, "123")
        result = pd.read_csv('data/comments_of_question/question_123.csv')
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
