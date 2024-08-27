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

import tiktoken
from openai import OpenAI


# Cost of the 'gpt-4' model
COST_PER_INPUT_TOKEN = 0.03 / 1000
COST_PER_OUTPUT_TOKEN = 0.06 / 1000


_client = None
_tokenizer = None


def gpt4(system_prompt, user_prompt, params={}) -> str:
    global _client, _tokenizer

    if _client is None:
        _client = OpenAI()

    if _tokenizer is None:
        _tokenizer = tiktoken.encoding_for_model("gpt-4")

    completion = _client.chat.completions.create(
        model='gpt-4', # or 'gpt-4-32k'
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
    )

    ret = completion.choices[0].message.content

    # Compute total cost using the number of input/output tokens
    input_tokens = _tokenizer.encode(system_prompt + user_prompt)
    output_tokens = _tokenizer.encode(ret)
    cost = len(input_tokens) * COST_PER_INPUT_TOKEN + len(output_tokens) * COST_PER_OUTPUT_TOKEN

    return ret, cost

