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

import json
import os
import toml
from datetime import datetime
from utils import import_function, preprocess_llm_json_output


OUTPUT_FILENAME_TEMPLATE = "prompts_generated_{ts}.toml"

POSTGRES_PROMPT_TEMPLATE = """
PostgreSQLのSQL構文、性能チューニング、バックアップとリストア、運用監視、また内部のソースコードなど様々な領域に
関する質疑応答を高精度で行うために、LLMに与える最適なプロンプトの候補を{num}個提案してください。
プロンプトの例を以下に示す。

プロンプト例:
あなたはPostgreSQLエキスパートです。
PostgreSQLに関するサポート業務に10年以上従事していて、顧客から質問された内容にほぼ100%の確率で正確な回答を提供してきています。
以降では、その経験を踏まえて、入力された質問に答えてください。


提案候補を出力する際は以下のルールを厳守してください。

 - プロンプトの提案候補は日本語で出力すること
 - 提案するプロンプトは上記の具体例と構造、語彙、文章量の観点で似ている出力はせずに、多様性を重視して出力すること
 - 以下の形式に従うJSONデータのみ出力して関係のない文字列を出力しないこと、また問題文の文字列内に含まれる改行は"\\n"と置換すること

JSONフォーマット:
[
    "あなたはPostgreSQLエキスパートです。\\nPostgreSQLに関するサポート業務に10年以上従事していて、顧客から質問された内容にほぼ100%の確率で正確な回答を提供してきています。\\n以降では、その経験を踏まえて、入力された質問に答えてください。",
    "...",
]
"""


def generate_prompts(func, num):
    prompt = POSTGRES_PROMPT_TEMPLATE.format(num=num)
    res, _ = func('', prompt)

    try:
        # TODO: Validate `generated` using pydantic
        generated = json.loads(preprocess_llm_json_output(res))
    except Exception as e:
        raise ValueError(f"Can't parse the OpenAPI response as JSON:\n{res}\n{e}")

    return prompt, generated


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--module', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--num', type=int, default=3)
    args = parser.parse_args()

    # Load an evaluation function from a given Python file
    func = import_function(args.module)

    prompt, generated = generate_prompts(func, args.num)

    filename = OUTPUT_FILENAME_TEMPLATE.format(ts=datetime.now().strftime("%Y%m%d%H%M%S"))
    filepath = os.path.join(args.output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        toml.dump({'llm': func.__name__, 'prompt': prompt, 'generated': generated}, f)

    print(f"Written to {filepath}")


if __name__ == "__main__":
    main()
