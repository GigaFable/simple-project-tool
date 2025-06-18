# Simple Project Tool

This is a simple project planning utility that generates
[Mermaid](https://mermaid.js.org/intro/) diagrams from projects defined as YAML
files. Mermaid diagrams are widely rendered by Markdown readers or you can use a
specialised viewer (such as
[Mermaid Preview](https://marketplace.visualstudio.com/items?itemName=vstirbu.vscode-mermaid-preview)
for [VS Code](https://code.visualstudio.com/)). It also has the ability to
suggest the order you do tasks (called stages by the utility) in.

# Installation

Installation requires [Python](https://www.python.org/). You can install python
from the projects home page.

Once you have python you need to setup a virtual environment and install the
requirements like this (executed from this projects home directory):

## Recommended method

```bash
python3 -m venv .venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install .
```

This will allow you to run the utility by calling `spt` whenever you activate
the virtual environment from the project directory using:

```bash
source .venv/bin/activate # On Windows: .venv\Scripts\activate
```

To deactivate the python virtual environment run

```bash
deactivate
```

## Alternative method

If you prefer, you can install the tool to your users environment so you don't
have to deal with activating and deactivating the tool with:

```bash
pip install --user setuptools
pip install --user .
```

This assumes you have pip and python installed. You can refer to the python
projects home page to get those installed.

# Usage

To use the package in it's most basic form, invoke the command with:

```bash
spt >project.mmd
```

This will read project.yaml from the current directory and spit out a mermaid
diagram to the file project.mmd.

Another useful choice is:

```bash
spt -o # Suggests an order of work
```

Which will output a suggested order of work for you to do, respecting stage
dependencies.

You can specify an alternative file to project.yaml on the command line by
providing it as an argument to spt, such as:

```bash
spt awesome.yaml
# or
spt -o awesome.yaml
```

There are a few undocumented features, you can get help on them with:

```bash
spt --help
```

# Configuration

You define your project in YAML format. The syntax of YAML is beyond the scope
of this document but you can get a feel for it by examining the included
project.yaml, which was used to self-plan this tool. The project is defined at
the root level with the following keys:

```yaml
title: My Awesome Project # This is the only required key
description: A longer description about what Awesome Project does
stages: # These stages each depend on the previous stage being completed
  - title: First required stage for Awesome Project
    description: This is more about the stage # Optional
  - title: Second required stage # to be completed after the first stage
    complete: true # Complete stages are filled with colour in the diagram
    milestone: true # This stage looks different in the diagram
parallel_stages: # These stages can be completed in any order
  - title: Required stage that can be executed in any order
  - title: Another stage, can be executed without finishing the previous stage
    depends_on:
      - Second required stage # Second required stage must be completed first
```

If you copy and paste that into a YAML file then feed it to the tool it will
output a mermaid diagram for you.

That's basically it. Give it a try, generate that YAML as a mermaid diagram and
you can expand upon it to define your project! Every stage can also have
`stages` and/or `parallel_stages` keys of their own.
