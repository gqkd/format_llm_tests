"""
Render canonical content as deterministic block-style YAML.

Input: Canonical content objects.

Processing: Converts content to plain Python data and serializes without flow style or key sorting.

Output: YAML text.
"""

from __future__ import annotations

import yaml

from templating.canonical import CanonicalContent, Format, Renderer
from templating.renderers._helpers import content_to_data


class YamlRenderer(Renderer):
    format = Format.YAML

    def render(self, canonical_content: CanonicalContent) -> str:
        return yaml.safe_dump(
            content_to_data(canonical_content),
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ).rstrip()
