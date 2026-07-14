#!/usr/bin/env python3
"""Fix Step 2: Remove Authorization header from WebSocket connection"""
filepath = '/Users/mac/FishPool/fishpool/adapters/qq_official_adapter.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

# Lines 262-266 (0-indexed: 261-265) - replace with empty headers
new_block = [
    "                # QQ 官方 API v2 的 WebSocket 连接不需要在 Header 中携带 Authorization\n",
    "                # 鉴权信息在 IDENTIFY 消息体内发送\n",
    "                headers = {}\n",
    "\n",
]
lines[261:266] = new_block

with open(filepath, 'w') as f:
    f.writelines(lines)

print("✅ Step 2 done")
