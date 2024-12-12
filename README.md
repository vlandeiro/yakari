# Yakari

Transform complex command-line interfaces into guided, interactive experiences. Yakari
helps users build commands step by step, making CLI tools more accessible and
user-friendly.


## Getting started

### Usage

<img src="./static/yakari.png" width="220" align="right" />

``` bash
usage: yakari [-h] [-d] [-n] command_name

positional arguments:
  command_name   Name of the command to execute

options:
  -h, --help     show this help message and exit
  -d, --dry-run  If toggled, Yakari only prints the command rather than running it.
  -n, --native   When toggled, run the command in the original shell instead of within the Yakari menu.
```

### Try it out!

With [uv](https://github.com/astral-sh/uv):

``` bash
uvx --from git+https://github.com/vlandeiro/yakari yakari demo
```

will start a demo that showcases the different types or arguments and commands.
This demo doesn't run any actual command other than `echo` so it's safe to use
anywhere.

``` bash
uvx --from git+https://github.com/vlandeiro/yakari yakari git
```

will start a TUI with basic `git` features. The video below shows how to use
this TUI to:

- list branches
- create and checkout a new `demo` branch
- add a file and create a commit
- check the git log to validate that the commit has been created
- delete the `demo` branch

https://github.com/user-attachments/assets/4202d30c-180a-4740-9e69-2b123f2e6dd4

Play around with this in a git repo!

### Basic Navigation

Yakari is an interactive command menu that makes it easy to run complex commands. 
Think of it as a smart command launcher where you type shortcuts instead of remembering full commands.

#### Start Typing

When you launch Yakari, you'll see a menu of available options. Every menu item has a shortcut (shown on the left). Type the shortcut to select it:
- Commands (things you can run)
- Arguments (options you can set)
- Subcommands (more options inside)

Other important keyboard shortcuts let you interact with the TUI:

| Key         | Action                   |
|-------------|--------------------------|
| ctrl+c      | Cancel/Exit              |
| backspace   | Erase/Go back            |
| tab         | Auto-complete            |
| slash       | Toggle results           |
| ctrl+e      | Toggle edit mode         |

> ![screenshot illustrating how yakari highlights compatible commands based on user's input](https://github.com/user-attachments/assets/95489bcd-832a-488b-b4eb-e75b5bcb30ec)
> **Example**: In the git branch menu, typing `-` highlights the `-f` and `-t` arguments, and dims other entries.

#### Working with Arguments

Arguments are options you can set. There are two modes for handling them:

Normal Mode (default):
- Selecting an argument toggles it on/off
- Great for quick switches like `--verbose`

Edit Mode (press `ctrl+e` to switch):
- Selecting an argument lets you edit its value
- Perfect for editing named argument with an existing value


### (Optional) Installation

Yakari is not yet published to PyPI - install directly from GitHub:

```bash
# Using pip
pip install git+https://github.com/vlandeiro/yakari.git

# Using uv
uv add git+https://github.com/vlandeiro/yakari.git
```

> [!TIP]
> Yakari comes with a set of [pre-defined menus](https://github.com/vlandeiro/yakari-menus)
> that you can use via `yakari <command-name>` (e.g. `yakari git`) without having to copy
> them to your machine.


## Features

- Interactive command building
- Contextual help and descriptions
- Works alongside existing CLI tools
- Command history across executions
- Static and dynamic suggestions
- In-place command execution with streamed output
- Supported argument types:
  - Flag argument
  - Single-value argument
  - Multi-choice argument 
  - Password argument
  - Multi-value argument

### Roadmap
- Add unit tests everywhere
- Add documentation on creating custom menus
- Publish to PyPi
- Add argument types:
  - File argument
- Support environment variables
- Support interactive commands when running in place

## References

- **Heavily** inspired by [transient](https://github.com/magit/transient).
- Powered by:
  - [textual](https://github.com/Textualize/textual)
  - [pydantic](https://github.com/pydantic/pydantic)

### Why Yakari?

The name comes from a Franco-Belgian comic book character who can talk to
animals. Similarly, this tool helps users communicate more naturally with
command-line programs by turning intimidating command structures into guided
conversations.
