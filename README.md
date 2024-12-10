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

## Roadmap

- Add documentation on creating custom menus
- Add unit tests everywhere
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
