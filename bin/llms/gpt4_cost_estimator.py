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

import random
import tiktoken


# Cost of the 'gpt-4' model
COST_PER_INPUT_TOKEN = 0.03 / 1000
COST_PER_OUTPUT_TOKEN = 0.06 / 1000


_tokenizer = None


def gpt4_cost_estimator(system_prompt, user_prompt) -> str:
    global _tokenizer

    if _tokenizer is None:
        _tokenizer = tiktoken.encoding_for_model("gpt-4")

    input_tokens = _tokenizer.encode(system_prompt + user_prompt)

    # Assume the number of output tokens is the same with as one of input tokens
    cost = len(input_tokens) * (COST_PER_INPUT_TOKEN + COST_PER_OUTPUT_TOKEN)

    return str(random.randint(0, 4)), cost

