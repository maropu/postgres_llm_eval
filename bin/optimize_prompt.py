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
import openai_response_format
import random
import toml
import tomllib
import tqdm
from datetime import datetime
from pathlib import Path
from utils import setup_logger, import_function


REWRITE_PROMPT = """
下記の「書き換え対象のプロンプト」以降で与えられる1から4の数字で回答する4択のPostgreSQLに
関する問題を解くためのプロンプトを、「書換えルール」で示す規則に従って、
より回答精度高くなるように書き換えてください、
また以下の示す制約を必ず厳守してください

 - 出力は書き換え後のプロンプトのみを出力して、余計な文章を追加しない
 - 書き換え前後で、文字数が大きく変わるような書き換えは行わない

## 書き換えルール:
{rule}

## 書き換え対象のプロンプト:
"""

PROPOSE_RULE_PROMPT = """
1から4の数字で回答する4択のPostgreSQLに関する問題の解答精度を高めるための書換えルールを、
以下の既存の書換えルールを参考に１つ提案してください、
また提案内容は下記の制約を厳守してください

 - 新しく提案するルールは、下記に示す書換えルールと異なるものを提案してください
 - 出力は書き換え後のプロンプトのみを出力して、余計な文章を追加しない

## 既存の書換えルール
"""


def apply_rules_to_prompt(prompt, rules, func):
    # TODO: Not sure that the commutative law holds in this rewrite process
    random.shuffle(rules)

    total_cost = 0.0
    for rule in tqdm.tqdm(rules, leave=False, desc=f'[Applying {len(rules)} rules]'):
        rewrite_system_prompt = REWRITE_PROMPT.format(rule=rule)
        prompt, cost = func(rewrite_system_prompt, prompt)
        total_cost += cost if cost is not None else 0.0

    return prompt, total_cost


def rewrite_prompt(prompt, rules, func, max_applied_rule_num):
    sampled_rules = random.sample(rules, random.randint(1, max_applied_rule_num))
    rewritten_prompt, cost = apply_rules_to_prompt(prompt, sampled_rules, func)
    return rewritten_prompt, sampled_rules, cost


def evaluate(context, query_prefix, questions, func, n=3):
    positive_num = 0
    total_cost = 0.0

    for _ in tqdm.tqdm(range(n), leave=False, desc=f'Evaluating prompt(#questions={len(questions)},#trials={n})'):
        for q in tqdm.tqdm(questions, leave=False):
            ret, cost = func(context, query_prefix + "\n" + q['question'], {'multiple_choice': 1})
            total_cost += cost if cost is not None else 0.0

            try:
                if int(ret) == int(q['answer']):
                    positive_num += 1
            except:
                continue

    return positive_num / (len(questions) * n), total_cost


def split_data(data, ratio=0.8, shuffle=True):
    if shuffle:
        random.shuffle(data)

    train_size = int(len(data) * ratio)
    train_data = data[:train_size]
    test_data = data[train_size:]

    return train_data, test_data


def prepare_rules(rules, rule_domain_size, func):
    diff = rule_domain_size - len(rules)
    if diff <= 0:
        return random.sample(rules, rule_domain_size), 0.0

    total_cost = 0.0
    for _ in tqdm.tqdm(range(diff), desc=f'[Generating {diff} rules]'):
        query = PROPOSE_RULE_PROMPT + "\n".join(list(map(lambda x: ' - ' + x, rules)))
        rule, cost = func('', query)
        total_cost += cost if cost is not None else 0.0
        rules.append(rule)

    return rules, total_cost


def optimize_prompt(initial_prompt, query_prefix, questions, rules, func,
                    rule_domain_size,
                    max_iter, max_applied_rule_num, max_example_num,
                    trace_enabled=False):
    best_prompt, best_score = '', -1.0
    base_prompt = initial_prompt
    initial_score = 0.0
    total_cost = 0.0
    trace = []

    demonstrations, questions = split_data(questions, ratio=0.4)

    try:
        # First, compute the base score by using the initial prompt
        initial_score, cost = evaluate(base_prompt, query_prefix, questions, func, n=3)
        total_cost += cost if cost is not None else 0.0

        rules, cost = prepare_rules(rules, rule_domain_size, func)
        total_cost += cost if cost is not None else 0.0

        with tqdm.tqdm(range(max_iter)) as pb:
            for _ in pb:
                if total_cost > 0.0:
                    pb.set_description(f"[Best Score:{best_score:.2f}, Cost:{total_cost:.2f}]")
                else:
                    pb.set_description(f"[Best Score:{best_score:.2f}]")

                # TODO: Improve a strategy for searching the best context prompt (e.g., use hyperpot?)
                rewritten_prompt, applied_rules, cost = rewrite_prompt(base_prompt, rules, func, max_applied_rule_num)
                total_cost += cost if cost is not None else 0.0

                # Selects some of demonstrations for filling the prompt
                examples = random.sample(demonstrations, random.randint(1, max_example_num))
                examples = list(map(lambda x: f"問題例{x[0]}:\n{x[1]['question']}\n\n問題例{x[0]}の解答: {x[1]['answer']}",
                                    enumerate(examples)))

                # TODO: Support the hyperparameter search for LLM params (e.g., temperature)
                # TODO: Pass an additional 'params' parameter in 'func'
                query = rewritten_prompt + "\n" + "\n\n".join(examples)
                score, cost = evaluate(query, query_prefix, questions, func, n=3)
                total_cost += cost if cost is not None else 0.0

                if trace_enabled:
                    trace.append({'score': score, 'prompt': query, 'rules': applied_rules})

                if best_score < score:
                    base_prompt = rewritten_prompt
                    best_prompt = query
                    best_score = score

    except (KeyboardInterrupt, Exception) as e:
        print("Failed midway because: " + str(e))
        pass

    if trace_enabled:
        return best_prompt, best_score, {
                'best_score': best_score,
                'best_prompt': best_prompt,
                'initial_score': initial_score,
                'initial_prompt': initial_prompt,
                'rules': rules,
                'trace': trace
            }

    return best_prompt, best_score, {}


_logger = setup_logger()


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--prompt', type=str, required=True)
    parser.add_argument('--questions', type=str, required=True)
    parser.add_argument('--module', type=str, required=True)
    parser.add_argument('--rules', type=str, required=True)
    parser.add_argument('--rule_domain_size', type=int, required=True)
    parser.add_argument('--query-prefix', type=str, default='PostgreSQLに関する質問:')
    parser.add_argument('--max-iter', type=int, default=32)
    # Too many rules aplied can deteriorate accuracy
    parser.add_argument('--max-applied-rule-num', type=int, default=3)
    parser.add_argument('--max-example-num', type=int, default=3)
    parser.add_argument('--trace', action='store_true')
    args = parser.parse_args()

    # Load an initial prompt given by a user
    prompt = Path(args.prompt).read_text(encoding='utf-8')

    with open(args.questions, 'r', encoding='utf-8') as f:
        loaded = tomllib.loads(f.read())

    # Validate loaded data for loading questions
    questions = openai_response_format.question_validate(loaded['questions'])

    _logger.info("{num} PostgreSQL questions loaded\n".format(num=len(questions)))

    with open(args.rules, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # Load an evaluation function from a given Python file
    func = import_function(args.module)

    # TODO: The current logic higly depends on the initial prompt,
    # against the issue, what can we do for improving accuracy?
    opt_prompt, score, trace = optimize_prompt(
            prompt, args.query_prefix, questions, rules, func,
            args.rule_domain_size,
            args.max_iter, args.max_applied_rule_num, args.max_example_num,
            trace_enabled=args.trace)

    ts = datetime.now().strftime("%Y%m%d%H%M%S")

    if args.trace:
        with open(f'trace_{ts}.json', 'w', encoding='utf-8') as f:
            json.dump(trace, f, indent=2, ensure_ascii=False)

    basename, ext = os.path.splitext(os.path.basename(args.prompt))
    filename = "{bn}_optimized_{ts}{ext}".format(bn=basename, prefix=args.prompt, ts=ts, ext=ext)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(opt_prompt)

    print(f"Written to {filename}")


if __name__ == "__main__":
    main()
