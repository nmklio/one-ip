#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复「AI 访问」出口 IP 探测：
1. 给支持 Cloudflare trace 的站点补上 traceDomain（Kimi）
2. 对无法跨域读取的站点，界面从“暂不可用”改为明确的“跨域不可读”
"""
import json, os, sys

def patch_platforms():
    p = 'src/views/ai/platforms.ts'
    if not os.path.exists(p):
        print('  ! platforms.ts 不存在'); return
    s = open(p, encoding='utf-8').read()
    if 'traceDomain: "www.kimi.com"' in s:
        print('  platforms.ts: Kimi 已配置，跳过'); return
    # Kimi 条目补 traceDomain
    old = '''  {
    id: "kimi",
    apiUrl: "https://api.moonshot.cn/v1",'''
    new = '''  {
    id: "kimi",
    traceDomain: "www.kimi.com",
    apiUrl: "https://api.moonshot.cn/v1",'''
    if old in s:
        s = s.replace(old, new, 1)
        open(p, 'w', encoding='utf-8').write(s)
        print('  platforms.ts: 已为 Kimi 添加 traceDomain')
    else:
        print('  ! platforms.ts 未找到 kimi 条目')

def patch_network_check():
    p = 'src/views/ai/network-check.tsx'
    if not os.path.exists(p):
        print('  ! network-check.tsx 不存在'); return
    s = open(p, encoding='utf-8').read()
    if '跨域不可读' in s and 'platforms.find((item) => item?.domain === domain)' in s:
        print('  network-check.tsx: 已修复，跳过'); return
    old = '''                    {exit.isFetching ? (
                      <Pending>{t("检测中…")}</Pending>
                    ) : exit.data?.ip ? (
                      <IpText ip={exit.data.ip} />
                    ) : (
                      <span title={t("未获取到出口，可能受跨域或连接限制。")}>
                        {t("暂不可用")}
                      </span>
                    )}'''
    new = '''                    {!platforms.find((item) => item?.domain === domain)
                      ?.traceDomain ? (
                      <span
                        title={t(
                          "该站点未提供可跨域读取的出口接口，仅能测量延迟。",
                        )}
                      >
                        {t("跨域不可读")}
                      </span>
                    ) : exit.isFetching ? (
                      <Pending>{t("检测中…")}</Pending>
                    ) : exit.data?.ip ? (
                      <IpText ip={exit.data.ip} />
                    ) : (
                      <span title={t("未获取到出口，可能受跨域或连接限制。")}>
                        {t("暂不可用")}
                      </span>
                    )}'''
    if old in s:
        s = s.replace(old, new, 1)
        open(p, 'w', encoding='utf-8').write(s)
        print('  network-check.tsx: 已区分“跨域不可读”')
    elif '!platform?.traceDomain' in s:
        s = s.replace('!platform?.traceDomain', '!platforms.find((item) => item?.domain === domain)?.traceDomain', 1)
        open(p, 'w', encoding='utf-8').write(s)
        print('  network-check.tsx: 已修正变量引用')
    else:
        print('  ! network-check.tsx 未匹配到目标片段')

def patch_i18n():
    p = 'src/i18n/en.json'
    if not os.path.exists(p):
        print('  ! en.json 不存在'); return
    en = json.load(open(p, encoding='utf-8'))
    additions = {
        '跨域不可读': 'Not readable cross-origin',
        '该站点未提供可跨域读取的出口接口，仅能测量延迟。':
            'This site does not expose a cross-origin readable egress endpoint; only latency can be measured.',
    }
    changed = 0
    for k, v in additions.items():
        if en.get(k) != v:
            en[k] = v
            changed += 1
    if changed:
        json.dump(en, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'  en.json: 新增 {changed} 条翻译')
    else:
        print('  en.json: 已是最新')

if __name__ == '__main__':
    print('  修补 platforms.ts'); patch_platforms()
    print('  修补 network-check.tsx'); patch_network_check()
    print('  修补 i18n'); patch_i18n()
