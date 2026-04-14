import os
import shutil
import subprocess
import tempfile
import unittest

import pandas as pd


SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'codes', 'scraping4.5_data_processing.py'
)


class TestScraping4_5(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.answer_dir = os.path.join(self.tmpdir, 'data', 'answers_of_question')
        os.makedirs(self.answer_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _make_answer_csv(self, filename, rows):
        df = pd.DataFrame(rows, columns=[
            'q_id', 'a_content', 'a_date', 'a_upvote', 'a_comment', 'a_id',
            'au_name', 'au_gender', 'au_urltoken', 'au_followerCount', 'au_headline'
        ])
        df.to_csv(os.path.join(self.answer_dir, filename), index=False)

    def _run_script(self):
        return subprocess.run(
            ['python3', os.path.abspath(SCRIPT_PATH)],
            cwd=self.tmpdir,
            capture_output=True, text=True
        )

    def test_merges_multiple_files(self):
        self._make_answer_csv('question_1.csv', [
            [1, 'ans1', '2024-01-01', 10, 2, 100, 'U1', 1, 'u1', 50, 'h1']
        ])
        self._make_answer_csv('question_2.csv', [
            [2, 'ans2', '2024-01-02', 20, 3, 200, 'U2', 0, 'u2', 30, 'h2']
        ])
        result = self._run_script()
        self.assertEqual(result.returncode, 0, result.stderr)

        merged = pd.read_csv(os.path.join(self.tmpdir, 'data', 'all_answers.csv'))
        self.assertEqual(len(merged), 2)

    def test_deduplicates_user_tokens(self):
        self._make_answer_csv('question_1.csv', [
            [1, 'a1', '2024-01-01', 10, 2, 100, 'U1', 1, 'shared_token', 50, 'h'],
            [1, 'a2', '2024-01-02', 5, 1, 101, 'U1', 1, 'shared_token', 50, 'h'],
        ])
        self._run_script()

        tokens = pd.read_csv(
            os.path.join(self.tmpdir, 'data', 'user_tokens.csv'), header=None
        )
        self.assertEqual(len(tokens), 1)

    def test_user_tokens_no_header(self):
        self._make_answer_csv('question_1.csv', [
            [1, 'a', '2024-01-01', 1, 1, 100, 'U', 1, 'tok', 10, 'h']
        ])
        self._run_script()

        token_path = os.path.join(self.tmpdir, 'data', 'user_tokens.csv')
        with open(token_path) as f:
            first_line = f.readline().strip()
        # Should NOT be a header like "au_urltoken,au_name"
        self.assertNotIn('au_urltoken', first_line)


if __name__ == '__main__':
    unittest.main()
