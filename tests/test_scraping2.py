import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

import pandas as pd
import scraping2_question_meta_by_questionID as s2


SAMPLE_QUESTION_HTML = '''
<html>
<head>
  <meta itemprop="name" content="What is Python?">
  <meta itemprop="answerCount" content="42">
  <meta itemprop="keywords" content="Python,Programming">
  <meta itemprop="dateCreated" content="2024-01-15T10:30:00.000Z">
</head>
<body>
  <strong class="NumberBoard-itemValue" title="1500">1,500</strong>
  <strong class="NumberBoard-itemValue" title="50000">50,000</strong>
</body>
</html>
'''


class TestGetQuestionList(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_filters_out_articles(self):
        filepath = os.path.join(self.tmpdir, 'q.csv')
        df = pd.DataFrame({
            'type': ['问题', '专栏', '问题'],
            'id': [1, 2, 3],
            'title': ['Q1', 'A1', 'Q2'],
            'url': ['u1', 'u2', 'u3'],
            'date': ['2024-11-01', '2024-11-01', '2024-11-01'],
        })
        df.to_csv(filepath, index=False)
        result = s2.get_question_list(filepath)
        types = [r[0] for r in result]
        self.assertNotIn('专栏', types)

    def test_filters_by_date(self):
        filepath = os.path.join(self.tmpdir, 'q.csv')
        df = pd.DataFrame({
            'type': ['问题', '问题'],
            'id': [1, 2],
            'title': ['Old', 'New'],
            'url': ['u1', 'u2'],
            'date': ['2024-01-01', '2024-11-01'],
        })
        df.to_csv(filepath, index=False)
        result = s2.get_question_list(filepath)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], 'New')

    def test_returns_list_of_lists(self):
        filepath = os.path.join(self.tmpdir, 'q.csv')
        df = pd.DataFrame({
            'type': ['问题'],
            'id': [1],
            'title': ['T'],
            'url': ['u'],
            'date': ['2024-11-01'],
        })
        df.to_csv(filepath, index=False)
        result = s2.get_question_list(filepath)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], list)
        self.assertEqual(len(result[0]), 5)


class TestGetQuestionData(unittest.TestCase):

    def setUp(self):
        s2.q_id = 12345

    def tearDown(self):
        if hasattr(s2, 'q_id'):
            del s2.q_id

    def test_parses_valid_html(self):
        result = s2.get_question_data(SAMPLE_QUESTION_HTML)
        self.assertEqual(result[0], 12345)
        self.assertEqual(result[1], 'What is Python?')
        self.assertEqual(result[2], '1500')
        self.assertEqual(result[3], '50000')
        self.assertEqual(result[4], '42')
        self.assertIn('Python', result[5])
        self.assertEqual(result[6], '2024-01-15')

    def test_truncates_date_to_10_chars(self):
        result = s2.get_question_data(SAMPLE_QUESTION_HTML)
        self.assertEqual(len(result[6]), 10)

    def test_malformed_html_returns_unknown_error(self):
        result = s2.get_question_data('<html></html>')
        self.assertEqual(result[1], 'UnknownError')

    def test_none_input_returns_unknown_error(self):
        result = s2.get_question_data(None)
        self.assertEqual(result[1], 'UnknownError')


class TestSaveData(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_new_file(self):
        filepath = os.path.join(self.tmpdir, 'meta.csv')
        data = [[1, 'Q1', 100, 5000, 10, 'tag', '2024-01-01']]
        s2.save_data(data, filepath)
        self.assertTrue(os.path.exists(filepath))
        df = pd.read_csv(filepath)
        self.assertEqual(len(df), 1)

    def test_merge_and_dedup(self):
        filepath = os.path.join(self.tmpdir, 'meta.csv')
        data1 = [[1, 'Q1', 100, 5000, 10, 'tag', '2024-01-01']]
        s2.save_data(data1, filepath)
        data2 = [[1, 'Q1_updated', 200, 6000, 20, 'tag2', '2024-01-01'],
                  [2, 'Q2', 50, 1000, 5, 'tag3', '2024-02-01']]
        s2.save_data(data2, filepath)
        df = pd.read_csv(filepath)
        self.assertEqual(len(df), 2)

    def test_removes_unknown_error_rows(self):
        filepath = os.path.join(self.tmpdir, 'meta.csv')
        data1 = [[1, 'UnknownError', 'UnknownError', 'UnknownError',
                   'UnknownError', 'UnknownError', 'UnknownError']]
        s2.save_data(data1, filepath)
        data2 = [[1, 'Good Q', 100, 5000, 10, 'tag', '2024-01-01']]
        s2.save_data(data2, filepath)
        df = pd.read_csv(filepath)
        self.assertNotIn('UnknownError', df['q_content'].values)


if __name__ == '__main__':
    unittest.main()
