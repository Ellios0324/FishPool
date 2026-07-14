#!/usr/bin/env python3
"""Fix Step 3a: Add self._access_token attribute"""
filepath = '/Users/mac/FishPool/fishpool/adapters/qq_official_adapter.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

# Find the line with self._identified: bool
for i, line in enumerate(lines):
    if 'self._identified: bool' in line:
        # Insert after this line
        lines.insert(i + 1, "        self._access_token: Optional[str] = None  # 从 app_secret 换取的真实令牌\n")
        break

with open(filepath, 'w') as f:
    f.writelines(lines)
print("✅ Step 3a done")
