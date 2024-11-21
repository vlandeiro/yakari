<img src="./static/yakari.png" width="150" align="left" />

# Yakari

Yakari is an interactive command generation tool. It aims to recreate the experience from Emacs's transient package.

## Motivation

- Magit is a tool to interact with ~git~ in emacs.
- Its interface lets users use ~git~ and discover new features.
- It relies on the ~transient~ library, an [[https://magit.vc/manual/transient/][Emacs package]] written in Emacs Lisp
  (https://magit.vc/manual/transient/).
- Emacs is not used by everyone and I could not find existing tools that
  reproduced the same behavior outside of Emacs.

## Definition

- yakari is a command generator and command invoker
- yakari calls existing CLIs
- yakari is not a replacement for click, fire, docopt, argparse, etc
