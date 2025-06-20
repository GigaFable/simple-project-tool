from setuptools import setup, find_packages

setup(
    name="simple-project-tool",
    version="1.0.2",
    packages=["simple_project_tool"],
    include_package_data=True,
    package_data={
        "simple_project_tool": ["schema.json"],
    },
    install_requires=[
        "attrs==25.3.0",
        "jsonschema==4.24.0",
        "jsonschema-specifications==2025.4.1",
        "markdown-it-py==3.0.0",
        "mdurl==0.1.2",
        "networkx==3.5",
        "Pygments==2.19.1",
        "referencing==0.36.2",
        "rich==14.0.0",
        "rpds-py==0.25.1",
        "ruamel.yaml==0.18.14",
        "ruamel.yaml.clib==0.2.12",
        "typing_extensions==4.14.0",
    ],
    entry_points={
        "console_scripts": [
            "spt=simple_project_tool.generate:main",
        ],
    },
    author="Robert Pitt",
    author_email="rob@gigafable.com",
    description="A simple project management utility that generates mermaid diagrams from YAML definitions and suggests an order of work.",
)
