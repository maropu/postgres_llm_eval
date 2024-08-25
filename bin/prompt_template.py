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


POSTGRES_QA_PROMPT_TEMPLATE = """
{prompt}

下記の問題例の形式で示されるPostgreSQL{version}に関する質問に対して、以下のルールを厳守して回答してください

 - 質問された内容が回答可能である場合には、半角数字で1, 2, 3, 4のいずれかで出力すること（下記の問題例の場合には1と出力すること）
 - 質問された内容が回答できない場合には、半角数字の0を出力すること
 - 半角数字の0, 1, 2, 3, 4以外の文字は出力しないこと

問題例:
コマンド「pg_dump -Fc db1 -f db.dump」にて実行したバックアップについて、正しいものは次のうちどれか？
[1] バックアップはカスタム形式と呼ばれるバイナリ形式で出力される
[2] バックアップは db.dump に出力されるが、合わせて標準出力にも出力される
[3] バックアップは psql コマンドでリストアする
[4] pg_dumpall はデータの一貫性が保証されるが、pg_dump はデータの一貫性が保証されない

PostgreSQL{version} に関する質問:
"""
