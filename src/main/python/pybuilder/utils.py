#   This file is part of PyBuilder
#
#   Copyright 2011-2013 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json
import os
import re
import subprocess
import tempfile
import time

from pybuilder.errors import MissingPrerequisiteException, PythonbuilderException


def render_report(report_dict):
    return json.dumps(report_dict, indent=2)


def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def timedelta_in_millis(timedelta):
    return((timedelta.days * 24 * 60 * 60) + timedelta.seconds) * 1000 + round(timedelta.microseconds / 1000)


def as_list(*whatever):
    """
        Returns a list containing all values given in whatever.
        Each list or tuple will be "unpacked", all other elements
        are added to the resulting list.

        Examples given

        >>> as_list('spam')
        ['spam']

        >>> as_list('spam', 'eggs')
        ['spam', 'eggs']

        >>> as_list(('spam', 'eggs'))
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'])
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'], ('spam', 'eggs'), 'foo', 'bar')
        ['spam', 'eggs', 'spam', 'eggs', 'foo', 'bar']
    """
    result = []

    for w in whatever:
        if w is None:
            continue
        elif isinstance(w, list):
            result += w
        elif isinstance(w, tuple):
            result += w
        else:
            result.append(w)
    return result


def discover_modules(source_path, suffix=".py"):
    result = []
    for module in discover_files(source_path, suffix):
        module = module.replace(source_path, "")
        module = module.replace(os.sep, ".")
        module = module[1:-3]
        if module.endswith(".__init__"):
            module = module.replace(".__init__", "")
        result.append(module)
    return result


def discover_files(start_dir, suffix):
    for root, _, files in os.walk(start_dir):
        for file_name in files:
            if file_name.endswith(suffix):
                yield os.path.join(root, file_name)


def execute_command(command_and_arguments, outfile_name, env=None, cwd=None, error_file_name=None, shell=False):
    if error_file_name is None:
        error_file_name = outfile_name + ".err"

    with open(outfile_name, "w") as out_file:
        with open(error_file_name, "w") as error_file:
            process = subprocess.Popen(command_and_arguments,
                                       stdout=out_file,
                                       stderr=error_file,
                                       env=env,
                                       cwd=cwd,
                                       shell=shell)
            return process.wait()


def assert_can_execute(command_and_arguments, prerequisite, caller):
    _, outfile = tempfile.mkstemp()
    f = open(outfile, "w")
    try:
        process = subprocess.Popen(command_and_arguments, stdout=f, stderr=f, shell=False)
        process.wait()
    except OSError:
        raise MissingPrerequisiteException(prerequisite, caller)
    finally:
        f.close()
        os.unlink(outfile)


def read_file(file_name):
    with open(file_name, "r") as file_handle:
        return file_handle.readlines()


def write_file(file_name, *lines):
    with open(file_name, "w") as file_handle:
        file_handle.writelines(lines)


class Timer(object):
    @staticmethod
    def start():
        return Timer()

    def __init__(self):
        self.start_time = time.time()
        self.end_time = None

    def stop(self):
        self.end_time = time.time()

    def get_millis(self):
        if self.end_time is None:
            raise PythonbuilderException("Timer is running.")
        return int((self.end_time - self.start_time) * 1000)


def apply_on_files(start_directory, closure, globs, *additional_closure_arguments, **keyword_closure_arguments):
    glob_expressions = list(map(lambda g: GlobExpression(g), globs))

    for root, _, file_names in os.walk(start_directory):
        for file_name in file_names:
            absolute_file_name = os.path.join(root, file_name)
            relative_file_name = absolute_file_name.replace(start_directory, "")[1:]

            for glob_expression in glob_expressions:
                if glob_expression.matches(relative_file_name):
                    closure(absolute_file_name,
                            relative_file_name,
                            *additional_closure_arguments,
                            **keyword_closure_arguments)


class GlobExpression(object):
    def __init__(self, expression):
        self.expression = expression
        self.regex = "^" + expression.replace("**", ".+").replace("*", "[^/]*") + "$"
        self.pattern = re.compile(self.regex)

    def matches(self, path):
        if self.pattern.match(path):
            return True
        return False


def mkdir(directory):
    """
    Tries to create the directory denoted by the given name. If it exists and is a directory, nothing will be created
    and no error is raised. If it exists as a file a PythonbuilderException is raised. Otherwise the directory incl.
    all parents is created.
    """

    if os.path.exists(directory):
        if os.path.isfile(directory):
            message = "Unable to created directory '%s': A file with that name already exists"
            raise PythonbuilderException(message, directory)
        return
    os.makedirs(directory)
