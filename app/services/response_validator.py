from __future__ import annotations

import json


class ResponseValidator:
    def validate(self, content: str, response_format: str) -> tuple[str, bool | None]:
        if response_format == 'text':
            return content, None
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return json.dumps(parsed, ensure_ascii=False), True
            return json.dumps({'result': parsed}, ensure_ascii=False), True
        except Exception:
            wrapped = json.dumps({'result': content}, ensure_ascii=False)
            return wrapped, False
