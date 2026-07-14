#!/usr/bin/env python3
"""Fix Step 3b: Add _get_access_token method before _send_identify"""
filepath = '/Users/mac/FishPool/fishpool/adapters/qq_official_adapter.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

# Find the line with "async def _send_identify"
insert_before = None
for i, line in enumerate(lines):
    if 'async def _send_identify' in line:
        insert_before = i
        break

if insert_before is None:
    print("❌ Could not find _send_identify method")
    exit(1)

new_method = [
    "    async def _get_access_token(self) -> Optional[str]:\n",
    '        """\n',
    "        通过 app_id 和 app_secret 换取 access_token\n",
    "\n",
    "        QQ 官方 API v2 需要先通过此接口获取 access_token，\n",
    "        然后用 access_token 作为 WebSocket 鉴权的凭证。\n",
    "\n",
    "        POST https://sandbox.api.sgroup.qq.com/v2/app/access_token\n",
    '        Body: { "app_id": "xxx", "app_secret": "xxx" }\n',
    '        """\n',
    "        if not self._app_secret:\n",
    '            self._logger.warning("未配置 app_secret，无法获取 access_token")\n',
    "            return None\n",
    "            \n",
    '        url = f"{self._api_base}/v2/app/access_token"\n',
    "        body = {\n",
    '            "app_id": self._app_id,\n',
    '            "app_secret": self._app_secret,\n',
    "        }\n",
    "        headers = {\n",
    '            "Content-Type": "application/json",\n',
    "        }\n",
    "    \n",
    "        try:\n",
    '            self._logger.info("🔑 正在获取 access_token...")\n',
    "            async with self._session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:\n",
    "                if resp.status == 200:\n",
    "                    result = await resp.json()\n",
    '                    access_token = result.get("access_token")\n',
    "                    if access_token:\n",
    "                        self._access_token = access_token\n",
    '                        self._logger.info(f"✅ access_token 获取成功: {access_token[:20]}...")\n',
    "                        return access_token\n",
    "                    else:\n",
    '                        self._logger.error(f"❌ access_token 获取失败: 响应中无 access_token 字段: {result}")\n',
    "                else:\n",
    "                    error_text = await resp.text()\n",
    '                    self._logger.error(f"❌ access_token 获取失败 [HTTP {resp.status}]: {error_text[:200]}")\n',
    "        except Exception as e:\n",
    '            self._logger.error(f"❌ access_token 获取异常: {e}")\n',
    "    \n",
    "        return None\n",
    "\n\n",
]

# Insert before _send_identify
for line in reversed(new_method):
    lines.insert(insert_before, line)

with open(filepath, 'w') as f:
    f.writelines(lines)
print("✅ Step 3b done")
