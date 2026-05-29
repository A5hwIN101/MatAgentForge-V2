import json
from datetime import datetime, timezone
from typing import Any

from app.schemas.sse import SSEEvent


class SSEEmitter:
    @staticmethod
    def build_event(
        *,
        event: str,
        chat_id: str,
        run_id: str,
        data: dict[str, Any],
    ) -> str:
        payload = SSEEvent(
            event=event,
            chat_id=chat_id,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
        )
        return f"data: {json.dumps(payload.model_dump(mode='json'))}\n\n"
