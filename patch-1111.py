#!/usr/bin/env python3
"""修复：1.1.1.1 在国内被墙，连通性检测的 Cloudflare 目标换成 www.cloudflare.com。
涉及：connectivity 组件、WebRTC 对照、链路检测目标。幂等。"""
import os
import sys

changed = []
edits = [
    ("src/components/connectivity.tsx",
     'url: "https://1.1.1.1/cdn-cgi/trace",',
     'url: "https://www.cloudflare.com/cdn-cgi/trace",'),
    ("src/views/link/targets.json",
     '"url": "https://1.1.1.1/cdn-cgi/trace"',
     '"url": "https://www.cloudflare.com/cdn-cgi/trace"'),
    ("src/views/webrtc/api.ts",
     'trace("1.1.1.1", signal).catch(() => null),',
     'trace("www.cloudflare.com", signal).catch(() => null),'),
]

for path, old, new in edits:
    if not os.path.exists(path):
        print(f"  ! 缺少 {path}")
        continue
    src = open(path, encoding="utf-8").read()
    if new in src:
        print(f"  {path}: 已应用，跳过")
        continue
    if old not in src:
        print(f"  {path}: 未匹配到目标（{path}）")
        continue
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    print(f"  {path}: 已修复")
    changed.append(path)

print()
print("  改动:", changed if changed else "无")
sys.exit(0)
