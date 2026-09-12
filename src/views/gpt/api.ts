import { endpoint, trace } from "@/lib/network";
import type { Geo } from "@/lib/types";
import { getDomesticIp } from "@/views/home/api";

export const gptApi = {
  domestic: getDomesticIp,
  // 1.1.1.1 在部分网络不可达；改走同源 Worker 接口（同样由 Cloudflare 边缘返回访客 IP）。
  cloudflare: (signal: AbortSignal) => endpoint<Geo>("/me", { signal }),
  exit: (signal: AbortSignal) => trace("chatgpt.com", signal),
  geo: (ip: string, signal: AbortSignal) =>
    endpoint<Geo>(`/geoip/${encodeURIComponent(ip)}`, { signal }),
};
