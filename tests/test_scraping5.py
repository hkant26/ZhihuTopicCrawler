import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

import pandas as pd
import scraping5_author_meta_by_authorID as s5


SAMPLE_USER_HTML = '''
<html>
<script id="js-initialData">
{
  "initialState": {
    "entities": {
      "users": {
        "test-user": {
          "urlToken": "test-user",
          "name": "TestUser",
          "gender": 1,
          "ipInfo": "IP 属地北京",
          "voteupCount": 1000,
          "thankedCount": 200,
          "followerCount": 500,
          "favoritedCount": 300,
          "answerCount": 50,
          "articlesCount": 10,
          "vipInfo": {"isVip": 1},
          "kvipInfo": {"isVip": 0},
          "badgeV2": {
            "mergedBadges": [
              {"type": "identity"},
              {"type": "best"}
            ]
          }
        }
      }
    }
  }
}
</script>
</html>
'''

SAMPLE_USER_NO_BADGES_HTML = '''
<html>
<script id="js-initialData">
{
  "initialState": {
    "entities": {
      "users": {
        "no-badge": {
          "urlToken": "no-badge",
          "name": "NoBadge",
          "gender": 0,
          "ipInfo": "IP 属地上海",
          "voteupCount": 10,
          "thankedCount": 5,
          "followerCount": 20,
          "favoritedCount": 3,
          "answerCount": 2,
          "articlesCount": 0,
          "vipInfo": {"isVip": 0},
          "kvipInfo": {"isVip": 0},
          "badgeV2": {"mergedBadges": []}
        }
      }
    }
  }
}
</script>
</html>
'''


class TestGetTokens(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_new_store_file_created(self):
        src = os.path.join(self.tmpdir, 'tokens.csv')
        store = os.path.join(self.tmpdir, 'store.csv')
        pd.DataFrame({'token': ['a', 'b'], 'name': ['A', 'B']}).to_csv(
            src, index=False, header=False
        )
        result = s5.get_tokens(src, store)
        self.assertTrue(os.path.exists(store))
        self.assertEqual(len(result), 2)

    def test_filters_existing_tokens(self):
        src = os.path.join(self.tmpdir, 'tokens.csv')
        store = os.path.join(self.tmpdir, 'store.csv')
        pd.DataFrame({'token': ['a', 'b', 'c'], 'name': ['A', 'B', 'C']}).to_csv(
            src, index=False, header=False
        )
        pd.DataFrame({
            'user_token': ['a'],
            'name': ['A'], 'gender': [1], 'IP_address': ['BJ'],
            'voteupCount': [0], 'thankedCount': [0], 'followerCount': [0],
            'favoritedCount': [0], 'productCount': [0], 'VIPs': [0],
            'identity': [0], 'top_writer': [0]
        }).to_csv(store, index=False)
        result = s5.get_tokens(src, store)
        self.assertNotIn('a', result)
        self.assertEqual(len(result), 2)


class TestGetAuthorInfo(unittest.TestCase):

    def test_parses_valid_html(self):
        result = s5.get_author_info(SAMPLE_USER_HTML, "test-user")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 12)
        self.assertEqual(result[0], "test-user")
        self.assertEqual(result[1], "TestUser")

    def test_ip_prefix_stripped(self):
        result = s5.get_author_info(SAMPLE_USER_HTML, "test-user")
        self.assertEqual(result[3], "北京")

    def test_product_count(self):
        result = s5.get_author_info(SAMPLE_USER_HTML, "test-user")
        self.assertEqual(result[8], 60)  # 50 + 10

    def test_vip_sum(self):
        result = s5.get_author_info(SAMPLE_USER_HTML, "test-user")
        self.assertEqual(result[9], 1)  # 1 + 0

    def test_identity_badge(self):
        result = s5.get_author_info(SAMPLE_USER_HTML, "test-user")
        self.assertEqual(result[10], 1)

    def test_top_writer_badge(self):
        result = s5.get_author_info(SAMPLE_USER_HTML, "test-user")
        self.assertEqual(result[11], 1)

    def test_no_badges(self):
        result = s5.get_author_info(SAMPLE_USER_NO_BADGES_HTML, "no-badge")
        self.assertEqual(result[10], 0)
        self.assertEqual(result[11], 0)

    def test_malformed_html_returns_none(self):
        result = s5.get_author_info("<html></html>", "test-user")
        self.assertIsNone(result)

    def test_none_input_returns_none(self):
        result = s5.get_author_info(None, "test-user")
        self.assertIsNone(result)


class TestSaveData(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_append_mode(self):
        filepath = os.path.join(self.tmpdir, 'authors.csv')
        # Create initial file with header
        pd.DataFrame([], columns=[
            'user_token', 'name', 'gender', 'IP_address',
            'voteupCount', 'thankedCount', 'followerCount', 'favoritedCount',
            'productCount', 'VIPs', 'identity', 'top_writer'
        ]).to_csv(filepath, index=False)

        data1 = [['t1', 'N1', 1, 'BJ', 10, 5, 20, 3, 5, 0, 0, 0]]
        s5.save_data(data1, filepath)
        data2 = [['t2', 'N2', 0, 'SH', 20, 10, 40, 6, 10, 1, 1, 1]]
        s5.save_data(data2, filepath)

        df = pd.read_csv(filepath)
        self.assertEqual(len(df), 2)


if __name__ == '__main__':
    unittest.main()
