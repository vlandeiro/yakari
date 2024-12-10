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

**Roadmap**:
- Publish to pip.
- Add argument types:
  - File argument
- Support environment variables.
- Stream command outputs instead of waiting.


## Run the demo

If you already have [uv](https://github.com/astral-sh/uv) installed, you can run the demo with:

```sh
uvx \
    --from git+ssh://git@github.com/vlandeiro/yakari \
    yakari https://raw.githubusercontent.com/vlandeiro/yakari/refs/heads/master/configurations/demo.toml
```

## How it works?

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

## Use existing configurations

Yakari comes with a set of ready-to-use configurations. To get started:

1. Link or copy the configurations to your config directory:
``` sh
ln -s /path/to/yakari/configurations ~/.config/yakari
```

2. Run commands using the shorter syntax:
   - Instead of `yakari ~/.config/yakari/configurations/git.toml`
   - Simply use `yakari git`

Yakari automatically searches for matching TOML configurations in `~/.config/yakari`.

## Create new configurations

If a CLI you use is not yet supported or you want to build your own collection
of commands, create a new TOML file with the following template:

``` toml
name = "My Yakari Menu"

# High-level configuration applied to every menu
[configuration]
# Toggles to sort arguments, command, and menus by alphabetical order. Default to true.

# sort_arguments = false
# sort_commands = true
# sort_menus = true

[configuration.named_arguments_style]
# The way to represent named argument and multi-valued named argument is
# different from one CLI to the next. This section lets you update the style so
# Yakari matches your target CLI.

separator = "equal"    # MUST be one of "equal" or "space"
multi_style = "repeat" # MUST be "repeat" or a single character like " " or ","
```

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
