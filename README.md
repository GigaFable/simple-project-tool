# Simple Project Tool

This is a simple project planning utility that generates
[Mermaid](https://mermaid.js.org/intro/) diagrams from projects defined as YAML
files. Mermaid diagrams are widely rendered by Markdown readers or you can use a
specialised viewer (such as
[Mermaid Preview](https://marketplace.visualstudio.com/items?itemName=vstirbu.vscode-mermaid-preview)
for [VS Code](https://code.visualstudio.com/)). It also has the ability to
suggest the order you do tasks (called stages by the utility) in.

# Getting Started

This app requires [Python](https://www.python.org/). You can install python from
the projects home page.

Once you have python you need to setup a virtual environment and install the
requirements like this (executed from this projects home directory):

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

You can now run `python spt.py` to test the program.

# Installation (Ubuntu/Debian)

The recommended way to install this app is with `pipx`. You can do that as
follows:

## Ubuntu/Debian

```bash
sudo apt install python3 pip pipx
pipx install .
pipx ensurepath
. ~/.bashrc
```

## Windows

If you installed python from the Windows store you can do this:

```powershell
python3 -m pip install --user pipx
python -m pipx ensurepath
```

Then restart your terminal session. If you are using another app to launch your
terminal sessions you will need to restart that before restarting your terminal
session. You can logout/login as an easy fix if the next stage fails due to not
finding pipx.

## After installing pipx

From the project directory

```bash
pipx install .
```

This will allow you to call the program as `spt` from your shell.

# Usage

The following assumes you have installed `spt` into your shell. If you haven't,
wherever it says `spt` replace the command with `python /path/to/spt.py`.

To use the package in it's most basic form, invoke the command with:

```bash
spt >project.mmd
```

This will read `project.yaml` from the current directory and spit out a mermaid
diagram to the file `project.mmd`.

Another useful choice is:

```bash
spt -o # Suggests an order of work
```

Which will output a suggested order of work for you to do, respecting stage
dependencies.

You can specify an alternative file to `project.yaml` on the command line by
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
of this document but you can get a feel for it with this example below. The
project is defined at the root level with the following keys:

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
    priority: 1 # Higher numbered stages are prioritised in the work order
  - title: Another stage, can be executed without finishing the previous stage
    depends_on:
      - Second required stage # Second required stage must be completed first
```

If you copy and paste that into a YAML file then feed it to the tool it will
output a mermaid diagram for you.

## A little bit on the `priority` key

Priorities work with higher numbers being assigned greater priority and that the
stage with priority 1 (being the only priority set) is the highest priority task
in the project.

You don't really need to think about this but if you don't assign a priority to
a stage it is treated as having priority `-1` if it's a stage with no sub-stages
and `0` if it has sub-stages.

---

That's basically it. Give it a try, generate that YAML as a mermaid diagram and
you can expand upon it to define your project! Every stage can also have
`stages` and/or `parallel_stages` keys of their own.

You could also examine the included `project.yaml`, which was used to self-plan
this tool to a working stage.
