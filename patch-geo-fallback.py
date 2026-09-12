#!/usr/bin/env python3
"""修复归属地查询：
1) src/views/home/api.ts —— 两个数据源并发竞速 + 8 秒预算 + Worker 兜底
2) public/worker/geo.js  —— Worker 侧 ipwho.is 被限流时回落到 ip.sb（带浏览器 UA）
幂等：已打过补丁会跳过。
"""
import os
import re
import sys

changed = []

# ---------- 1. 前端 getGeo ----------
p1 = "src/views/home/api.ts"
if os.path.exists(p1):
    src = open(p1, encoding="utf-8").read()
    if "Promise.any([ipSb, ipWho])" in src:
        print("  api.ts: 已是补丁版本，跳过")
    elif re.search(r"export async function getGeo\(", src):
        new_block = '''export async function getGeo(
  ip: string,
  signal?: AbortSignal,
  timeoutMs = 8000,
): Promise<Geo> {
  const timeout = AbortSignal.timeout(timeoutMs);
  const merged = signal ? AbortSignal.any([signal, timeout]) : timeout;
  // 两个数据源并发查询，谁先返回有效结果用谁：单个数据源可能被限流或响应很慢，
  // 串行等待会让兜底源失去时间窗口，整块归属信息直接不可用。
  const ipSb = (async () => {
    const data = await request<Geo>(
      `https://api.ip.sb/geoip/${encodeURIComponent(ip)}`,
      { signal: merged },
    );
    if (!data.ip || (!data.country && !data.isp))
      throw new Error(t("归属信息不完整"));
    return { ...data, ip, source: "ip.sb" };
  })();
  const ipWho = (async () => {
    const data = await request<{
      success: boolean;
      country?: string;
      country_code?: string;
      region?: string;
      city?: string;
      connection?: { isp?: string; asn?: number };
      latitude?: number;
      longitude?: number;
      timezone?: { id?: string };
    }>(`https://ipwho.is/${encodeURIComponent(ip)}`, { signal: merged });
    if (!data.success) throw new Error(t("归属信息暂不可用，请稍后重试"));
    return {
      ip,
      country: data.country,
      country_code: data.country_code,
      region: data.region,
      city: data.city,
      isp: data.connection?.isp,
      asn: data.connection?.asn,
      latitude: data.latitude,
      longitude: data.longitude,
      timezone: data.timezone?.id,
      source: "ipwho.is",
    };
  })();
  try {
    return await Promise.any([ipSb, ipWho]);
  } catch {
    merged.throwIfAborted();
    // 浏览器侧两个源都失败（本地网络限制或数据源限流）时，再走本站 Worker 兜底。
    try {
      return await endpoint<Geo>(`/geoip/${encodeURIComponent(ip)}`, {
        signal: merged,
      });
    } catch {
      merged.throwIfAborted();
      throw new Error(t("归属信息暂不可用，请稍后重试"));
    }
  }
}
'''
        src2, n = re.subn(
            r"export async function getGeo\(\n.*?\n\}\n",
            new_block,
            src,
            count=1,
            flags=re.S,
        )
        if n:
            open(p1, "w", encoding="utf-8").write(src2)
            print("  api.ts: 已改写 getGeo（并发竞速 + Worker 兜底）")
            changed.append(p1)
        else:
            print("  api.ts: 未匹配到 getGeo，跳过")
else:
    print("  ! 缺少", p1)

# ---------- 2. Worker geo.js ----------
p2 = "public/worker/geo.js"
if os.path.exists(p2):
    src = open(p2, encoding="utf-8").read()
    if "BROWSER_UA" in src:
        print("  geo.js: 已是补丁版本，跳过")
    else:
        # 2a. 给 secondaryGeo 带上浏览器 UA（ip.sb 会按 UA 拦截）
        old_sec = '''export async function secondaryGeo(ip) {
  publicIp(ip);
  const data = await upstream(
    `https://api.ip.sb/geoip/${encodeURIComponent(ip)}`,
  );'''
        new_sec = '''const BROWSER_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

export async function secondaryGeo(ip) {
  publicIp(ip);
  const data = await upstream(
    `https://api.ip.sb/geoip/${encodeURIComponent(ip)}`,
    {
      headers: {
        "User-Agent": BROWSER_UA,
        Accept: "application/json",
      },
    },
  );'''
        n1 = src.count(old_sec)
        if n1:
            src = src.replace(old_sec, new_sec, 1)

        # 2b. geoIp 失败时回落 secondaryGeo
        old_geo = re.search(r"export async function geoIp\(ip\) \{\n.*?\n\}\n", src, re.S)
        if old_geo:
            new_geo = '''export async function geoIp(ip) {
  publicIp(ip);
  try {
    const data = await upstream(`https://ipwho.is/${encodeURIComponent(ip)}`);
    if (!data.success) throw new Error("IP 归属地数据源未返回有效结果");
    return {
      ip: data.ip,
      country: data.country,
      country_code: data.country_code,
      region: data.region,
      city: data.city,
      isp: data.connection?.isp,
      asn: data.connection?.asn,
      latitude: data.latitude,
      longitude: data.longitude,
      timezone: data.timezone?.id,
      source: "ipwho.is",
    };
  } catch (error) {
    // ipwho.is 对 Worker 共享出口容易限流；回落到 ip.sb（带浏览器 UA）再试一次。
    try {
      return await secondaryGeo(ip);
    } catch {
      throw error;
    }
  }
}
'''
            src = src[: old_geo.start()] + new_geo + src[old_geo.end() :]
        if n1:
            open(p2, "w", encoding="utf-8").write(src)
            print("  geo.js: 已加入 ip.sb 兜底源（浏览器 UA）")
            changed.append(p2)
        else:
            print("  geo.js: 未匹配到 secondaryGeo，跳过")
else:
    print("  ! 缺少", p2)

print("  改动文件:", changed if changed else "无")
sys.exit(0)
