- [Transient CLI in Python](#sec-1)
  - [Motivation](#sec-1-1)
  - [Definition](#sec-1-2)
  - [Architecture](#sec-1-3)
  - [Tests](#sec-1-4)

# Transient CLI in Python<a id="sec-1"></a>

## Motivation<a id="sec-1-1"></a>

-   Magit is an awesome tool to interact with git in emacs
-   It has a great interface using transient states
-   It relies on the `transient` library in emacs (<https://magit.vc/manual/transient/>)
-   Emacs is not used by everyone and there are no libraries implementing similar transient CLIs in python

## Definition<a id="sec-1-2"></a>

-   pytransient is a python tool to help you build interactive user interfaces in the terminal
-   pytransient wraps around existing CLI
-   pytransient is not a replacement for click, fire, docopt, argparse, etc

## Architecture<a id="sec-1-3"></a>

-   use pynput to listen to keyboard

## Tests<a id="sec-1-4"></a>

```python
from blessed import Terminal

term = Terminal()

def group(term, s):
  print("::" + term.bold(s) + "::")

with term.location(0, term.height - 1):
  group(term, "Test")
```
