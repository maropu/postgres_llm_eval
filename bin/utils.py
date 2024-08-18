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

import importlib.util
import inspect
import os
import re


def setup_logger():
    from logging import getLogger, Formatter, NullHandler, StreamHandler, INFO
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    logging_enabled = os.getenv('LOGGING_ENABLED')

    if logging_enabled:
        console_handler = StreamHandler()
        format = "%(levelname)s  %(asctime)s [%(filename)s:%(lineno)d] %(message)s"
        console_handler.setFormatter(Formatter(format))
        logger.addHandler(console_handler)
    else:
        logger.addHandler(NullHandler())

    return logger


# Logger for internal use in this module
_logger = setup_logger()


def _list_functions_in_file(module_path):
    try:
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        functions = [name for name, obj in inspect.getmembers(module, inspect.isfunction)]
        return functions
    except Exception as e:
        raise ValueError(f"Can't load {module_path}: {e}")


def _import_function_from_file(module_path, function_name):
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function_name)


def import_function(module_path):
    # Load an evaluation function from a given Python file
    function_names = _list_functions_in_file(module_path)
    if len(function_names) == 0:
        raise ValueError(f"Can't load any function from '{module_path}'")
    if len(function_names) > 1:
        raise ValueError(f"Multiple functions found in '{module_path}', it must have only one function")

    fn = function_names[0]
    func = _import_function_from_file(module_path, fn)
    _logger.info(f"Function '{fn}' loaded from '{module_path}'")

    return func


def _escape_newline_in_quotes(text):
    def _escape_newline(match):
        return match.group(0).replace('\n', '\\n')

    return re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', _escape_newline, text)


def _escape_non_newline_in_quotes(s):
    def _replace_escapes(match):
        quoted_string = match.group(1)
        return re.sub(r'\\(?!n)(.)', r'\\\1', quoted_string)

    result = re.sub(r'(".*?")', _replace_escapes, s)
    return result


def preprocess_llm_json_output(s):
    s = _escape_newline_in_quotes(s)
    s = _escape_non_newline_in_quotes(s)
    return s

