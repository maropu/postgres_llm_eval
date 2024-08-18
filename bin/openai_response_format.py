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

from pydantic import BaseModel, RootModel, conint, constr, ValidationError
from typing import List, Optional


class Question(BaseModel):
    question: constr(min_length=1)
    answer: conint(ge=0, le=4)
    changelog: Optional[constr(min_length=1)] = None


class QuestionList(RootModel):
    root: List[Question]


def question_validate(data):
    try:
        questions = QuestionList.model_validate(data)
        return [q.model_dump() for q in questions.root]
    except ValidationError as e:
        print(e)
        exit(-1)

