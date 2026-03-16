"""Template tree renderer with @each() loop directive.

Walks a template directory tree and renders files into an output directory.
Inspired by cookiecutter's generate.py, with an added @each(var) directive
for dynamic directory repetition.
"""

import re
from pathlib import Path

from jinja2 import Environment

EACH_PATTERN = re.compile(r"^@each\((\w+)\)$")


def render_tree(
    template_dir: Path,
    output_dir: Path,
    context: dict,
    env: Environment,
) -> None:
    """Walk template_dir and render all .j2 files into output_dir.

    - Directory names may contain Jinja expressions (e.g., ``{{package_name}}``)
      and are rendered through the environment before creation.
    - Files ending in ``.j2`` are rendered through Jinja; the suffix is stripped
      from the output filename.
    - Files that render to whitespace-only content are skipped (conditional files).
    - A directory named ``@each(var)`` triggers a loop: ``context[var]`` must be a
      dict mapping directory names to sub-context dicts.  For each key/value pair,
      a directory is created and the subtree is rendered with merged context.
    """
    for entry in sorted(template_dir.iterdir(), key=lambda e: e.name):
        if entry.is_dir():
            match = EACH_PATTERN.match(entry.name)
            if match:
                var_name = match.group(1)
                items = context.get(var_name, {})
                for dirname, sub_context in sorted(items.items()):
                    merged = {**context, **sub_context}
                    out_subdir = output_dir / dirname
                    out_subdir.mkdir(parents=True, exist_ok=True)
                    render_tree(entry, out_subdir, merged, env)
            else:
                rendered_name = env.from_string(entry.name).render(**context)
                out_subdir = output_dir / rendered_name
                out_subdir.mkdir(parents=True, exist_ok=True)
                render_tree(entry, out_subdir, context, env)

        elif entry.name.endswith(".j2"):
            output_name = env.from_string(entry.name[:-3]).render(**context)
            template = env.from_string(entry.read_text())
            content = template.render(**context)
            if content.strip():
                (output_dir / output_name).write_text(content + "\n")
