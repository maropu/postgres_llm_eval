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

import sys
from pathlib import Path
from utils import import_function


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--module', type=str, required=True)
    parser.add_argument('--fn', type=str)
    parser.add_argument('--context', type=str)
    args = parser.parse_args()

    # Load an evaluation function from a given Python file
    func = import_function(args.module, fn=args.fn)

    # Load an system prompt if given
    context = ''
    if args.context is not None:
        context = Path(args.context).read_text(encoding='utf-8')

    generated, cost = func(context, ''.join(sys.stdin.readlines()))

    if cost is not None:
        print('Estimated Cost: {}'.format(cost))

    print("'{fn}' generated:".format(fn=func.__name__))
    print(generated)


if __name__ == "__main__":
    main()
