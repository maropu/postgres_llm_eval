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
import openai_response_format
import prompt_template
import tomllib
import tqdm
import statistics
from pathlib import Path
from utils import setup_logger, import_function


EVALSTATE_FILENAME_TEMPLATE = ".evalstate_{hc}.json"


class EvalResultState:

    def __init__(self, state=None):
        self.positive_ratio_seq = state['positive_ratio_seq'] if state else []
        self.illegal_ratio_seq = state['illegal_ratio_seq'] if state else []
        self.unknown_ratio_seq = state['unknown_ratio_seq'] if state else []

    def append(self, positive_ratio, illegal_ratio, unknown_ratio):
        self.positive_ratio_seq.append(positive_ratio)
        self.illegal_ratio_seq.append(illegal_ratio)
        self.unknown_ratio_seq.append(unknown_ratio)

    def sample_num(self):
        return len(self.positive_ratio_seq)

    def avg_positive_ratio(self):
        return sum(self.positive_ratio_seq) / len(self.positive_ratio_seq)

    def stdev_positive_ratio(self):
        return statistics.stdev(self.positive_ratio_seq)

    def avg_illegal_ratio(self):
        return sum(self.illegal_ratio_seq) / len(self.illegal_ratio_seq)

    def avg_unknown_ratio(self):
        return sum(self.unknown_ratio_seq) / len(self.unknown_ratio_seq)

    def to_dict(self):
        return {
            'positive_ratio_seq': self.positive_ratio_seq,
            'illegal_ratio_seq': self.illegal_ratio_seq,
            'unknown_ratio_seq': self.unknown_ratio_seq
        }


_logger = setup_logger()


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--questions', type=str)
    parser.add_argument('--module', type=str)
    parser.add_argument('--version', type=str)
    parser.add_argument('--prompt', type=str)
    parser.add_argument('--nsamples', type=int, default=12)
    parser.add_argument('--resume', type=str)
    args = parser.parse_args()

    if not ((args.questions and args.module) or args.resume):
        raise ValueError('If `--resume` not given, you must specify both `--questions` and `--module`')

    prev_state = None

    if not args.resume:
        version = args.version
        module_path = args.module

        user_prompt = ''
        if args.prompt is not None:
            user_prompt = Path(args.prompt).read_text(encoding='utf-8')

        # system_prompt = prompt_template.POSTGRES_QA_PROMPT_TEMPLATE.format(prompt=user_prompt, version=version)
        system_prompt = user_prompt

        with open(args.questions, 'r', encoding='utf-8') as f:
            loaded = tomllib.loads(f.read())

        # Validate loaded data for loading questions
        questions = openai_response_format.question_validate(loaded['questions'])
        for q in questions:
            # Initialize lists for storing LLM results
            q['results'] = []
    else:
        with open(args.resume, 'r', encoding='utf-8') as f:
            # TODO: Validate `prev_state` using pydantic
            prev_state = json.load(f)

        version = prev_state['version']
        module_path = prev_state['module']
        system_prompt = prev_state['system_prompt']
        questions = prev_state['questions']

    question_num = len(questions)

    _logger.info("{num} questions of PostgreSQL{version} loaded\n".format(num=question_num, version=version if version is not None else ''))
    _logger.info(f"System prompt:\n{system_prompt}")

    # Load an evaluation function from a given Python file
    func = import_function(module_path)

    # If `prev_state` given, fill evaluation state with the previous results
    eval_state = EvalResultState(prev_state)

    # Keep pay-as-you-go service cost if possible
    total_cost = 0.0

    try:
        for _ in tqdm.tqdm(range(args.nsamples)):
            positive_num = 0
            illegal_num = 0
            unknown_num = 0

            for q in tqdm.tqdm(questions, leave=False):
                ret, cost = func(system_prompt, q['question'])
                q['results'].append(ret)

                total_cost += cost if cost else 0.0

                try:
                    response = int(ret)
                except:
                    illegal_num += 1
                    continue

                if response == int(q['answer']):
                    positive_num += 1
                elif response == 0:
                    unknown_num += 1

            eval_state.append(positive_num / question_num, illegal_num / question_num,
                              unknown_num / question_num)

    finally:
        print("Averaged Accuracy(#samples={nsamples}): {acc}(sd={sd})".format(
                nsamples=eval_state.sample_num(), acc=eval_state.avg_positive_ratio(),
                sd=eval_state.stdev_positive_ratio()))

        print("  - # of unknown responses: {num}".format(num=eval_state.avg_unknown_ratio()))
        print("  - # of illegal responses: {num}".format(num=eval_state.avg_illegal_ratio()))
        print("")

        if total_cost > 0.0:
            print("Total Estimated Cost: ${cost}".format(cost=total_cost))
            print("")

        # Write down the current state to a file
        evalstate_fn = None
        evalstate = {
            'version': version,
            'module': module_path,
            'system_prompt': system_prompt,
            'questions': questions
        }

        if not args.resume:
            s = "{}{}{}{}{}".format(version, module_path, func.__name__, question_num, system_prompt)
            hashcode = hashlib.sha256(s.encode()).hexdigest()
            evalstate_fn = EVALSTATE_FILENAME_TEMPLATE.format(hc=hashcode[0:8])
        else:
            evalstate_fn = args.resume

        with open(evalstate_fn, 'w', encoding='utf-8') as f:
            json.dump(evalstate | eval_state.to_dict(), f, indent=2,
                      ensure_ascii=False)

        print(f"Written to {evalstate_fn}")


if __name__ == "__main__":
    main()
