"""
Render canonical content as deterministic JSON.

Input: Canonical content objects.

Processing: Converts content to plain Python data and serializes with fixed JSON options.

Output: JSON text.
"""

from __future__ import annotations

import json

from templating.canonical import CanonicalContent, Format, Renderer
from templating.renderers._helpers import content_to_data


class JsonRenderer(Renderer):
    format = Format.JSON

    def render(self, canonical_content: CanonicalContent) -> str:
        return json.dumps(
            content_to_data(canonical_content),
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
