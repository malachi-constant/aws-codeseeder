#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
import shutil
import subprocess
from typing import List, cast

from aws_codeseeder import CLI_ROOT, LOGGER, bundle, create_output_dir
from aws_codeseeder.services import cfn

FILENAME = "update_repo.sh"
RESOURCES_FILENAME = os.path.join(CLI_ROOT, "resources", FILENAME)


def _prep_modules_directory() -> str:
    LOGGER.info("Preparing modules working directory")
    out_dir = create_output_dir("modules")
    dst_file = os.path.join(out_dir, FILENAME)
    LOGGER.debug("Copying file to %s", dst_file)
    shutil.copy(src=RESOURCES_FILENAME, dst=dst_file)

    return out_dir


def deploy_modules(toolkit_name: str, python_modules: List[str]) -> None:
    stack_name: str = cfn.get_stack_name(toolkit_name=toolkit_name)
    LOGGER.info("Deploying Modules for Toolkit %s with Stack Name %s", toolkit_name, stack_name)
    LOGGER.debug("Python Modules: %s", python_modules)

    stack_exists, stack_outputs = cfn.does_stack_exist(stack_name=stack_name)
    if not stack_exists:
        LOGGER.warn("Toolkit/Stack does not exist")
        return
    domain = stack_outputs.get("CodeArtifactDomain")
    repository = stack_outputs.get("CodeArtifactRepository")

    if any([":" not in pm for pm in python_modules]):
        raise ValueError(
            "Invalid `python_module`. Modules are identified with '[module-name]:[directory]': %s", python_modules
        )

    out_dir = _prep_modules_directory()
    modules = {ms[0]: ms[1] for ms in [m.split(":") for m in python_modules]}

    for module, dir in modules.items():
        LOGGER.info("Creating working directory for Module %s", module)
        bundle.generate_dir(out_dir=out_dir, dir=dir, name=module)

    for module, dir in modules.items():
        LOGGER.info("Deploy Module %s to Toolkit Domain/Repository %s/%s", module, domain, repository)
        subprocess.check_call(
            [os.path.join(out_dir, FILENAME), cast(str, domain), cast(str, repository), module, module]
        )
