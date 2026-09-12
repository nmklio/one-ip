import { publicIp, upstream } from "./http.js";

export function cfGeo(request) {
  const cf = request.cf ?? {};
  return {
    ip: request.headers.get("CF-Connecting-IP") ?? "",
    country: cf.country,
    country_code: cf.country,
    region: cf.region,
    city: cf.city,
    isp: cf.asOrganization,
    asn: cf.asn,
    latitude: cf.latitude ? Number(cf.latitude) : undefined,
    longitude: cf.longitude ? Number(cf.longitude) : undefined,
    timezone: cf.timezone,
    source: "Cloudflare request.cf",
  };
}
export async function geoIp(ip) {
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
const BROWSER_UA =
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
  );
  if (!data.ip) throw new Error("第二归属地数据源未返回结果");
  return {
    ip: data.ip,
    country: data.country,
    country_code: data.country_code,
    city: data.city,
    isp: data.isp,
    asn: data.asn,
    latitude: data.latitude,
    longitude: data.longitude,
    source: "ip.sb",
  };
}
