import asyncio
import json
import ssl
from urllib.parse import urlparse

import websockets


def get_esphome_version(url):
    parsed = urlparse(url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{scheme}://{parsed.netloc}/ws"

    async def _read_version():
        ssl_ctx = ssl._create_unverified_context() if scheme == "wss" else None
        async with websockets.connect(ws_url, ssl=ssl_ctx, open_timeout=10) as ws:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                if "esphome_version" in data:
                    return data["esphome_version"]

    try:
        return asyncio.run(_read_version())
    except Exception as e:
        print(f"  ESPHome: Could not get version: {e}")
        return None
