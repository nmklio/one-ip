#!/usr/bin/env python3
"""修复 AI 页/CDN 页的出口与节点读取（缩进无关，幂等）。
1) ai/index.tsx        —— 「Cloudflare」对照出口改用同源 /api/me
2) gpt/api.ts, claude/api.ts —— 同上
3) cdn/providers.ts    —— Cloudflare 节点改用同源 /cdn-cgi/trace
4) ai/network-check.tsx —— 无 traceDomain 的域名也尝试直接 trace
"""
import os
import re
import sys

changed = []


def sub_file(path, pattern, repl, label, count=1):
    if not os.path.exists(path):
        print(f"  ! 缺少 {path}")
        return
    src = open(path, encoding="utf-8").read()
    new, n = re.subn(pattern, repl, src, count=count, flags=re.M)
    if n == 0:
        print(f"  {path}: 未匹配/已应用（{label}）")
        return
    if new == src:
        print(f"  {path}: 无变化（{label}）")
        return
    open(path, "w", encoding="utf-8").write(new)
    print(f"  {path}: 已修改（{label}）")
    changed.append(path)


# ---------- 1. AI 页对照出口 ----------
p = "src/views/ai/index.tsx"
sub_file(
    p,
    r'^import \{ getGeo, getDomesticIp \} from "@/views/home/api";$',
    'import { getGeo, getDomesticIp, getMyIp } from "@/views/home/api";',
    "导入 getMyIp",
)
sub_file(
    p,
    r'^(?P<i>[ \t]*)const cf = useQuery\(\{\n'
    r'(?P=i)  queryKey: \["cf-exit"\],\n'
    r'(?P=i)  queryFn: \([^\n]*\) => trace\("1\.1\.1\.1", signal\),\n'
    r'(?P=i)  retry: false,\n'
    r'(?P=i)\}\);',
    lambda m: (
        f'{m.group("i")}const cf = useQuery({{\n'
        f'{m.group("i")}  queryKey: ["cf-exit"],\n'
        f'{m.group("i")}  // 1.1.1.1 在部分网络（尤其国内）不可达，改用同源的 Worker 接口，\n'
        f'{m.group("i")}  // 它同样由 Cloudflare 边缘返回访客 IP。\n'
        f'{m.group("i")}  queryFn: ({{ signal }}) => getMyIp(signal),\n'
        f'{m.group("i")}  retry: false,\n'
        f'{m.group("i")}}})'
    ),
    "Cloudflare 对照出口改走 /api/me",
)

# ---------- 2. gpt / claude api ----------
for p in ("src/views/gpt/api.ts", "src/views/claude/api.ts"):
    sub_file(
        p,
        r'^(?P<i>[ \t]*)cloudflare: \(signal: AbortSignal\) => trace\("1\.1\.1\.1", signal\),$',
        lambda m: (
            f'{m.group("i")}// 1.1.1.1 在部分网络不可达；改走同源 Worker 接口（同样由 Cloudflare 边缘返回访客 IP）。\n'
            f'{m.group("i")}cloudflare: (signal: AbortSignal) =>\n'
            f'{m.group("i")}  endpoint<Geo>("/me", {{ signal }}),'
        ),
        "Cloudflare 出口改走 /api/me",
    )

# ---------- 3. CDN 页 Cloudflare 节点 ----------
p = "src/views/cdn/providers.ts"
sub_file(
    p,
    r'^(?P<i>[ \t]*)url: "https://www\.cloudflare\.com/cdn-cgi/trace",$',
    lambda m: (
        f'{m.group("i")}// 同源读取：本站由 Cloudflare 边缘提供服务，/cdn-cgi/trace 可直接拿到 colo。\n'
        f'{m.group("i")}url: "/cdn-cgi/trace",'
    ),
    "Cloudflare 节点改同源 trace",
)

# ---------- 4. network-check ----------
p = "src/views/ai/network-check.tsx"
sub_file(
    p,
    r'^(?P<i>[ \t]*)enabled: Boolean\(platform\?\.traceDomain\),$',
    lambda m: f'{m.group("i")}// 无 traceDomain 的域名也直接尝试 trace，读不到再标注跨域不可读。\n'
              f'{m.group("i")}enabled: true,',
    "启用全部 trace",
)
sub_file(
    p,
    r'^(?P<i>[ \t]*)trace\(platform!\.traceDomain!, signal\),$',
    lambda m: f'{m.group("i")}trace(platforms[index]?.traceDomain ?? domains[index], signal),',
    "trace 目标改为域名兜底",
)
sub_file(
    p,
    r'^(?P<i>[ \t]*)\{!platforms\.find\(\(item\) => item\?\.domain === domain\)[\s\S]*?\{t\("暂不可用"\)\}[\s\n]*</span>[\s\n]*\)\}',
    lambda m: (
        f'{m.group("i")}{{exit.isFetching ? (\n'
        f'{m.group("i")}  <Pending>{{t("检测中…")}}</Pending>\n'
        f'{m.group("i")}) : exit.data?.ip ? (\n'
        f'{m.group("i")}  <IpText ip={{exit.data.ip}} />\n'
        f'{m.group("i")}) : (\n'
        f'{m.group("i")}  <span\n'
        f'{m.group("i")}    title={{t(\n'
        f'{m.group("i")}      "该站点未提供可跨域读取的出口接口，仅能测量延迟。",\n'
        f'{m.group("i")}    )}}\n'
        f'{m.group("i")}  >\n'
        f'{m.group("i")}    {{t("跨域不可读")}}\n'
        f'{m.group("i")}  </span>\n'
        f'{m.group("i")})}}'
    ),
    "渲染逻辑调整",
)
sub_file(
    p,
    r'^(?P<i>[ \t]*)\.filter\(\(_, index\) => platforms\[index\]\?\.traceDomain\)\n'
    r'(?P=i)\.map\(\(exit\) => exit\.refetch\(\)\),$',
    lambda m: f'{m.group("i")}.map((exit) => exit.refetch()),',
    "刷新时一并重查出口",
)

print()
print("  改动文件:", changed if changed else "无")
sys.exit(0)
