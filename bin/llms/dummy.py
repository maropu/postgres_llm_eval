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
import time


def dymmy_fn(system_prompt, user_prompt, params={}) -> str:
    if 'print_prompt' in params:
        print(f"system_prompt:\n{system_prompt}\nuser_prompt:\n{user_prompt}")

    # Emulate Web API turn-around time
    time.sleep(params['sleep_time'] if 'sleep_time' in params else 0)
    ret = str(random.randint(0, 4)) if 'multiple_choice' in params else system_prompt + user_prompt
    cost = float(params['cost']) if 'cost' in params else None
    return ret, cost

