from .types import Menu
from pydantic import BaseModel
import subprocess
from openai import OpenAI

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain.prompts import (
        SystemMessagePromptTemplate,
        HumanMessagePromptTemplate,
        ChatPromptTemplate,

    )
    from langchain_openai import ChatOpenAI
except ImportError:
    raise


class RunHelpCommand(BaseModel):
    command: str


class ModelResult(BaseModel):
    more_information_needed: bool
    result: RunHelpCommand | Menu



system_msg = """
# Instructions

You are a software engineer specialized in reading and making sense of CLI
documentation. Your task is to write a structured version of all the options
available through a CLI using structured JSON as an output. You are going to
receive an input using the following template:

```md
## CLI command

<the base command (e.g. docker, git)>

## Help command

<command to retrieve the help for the base command, e.g. >

## Help command's result

<result of the help command, often multiline>
```

You have two valid answers to give for every message:

## 1. Ask for more information

You can get more documentation by asking for the documentation of a SPECIFIC
subcommand (e.g. `git commit`). To do so, you must return a JSON object
in the following format:

```json
{
  "more_information_needed": true,
  "result": {"command": <the command you want to run to get further help information (e.g. git commit --help), this cannot contain any placeholder values>}
}
```

## 2. Return the JSON formatted result

Once you have enough information to generate the full specification of the CLI,
return a JSON object representation in the following format:

```json
{
  "more_information_needed": false,
  "result": <nested menu using the Menu schema>
}
```
"""


def get_help_command_result(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True).stdout.decode()


base_command = "git"
help_command = "git --help"
help_command_result = get_help_command_result(help_command)

human_msg = f"""
## CLI command

{base_command}

## Help command

{help_command}

## Help command's result

```
{help_command_result}
```
"""

model_name = "gpt-4o-mini"
llm1 = ChatOpenAI(model_name=model_name).with_structured_output()
llm2 = ChatOpenAI(model_name=model_name).with_structured_output(ModelResult)

# Create message prompts
messages = [
    SystemMessage(system_msg),
    HumanMessage(human_msg)
]

# Get response from LLM
result: ModelResult = llm.invoke(messages)

count = 0
while True:
    count += 1
    if count > 5:
        break
    print(result)

    if result.more_information_needed:
        messages.append(SystemMessage(result.model_dump_json()))
        help_command = result.result.command
        help_command_result = get_help_command_result(help_command)

        messages.append(HumanMessage(
            f"## Help command\n\n{help_command}\n\n## Help command's result\n\n{help_command_result}"
        ))
        llm.invoke(messages)

# client = OpenAI()

# completion = client.beta.chat.completions.parse(
#     model="gpt-4o",
#     messages=[
#         {"role": "system", "content": system_template},
#         {"role": "user", "content": human_template},
#     ],
#     response_format=ModelResult,
# )

# event = completion.choices[0].message.parsed

# print(event)
