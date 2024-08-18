#!/usr/bin/env python3

#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import hashlib
import json
import os
import re
import random
import requests
import toml
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
from pathlib import Path
import openai_response_format
from typing import List
from utils import setup_logger. preprocess_llm_json_output


OUTPUT_FILENAME_TEMPLATE = "postgres{version}_questions.toml"

POSTGRES_CHANGELOG_QUESTION_TEMPLATE = """
PostgresSQL{version}の変更点（{title}）:
{changelogs}

上記に列挙されたPostgreSQL{version}の変更点のリストを参考に、PostgreSQL{version}に関する問題と回答のペアを{num}個作成してください。
出力する際は以下のルールを厳守してください。

 - 問題と回答文は日本語で出力すること
 - 上記で列挙しているPostgreSQL{version}の変更点の情報のみを使用して問題文を作成すること、また問題文を作成するために使用した変更点（changelogs）の情報も併せて出力すること
 - 問題文は[1],[2],[3],[4]の4択で回答可能な文章として、以下で示す問題例(OSS-DB Exam Silver/Goldの例題)と同様の形式で出力すること

問題例1:
コマンド「pg_dump -Fc db1 -f db.dump」にて実行したバックアップについて、正しいものは次のうちどれか？
[1] バックアップはカスタム形式と呼ばれるバイナリ形式で出力される
[2] バックアップは db.dump に出力されるが、合わせて標準出力にも出力される
[3] バックアップは psql コマンドでリストアする
[4] pg_dumpall はデータの一貫性が保証されるが、pg_dump はデータの一貫性が保証されない

問題例2:
pg_stat_statementsの説明として正しいものは次のうちどれか？
[1] SQL文の実行に指定した時間以上かかった場合、それぞれのSQL文の実行に要した時間を記録する
[2] ロック待ちとなっているトランザクションや対象のテーブルを確認する
[3] 実行された全てのSQL文の実行時の統計情報を記録する
[4] 現在のデータベースの各テーブルごとに1行の形で、テーブルへのアクセス統計情報を表示する

 - 回答は上記の問題例の回答候補[1],[2],[3],[4]のいずれかの番号を半角数字1文字として出力すること
 - 問題文は、上記の問題例と同等の中級者から上級者を想定した(OSS-DB Exam Silver/Gold相当の)レベルで生成すること、あまりに簡単な問題は出力しないこと
 - 問題文は「PostgreSQL16の新機能について、次のうち正しいのはどれですか？」の様に、単純に正しい変更点を選択させる質問はしないこと
 - 以下の形式に従うJSONデータのみ出力して関係のない文字列を出力しないこと、また問題文の文字列内に含まれる改行は"\\n"と置換すること

JSONフォーマット:
[
  {{
    "question": "コマンド「pg_dump -Fc db1 -f db.dump」にて実行したバックアップについて、正しいものは次のうちどれか？\\n[1] バックアップはカスタム形式と呼ばれるバイナリ形式で出力される\\n[2] バックアップは db.dump に出力されるが、合わせて標準出力にも出力される\\n[3] バックアップは psql コマンドでリストアする\\n[4] pg_dumpall はデータの一貫性が保証されるが、pg_dump はデータの一貫性が保証されない",
    "answer": 1,
    "changelog": "pg_dumpにカスタム形式と呼ばれるバイナリ形式で出力するためのオプションを追加しました"
  }},
  {{
    "question": "pg_stat_statementsの説明として正しいものは次のうちどれか？\\n[1] SQL文の実行に指定した時間以上かかった場合、それぞれのSQL文の実行に要した時間を記録する\\n[2] ロック待ちとなっているトランザクションや対象のテーブルを確認する\\n[3] 実行された全てのSQL文の実行時の統計情報を記録する\\n[4] 現在のデータベースの各テーブルごとに1行の形で、テーブルへのアクセス統計情報を表示する",
    "answer": 3,
    "changelog": "実行された全てのSQL文の実行時の統計情報を記録するためのpg_stat_statementsをcontribに追加しました"
  }},
  ...
]
"""

POSTGRES_QUESTION_TEMPLATE = """
PostgreSQLのSQL構文、性能チューニング、バックアップとリストア、運用監視など網羅的なトピックに関する問題と回答のペアを{num}個作成してください。
出力する際は以下のルールを厳守してください。

 - 問題と回答文は日本語で出力すること
 - 問題文は[1],[2],[3],[4]の4択で回答可能な文章として、以下で示す問題例(OSS-DB Exam Silver/Goldの例題)と同様の形式で出力すること

問題例1:
コマンド「pg_dump -Fc db1 -f db.dump」にて実行したバックアップについて、正しいものは次のうちどれか？
[1] バックアップはカスタム形式と呼ばれるバイナリ形式で出力される
[2] バックアップは db.dump に出力されるが、合わせて標準出力にも出力される
[3] バックアップは psql コマンドでリストアする
[4] pg_dumpall はデータの一貫性が保証されるが、pg_dump はデータの一貫性が保証されない

問題例2:
pg_stat_statementsの説明として正しいものは次のうちどれか？
[1] SQL文の実行に指定した時間以上かかった場合、それぞれのSQL文の実行に要した時間を記録する
[2] ロック待ちとなっているトランザクションや対象のテーブルを確認する
[3] 実行された全てのSQL文の実行時の統計情報を記録する
[4] 現在のデータベースの各テーブルごとに1行の形で、テーブルへのアクセス統計情報を表示する

 - 回答は上記の問題例の回答候補[1],[2],[3],[4]のいずれかの番号を半角数字1文字として出力すること
 - 問題文は、上記の問題例と同等の中級者から上級者を想定した(OSS-DB Exam Silver/Gold相当の)レベルで生成すること、あまりに簡単な問題は出力しないこと
 - 以下の形式に従うJSONデータのみ出力して関係のない文字列を出力しないこと、また問題文の文字列内に含まれる改行は"\\n"と置換すること

JSONフォーマット:
[
  {{
    "question": "コマンド「pg_dump -Fc db1 -f db.dump」にて実行したバックアップについて、正しいものは次のうちどれか？\\n[1] バックアップはカスタム形式と呼ばれるバイナリ形式で出力される\\n[2] バックアップは db.dump に出力されるが、合わせて標準出力にも出力される\\n[3] バックアップは psql コマンドでリストアする\\n[4] pg_dumpall はデータの一貫性が保証されるが、pg_dump はデータの一貫性が保証されない",
    "answer": 1
  }},
  {{
    "question": "pg_stat_statementsの説明として正しいものは次のうちどれか？\\n[1] SQL文の実行に指定した時間以上かかった場合、それぞれのSQL文の実行に要した時間を記録する\\n[2] ロック待ちとなっているトランザクションや対象のテーブルを確認する\\n[3] 実行された全てのSQL文の実行時の統計情報を記録する\\n[4] 現在のデータベースの各テーブルごとに1行の形で、テーブルへのアクセス統計情報を表示する",
    "answer": 3
  }},
  ...
]
"""


_logger = setup_logger()


def parse_postgresql_release_note(version=16):
    assert version in [14, 15, 16], "`version` must be 14, 15, or 16"

    POSTGRESQL_RELEASE_NOTE_URL = "https://www.postgresql.jp/document/{version}/html/release-{version}.html"
    url = POSTGRESQL_RELEASE_NOTE_URL.format(version=version)

    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(response.text, 'html.parser')

    # List of extracted tags
    sections = soup.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'li'])

    data = {}
    current_section = None

    # Pattern to remove contributor names
    contributor_pattern = re.compile(r'\(.*?\)')

    # List of skipped sections
    skip_keywords = ["リリース", "謝辞"]

    def _preprocess_text(text):
        cleaned_text = contributor_pattern.sub('', text.strip()).strip()
        cleaned_text = cleaned_text.replace('\n', '')
        return cleaned_text

    for tag in sections:
        if tag.name in ['h2', 'h3', 'h4']:
            section_name = tag.get_text().strip()

            if any(keyword in section_name for keyword in skip_keywords):
                current_section = None
                continue

            current_section = section_name
            data[current_section] = []

        elif tag.name == 'p' and current_section:
            data[current_section].append(_preprocess_text(tag.get_text()))

        elif tag.name in ['ul', 'ol'] and current_section:
            for li in tag.find_all('li'):
                data[current_section].append(_preprocess_text(li.get_text()))

    return data


def random_window_slice(lst, window_size):
    start_index = random.randint(0, max(0, len(lst) - window_size))
    return lst[start_index:start_index + window_size]


def generate_questions(version, num, openai_modelname, changelog_max_num=30, cache_enabled=True):
    CACHE_FILENAME_TEMPLATE = ".openai_response_cache_{}.json"

    client = OpenAI()

    def _gen_questions(key, value):
        cache_filename = None
        if cache_enabled:
            s = "{}{}{}".format(version, openai_modelname, key)
            hashcode = hashlib.sha256(s.encode()).hexdigest()
            cache_filename = CACHE_FILENAME_TEMPLATE.format(hashcode[0:8])

        openai_res = None

        if cache_enabled and os.path.exists(cache_filename):
            openai_res = Path(cache_filename).read_text()
            _logger.info(f"Cached JSON file '{cache_filename}' loaded")
        else:
            completion = client.chat.completions.create(
                model=openai_modelname, messages=[{'role': 'user', 'content': value}])

            # A openai_resurned text from OpenAI APIs ocassionally could have a meta symbol
            # (e.g., the new line), so it is escaped just in case here.
            openai_res = completion.choices[0].message.content

            # To avoid duplicate OpenAI API calls, the response is written to a file as cache
            if cache_enabled:
                with open(cache_filename, "w") as f:
                    f.write(openai_res)

            _logger.info("生成日時: {timestamp}".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            _logger.info("生成モデル: {modelname}".format(modelname=completion.model))
            _logger.info("プロンプト:\n\n{prompt}".format(prompt=value))

        try:
            return json.loads(preprocess_llm_json_output(openai_res))
        except Exception as e:
            raise ValueError(f"Can't parse the OpenAPI response as JSON:\n{openai_res}\n{e}")

    if version is not None:
        release_note = parse_postgresql_release_note(version)
        num_per_generated = int(num / len(release_note)) + 1
        data = []
        for section, contents in release_note.items():
            contents = random_window_slice(contents, changelog_max_num)
            changelogs = "\n".join(map(lambda s: f" - {s}", contents))
            question = POSTGRES_CHANGELOG_QUESTION_TEMPLATE.format(
                version=version, num=num_per_generated, title=section, changelogs=changelogs)
            data.extend(_gen_questions(section, question))
    else:
        question = POSTGRES_QUESTION_TEMPLATE.format(num=num)
        data = _gen_questions('general', question)

    questions = openai_response_format.question_validate(data)
    random.shuffle(questions)

    return questions


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--model', type=str, default='gpt-4') # 'gpt-4' or 'gpt-3.5-turbo'
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--version', type=int)
    parser.add_argument('--num', type=int, default=30)
    parser.add_argument('--cache', action='store_true')
    args = parser.parse_args()

    questions = generate_questions(args.version, args.num, args.model, cache_enabled=args.cache)

    filename = OUTPUT_FILENAME_TEMPLATE.format(version=args.version if args.version is not None else '')
    filepath = os.path.join(args.output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        toml.dump({'questions': questions}, f)

    print(f"Written to {filepath}")


if __name__ == "__main__":
    main()
