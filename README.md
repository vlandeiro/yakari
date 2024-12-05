# Yakari

<img src="./static/yakari.png" width="220" align="right" />

Transform complex command-line interfaces into guided, interactive experiences. Yakari
helps users build commands step by step, making CLI tools more accessible and
user-friendly through contextual assistance.

Powered by [pydantic](https://github.com/pydantic/pydantic) and
[textual](https://github.com/Textualize/textual).

**Features**: 

- [X] Interactive command building
- [X] Contextual help and descriptions
- [X] Works alongside existing CLI tools
- [X] Command history across executions
- [X] Suggestions from other commands
- Supported argument types:
  - [X] Flag argument
  - [X] Single-value argument
  - [X] Multi-choice argument 
  - [X] Password argument
  - [X] Multi-value argument
  - [ ] File argument

## How it works?

Yakari is built around three core concepts:

- A `Menu` organizes your command structure through a collection of sub-menus, arguments, and commands
- An `Argument` represents an interactive variable (flag, named argument, or positional argument) that users can modify
- A `Command` defines the final executable instruction

Yakari uses TOML configuration files to define menus. Here's an example that creates
a simple `git` menu for branch operations:

```toml
name = "git"

[menus.b]
name = "Branch operations"

[menus.b.arguments]
"-f" = { flag="--force" }

[menus.b.commands.b]
name = "create"
description = "Create new branch"
template = [
    "git", 
    "checkout", 
    {varname="optional_arguments"},  # special deferred value to capture all menu arguments
    "-b", {name="branch_name"}       # dynamic argument querying the user at run time
]

[menus.b.commands.d]
name = "delete"
description = "Delete a branch"
template = ["git", "branch", {varname="optional_arguments"}, "-d", {name="branch_name"}]

[menus.b.commands.l]
name = "list"
description = "List branches"
template = ["git", "branch", {varname="optional_arguments"}, "--list"]
```

## Using Predefined Configurations

Yakari comes with a set of ready-to-use configurations. To get started:

1. Link or copy the configurations to your config directory:
``` sh
ln -s /path/to/yakari/configurations ~/.config/yakari
```

2. Run commands using the shorter syntax:
   - Instead of `yakari ~/.config/yakari/git.toml`
   - Simply use `yakari git`

Yakari automatically searches for matching TOML configurations in `~/.config/yakari`.

## Why Yakari?

The name comes from a Franco-Belgian comic book character who can talk to
animals. Similarly, this tool helps users communicate more naturally with
command-line programs by turning intimidating command structures into guided
conversations.
