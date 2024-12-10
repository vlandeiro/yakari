# Yakari

<img src="./static/yakari.png" width="220" align="right" />

Transform complex command-line interfaces into guided, interactive experiences. Yakari
helps users build commands step by step, making CLI tools more accessible and
user-friendly.

**Features**: 

- Interactive command building
- Contextual help and descriptions
- Works alongside existing CLI tools
- Command history across executions
- Static and dynamic suggestions
- In-place command execution
- Supported argument types:
  - Flag argument
  - Single-value argument
  - Multi-choice argument 
  - Password argument
  - Multi-value argument

## Getting started

### (Optional) Installation

Yakari is not yet published to PyPI - install directly from GitHub:

```bash
# Using pip
pip install git+https://github.com/vlandeiro/yakari.git

# Using uv
uv add git+https://github.com/vlandeiro/yakari.git
```

> [!TIP]
> Yakari comes with a set of [pre-defined menus](https://github.com/vlandeiro/yakari/tree/master/configurations/tree/master/configurations).
> Copy the menus you want to use into `~/.config/yakari/configurations` (e.g. `git.toml`) so you can run `yakari git` instead of `yakari https://raw.githubusercontent.com/vlandeiro/yakari/refs/heads/master/configurations/git.toml`

### Basic Navigation

Yakari is an interactive command menu that makes it easy to run complex commands. 
Think of it as a smart command launcher where you type shortcuts instead of remembering full commands.

#### Start Typing

When you launch Yakari, you'll see a menu of available options. Just start typing - Yakari instantly shows what matches your input!

<figure>
  <img src="https://github.com/user-attachments/assets/95489bcd-832a-488b-b4eb-e75b5bcb30ec" alt="screenshot illustrating how yakari highlights compatible commands based on user's input" />
  <figcaption>In the git branch menu, typing `-` highlights the `-f` and `-t` arguments, and dims other entries.</figcaption>
</figure>

Every menu item has a shortcut (shown on the left). Type the shortcut to select it:
- Commands (things you can run)
- Arguments (options you can set)
- Subcommands (more options inside)

Example:
```
b    branch       Switch to an existing branch
c    checkout     Create a new branch and switch to it
C    create       Create a new branch but stay on the current branch
```

#### Key Controls

The most important keys to know:

`backspace`
- Erases the last character you typed
- Goes back to the previous menu when there are no more character to erase

`tab`
- Auto-completes when there's only one matching option

`slash`
- Toggles the results window

#### Working with Arguments

Arguments are options you can set. There are two modes for handling them:

Normal Mode (default):
- Selecting an argument toggles it on/off
- Great for quick switches like `--verbose`

Edit Mode (press `ctrl+e` to switch):
- Selecting an argument lets you edit its value
- Perfect for editing named argument with an existing value

### Try it out!

#### Arguments and commands showcase

With [uv](https://github.com/astral-sh/uv) installed, run `uvx --from git+https://github.com/vlandeiro/yakari yakari https://raw.githubusercontent.com/vlandeiro/yakari/refs/heads/master/configurations/demo.toml`
to start a demo that showcases the different types or arguments and commands. This demo doesn't run any actual command other than `echo` so it's safe to use anywhere.

#### Git example

Running `uvx --from git+https://github.com/vlandeiro/yakari yakari https://raw.githubusercontent.com/vlandeiro/yakari/refs/heads/master/configurations/git.toml`
will start a TUI with basic `git` features. The video below shows how to use this TUI to:

- list branches
- create and checkout a new `demo` branch
- add a file and create a commit
- check the git log to validate that the commit has been created
- delete the `demo` branch

https://github.com/user-attachments/assets/4202d30c-180a-4740-9e69-2b123f2e6dd4

Play around with this in a git repo!

### Create your own menus [WIP]

Yakari is built around three core concepts:

- An `Argument` represents an interactive variable (flag, named argument, or
  positional argument) that users can modify
- A `Command` represents the final executable instruction
- A `Menu` is a collection of arguments, commands, and sub-menus.

Yakari uses TOML configuration files to define menus. Here's an example that creates
a menu to list/create/delete git branches:

```toml
[menus.b]
name = "Branch operations"

[menus.b.arguments]
"-f" = { flag = "--force" }

[menus.b.commands.b]
name = "create"
description = "Create new branch"
template = [
  "git",
  "branch",
  { include = "*" },
  { name = "branch_name" },
]

[menus.b.commands.d]
name = "delete"
description = "Delete a branch"
template = [
  "git",
  "branch",
  { include = "*" },
  "-d",
  {
    name = "branch_name",
    suggestions = { command = "git for-each-ref --format='%(refname:short)' refs/heads/" }
  }
]

[menus.b.commands.l]
name = "list"
description = "List branches"
template = ["git", "branch", "--list"]
```

## Roadmap

- Publish to PyPi
- Add argument types:
  - File argument
- Support environment variables
- Stream command outputs instead of blocking until the command finishes
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
