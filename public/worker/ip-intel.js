import { publicIp } from "./http.js";

// 公开 DNSBL（免密钥），通过 DoH 实时查询，用于补齐「蜜罐黑名单」字段。
const ZONES = [
  { zone: "dnsbl.dronebl.org", name: "DroneBL" },
  { zone: "dnsbl.sorbs.net", name: "SORBS" },
  { zone: "bl.spamcop.net", name: "SpamCop" },
  { zone: "all.s5h.net", name: "S5H" },
];

const DOH = "https://cloudflare-dns.com/dns-query";

function reverseNibblesV6(value) {
  let address = value.split("/")[0];
  if (address.includes("::")) {
    const [left, right] = address.split("::");
    const l = left ? left.split(":").filter(Boolean) : [];
    const r = right ? right.split(":").filter(Boolean) : [];
    const middle = Array(8 - l.length - r.length).fill("0");
    address = [...l, ...middle, ...r]
      .map((group) => group.padStart(4, "0"))
      .join("");
  } else {
    address = address
      .split(":")
      .map((group) => group.padStart(4, "0"))
      .join("");
  }
  return address.split("").reverse().join(".");
}

async function listedIn(ip, zone) {
  const reversed = ip.includes(":")
    ? reverseNibblesV6(ip)
    : ip.split(".").reverse().join(".");
  const query = `${reversed}.${zone}`;
  try {
    const response = await fetch(
      `${DOH}?name=${encodeURIComponent(query)}&type=A`,
      { headers: { accept: "application/dns-json" } },
    );
    if (!response.ok) return { zone, listed: null };
    const data = await response.json();
    const answer = (data.Answer ?? []).find(
      (record) => record.type === 1 && /^127\./.test(String(record.data)),
    );
    return {
      zone,
      listed: Boolean(answer),
      record: answer ? String(answer.data) : undefined,
    };
  } catch {
    return { zone, listed: null };
  }
}

export async function ipIntel(request) {
  const url = new URL(request.url);
  const target = url.searchParams.get("ip");
  const ip = publicIp(target ?? request.headers.get("CF-Connecting-IP"));

  // 结果缓存 30 分钟：同一 IP 的黑名单状态不会频繁变化。
  const cacheKey = new Request(`https://${url.host}/__ip_intel__/${ip}`, {
    method: "GET",
  });
  const cache = caches.default;
  try {
    const cached = await cache.match(cacheKey);
    if (cached) return cached;
  } catch {
    // 预览环境可能没有 Cache API，忽略。
  }

  const results = await Promise.all(
    ZONES.map(async (zone) => ({
      name: zone.name,
      zone: zone.zone,
      ...(await listedIn(ip, zone.zone)),
    })),
  );
  const listed = results.filter((result) => result.listed === true);
  const payload = {
    ip,
    source: "公开 DNSBL（DroneBL / SORBS / SpamCop / S5H，经 DoH 实时查询）",
    checked_at: new Date().toISOString(),
    zones: results,
    listed_count: listed.length,
    listed_names: listed.map((result) => result.name),
    records: listed.map((result) => result.record).filter(Boolean),
  };
  const response = new Response(JSON.stringify(payload), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=1800",
      "X-Content-Type-Options": "nosniff",
    },
  });
  try {
    await cache.put(cacheKey, response.clone());
  } catch {
    // 忽略缓存写入失败。
  }
  return response;
}
