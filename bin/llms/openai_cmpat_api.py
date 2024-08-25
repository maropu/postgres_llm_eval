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

import requests
import retrying
import timeout_decorator


OPENAI_CMPAT_API_SERV_HOST = '127.0.0.1:8080'
OPENAI_CMPAT_API_SERV_MODEL = 'mmnga-Llama-3.1-8B-EZO-1.1-it-Q8_0.gguf'
OPENAI_CMPAT_API_SERV_API_KEY = ''


# For a list of requests's exceptions, see:
# https://docs.python-requests.org/en/latest/user/quickstart/#errors-and-exceptions
def _retry_if_timeout(caught: Exception) -> bool:
    return isinstance(caught, requests.exceptions.Timeout)


def _to_error_msg(text: str) -> str:
    try:
        return (json.loads(text))['message']
    except:
        return text


@timeout_decorator.timeout(120, timeout_exception=RuntimeError)
@retrying.retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=4000,
                retry_on_exception=_retry_if_timeout,
                wrap_exception=False)
def openai_compat_api(system_prompt, user_prompt, api='chat/completions') -> str:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_CMPAT_API_SERV_API_KEY}',
        'User-Agent': 'openai_compat_api'
    }
    ret = requests.get(f'http://{OPENAI_CMPAT_API_SERV_HOST}/openai-api/v1/{api}',
                       timeout=10, headers=headers, verify=False)
    if ret.status_code != 200:
        error_msg = "REST API '{api}' request failed because: status_code={code}, msg='{msg}'"
        error_msg = error_msg.format(api=api,  status_code=ret.status_code, msg=_to_error_msg(ret.text))
        raise RuntimeError(error_msg)

    return ret.text

