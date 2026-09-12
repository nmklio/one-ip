#!/usr/bin/env python3
"""补齐 IP 情报卡的「蜜罐黑名单 / VPN 线索」：
1) details.tsx 增加查询 /api/ip/intel（Worker 端 DNSBL 实时检测）
2) 蜜罐黑名单：显示 DNSBL 命中数（上游 rep_threat 作为兜底）
3) VPN 线索：用同源数据里的 VPN/代理/机房/移动 标记推导，上游 vpn_trace 有值一并显示
幂等：已打过补丁会跳过。
"""
import os
import re
import sys

changed = []


def sub_file(path, pattern, repl, label, count=1, flags=re.M):
    if not os.path.exists(path):
        print(f"  ! 缺少 {path}")
        return
    src = open(path, encoding="utf-8").read()
    if isinstance(repl, str) and "__I1__" in repl:
        pass
    new, n = re.subn(pattern, repl, src, count=count, flags=flags)
    if n == 0:
        print(f"  {path}: 未匹配/已应用（{label}）")
        return
    if new == src:
        print(f"  {path}: 无变化（{label}）")
        return
    open(path, "w", encoding="utf-8").write(new)
    print(f"  {path}: 已修改（{label}）")
    changed.append(path)


P = "src/views/ip/details.tsx"

# ---------- 1. 导入 ----------
# GUARD1: 幂等护栏（重复执行不再插入重复导入）
_cur = open(P, encoding="utf-8").read()
_p1 = 'import { IpText, ToolCard, DataTable, Pending } from "@/components/toolkit";'
if _p1 not in _cur:
    sub_file(
        P,
        r'^import \{ IpText, ToolCard, DataTable \} from "@/components/toolkit";$',
        _p1,
        "toolkit 导入 Pending",
    )
_p2 = 'import { endpoint } from "@/lib/network";'
if _p2 not in _cur:
    sub_file(
        P,
        r'^import type \{ ReactNode \} from "react";$',
        'import type { ReactNode } from "react";\n'
        'import { useQuery } from "@tanstack/react-query";\n'
        'import { endpoint } from "@/lib/network";',
        "新增 useQuery / endpoint 导入",
    )

# ---------- 2. intel 查询 + VPN 线索标记（插在 score 与 rpki 之间） ----------
INSERT = '''__I1__const intel = useQuery({
__I1__  queryKey: ["ip-intel-dnsbl", d.ip],
__I1__  queryFn: ({ signal }) =>
__I1__    endpoint<{
__I1__      ip: string;
__I1__      source: string;
__I1__      checked_at: string;
__I1__      zones: { name: string; listed: boolean | null; record?: string }[];
__I1__      listed_count: number;
__I1__      listed_names: string[];
__I1__    }>(`/ip/intel?ip=${encodeURIComponent(d.ip)}`, { signal }),
__I1__  staleTime: 300_000,
__I1__  retry: false,
__I1__});
__I2__// VPN 线索：同一次查询里已有布尔标记，直接推导成可读线索。
__I2__const vpnHintLabels: string[] = [];
__I2__if (d.is_vpn === true) vpnHintLabels.push(t("VPN 标记"));
__I2__if (d.is_proxy === true) vpnHintLabels.push(t("代理标记"));
__I2__if (d.is_mobile === true) vpnHintLabels.push(t("移动网络"));
__I2__if (d.is_datacenter === true)
__I2__  vpnHintLabels.push(
__I2__    d.datacenter_name
__I2__      ? `${t("数据中心")} · ${d.datacenter_name}`
__I2__      : t("数据中心"),
__I2__  );
'''
sub_file(
    P,
    r'^(?P<i>[ \t]*): null;\n(?P<j>[ \t]*)const rpki:',
    lambda m: INSERT.replace("__I1__", m.group("i")).replace("__I2__", m.group("j"))
    + f'{m.group("j")}const rpki:',
    "插入 intel 查询与 VPN 标记推导",
)

# ---------- 3. 蜜罐黑名单行 ----------
HONEYPOT = r'^(?P<i>[ \t]*)\[t\("HTTP 蜜罐黑名单"\),\n[\s\S]*?^\1\],\n'
HONEYPOT_NEW = '''__I__[t("HTTP 蜜罐黑名单"),
__I__  dnsbl.isFetching ? (
__I__    <Pending key="hb">{t("检测中…")}</Pending>
__I__  ) : dnsbl.data ? (
__I__    dnsbl.data.listed_count
__I__      ? chip(
__I__          `${t("命中")} ${dnsbl.data.listed_count}/${dnsbl.data.zones.length}（${dnsbl.data.listed_names.join("、")}）`,
__I__          "bad",
__I__        )
__I__      : chip(t("未命中（4 个公开黑名单源）"), "good")
__I__  ) : d.intelligence?.rep_threat == null ? (
__I__    chip(t("未知"))
__I__  ) : (
__I__    JSON.stringify(d.intelligence.rep_threat)
__I__  ),
__I__],
'''
sub_file(P, HONEYPOT, lambda m: HONEYPOT_NEW.replace("__I__", m.group("i")), "蜜罐黑名单行")

# ---------- 4. VPN 线索行 ----------
VPN = r'^(?P<i>[ \t]*)\[t\("VPN 线索"\),\n[\s\S]*?^\1\],\n'
VPN_NEW = '''__I__[t("VPN 线索"),
__I__  (() => {
__I__    const parts: string[] = [];
__I__    if (typeof d.vpn_trace === "string" && d.vpn_trace.trim())
__I__      parts.push(d.vpn_trace.trim());
__I__    else if (d.vpn_trace != null) parts.push(JSON.stringify(d.vpn_trace));
__I__    if (vpnHintLabels.length) parts.push(vpnHintLabels.join(" · "));
__I__    return parts.length
__I__      ? chip(parts.join(" · "), d.is_vpn || d.is_proxy ? "warn" : "neutral")
__I__      : chip(t("未发现 VPN / 代理标记"), "good");
__I__  })(),
__I__],
'''
sub_file(P, VPN, lambda m: VPN_NEW.replace("__I__", m.group("i")), "VPN 线索行")

print()
print("  改动文件:", sorted(set(changed)) if changed else "无")
sys.exit(0)
