#!/usr/bin/env bash
# 对 one-ip 仓库应用本站全部自定义（幂等，可重复执行）
# 用法：在仓库根目录执行 bash apply-custom.sh
set -u
cd "$(dirname "$0")"

echo '=== [1/5] 页脚精简：只保留 © 年份 IP · API ==='
python3 - <<'PYEOF'
import re, sys, os
p = 'src/layout/index.tsx'
if not os.path.exists(p):
    print('  ! 缺少 src/layout/index.tsx'); sys.exit(0)
s = open(p, encoding='utf-8').read()
new_footer = '''        <footer className="app-footer">
          © {new Date().getFullYear()} IP ·{" "}
          <UnderlineHover asChild>
            <Link to="/docs/api">API</Link>
          </UnderlineHover>
        </footer>'''
pat = re.compile(r'[ \t]*<footer className="app-footer">[\s\S]*?</footer>', re.M)
s2, n = pat.subn(new_footer, s, count=1)
if n and s2 != s:
    open(p, 'w', encoding='utf-8').write(s2)
    print('  页脚已精简')
else:
    print('  页脚无需修改' if n else '  ! 未找到 footer')
PYEOF

echo '=== [2/5] Telegram 状态接入（可达性检测）==='
python3 - <<'PYEOF'
import json, os
NEW_NOTE_ZH = '非官方检测：通过 Telegram Bot API 可达性判断，仅供参考，不代表官方状态。'
NEW_NOTE_EN = 'Unofficial check: based on Telegram Bot API reachability, for reference only; not an official status feed.'
p1 = 'src/views/status/services.json'
if os.path.exists(p1):
    d = json.load(open(p1, encoding='utf-8'))
    changed = False
    for s in d:
        if s.get('id') == 'telegram':
            if s.get('url') != 'https://api.telegram.org' or s.get('note') != NEW_NOTE_ZH:
                s['url'] = 'https://api.telegram.org'
                s['note'] = NEW_NOTE_ZH
                changed = True
    json.dump(d, open(p1, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('  services.json:', '已更新' if changed else '无需修改')
p3 = 'src/i18n/en.json'
if os.path.exists(p3):
    en = json.load(open(p3, encoding='utf-8'))
    if en.get(NEW_NOTE_ZH) != NEW_NOTE_EN:
        en[NEW_NOTE_ZH] = NEW_NOTE_EN
        json.dump(en, open(p3, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('  en.json: 已补充翻译')
PYEOF

echo '=== [3/5] 品牌名统一为 Miao IPsec ==='
python3 - <<'PYEOF'
import json, os
OLD_MAIN = 'IP 网络工具概览'
OLD = 'IP 网络工具'
NEW = 'Miao IPsec'
files = ['index.html', 'src/layout/index.tsx', 'src/i18n/index.ts',
         'src/views/link/exits.tsx', 'src/views/link/index.tsx',
         'src/views/home/index.tsx', 'src/views/ping/index.tsx']
for rel in files:
    if not os.path.exists(rel):
        continue
    s = open(rel, encoding='utf-8').read()
    s2 = s.replace(OLD_MAIN, NEW).replace(OLD, NEW)
    if s2 != s:
        open(rel, 'w', encoding='utf-8').write(s2)
        print('  已重命名:', rel)
p = 'index.html'
if os.path.exists(p):
    s = open(p, encoding='utf-8').read()
    if '<title>IP 查询与网络诊断</title>' in s:
        open(p, 'w', encoding='utf-8').write(s.replace('<title>IP 查询与网络诊断</title>', f'<title>{NEW}</title>'))
        print('  index.html 标题已更新')
p = 'src/i18n/en.json'
if os.path.exists(p):
    en = json.load(open(p, encoding='utf-8'))
    out, changed = {}, 0
    for k, v in en.items():
        nk = k.replace(OLD_MAIN, NEW).replace(OLD, NEW)
        nv = v.replace('IP Tools overview', NEW).replace('IP Tools', NEW) if isinstance(v, str) else v
        if nk != k or nv != v:
            changed += 1
        out[nk] = nv
    if changed:
        json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'  en.json: 更新 {changed} 条')
PYEOF

echo '=== [4/5] AI 出口探测修复 ==='
if [ -f patch-ai-egress.py ]; then
  python3 patch-ai-egress.py
else
  echo '  ! 缺少 patch-ai-egress.py'
fi

echo '=== [5/5] 站点图标替换 ==='
if [ -f assets/miao-icon.jpg ]; then
  python3 - <<'PYEOF'
import base64, os
icon = 'assets/miao-icon.jpg'
b64 = base64.b64encode(open(icon, 'rb').read()).decode()
svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
       'viewBox="0 0 256 256"><image width="256" height="256" '
       f'xlink:href="data:image/jpeg;base64,{b64}"/></svg>')
for p in ['public/favicon.svg', 'public/icon.svg', 'public/icon-knockout.svg']:
    if os.path.isdir(os.path.dirname(p)):
        open(p, 'w', encoding='utf-8').write(svg)
        print('  已替换:', p)
# index.html 引用不变（/favicon.svg）
PYEOF
else
  echo '  ! 缺少 assets/miao-icon.jpg，跳过图标替换'
fi

echo '=== [6/6] Worker 内置 Telegram 可达性接口 ==='
python3 - <<'PYEOF'
import os
p = 'public/worker/index.js'
if not os.path.exists(p):
    print('  ! 缺少 public/worker/index.js')
else:
    s = open(p, encoding='utf-8').read()
    if '"/status/telegram"' in s:
        print('  已存在 Telegram 接口，跳过')
    else:
        anchor = '      if (path.startsWith("/status/")) {'
        block = '''      if (path === "/status/telegram") {
        try {
          const res = await fetch(
            "https://api.telegram.org/bot0:invalid/getMe",
            {
              headers: { accept: "application/json" },
              cf: { cacheTtl: 60 },
            },
          );
          const text = await res.text();
          const reachable =
            res.status === 401 || /"ok"\\s*:\\s*(true|false)/.test(text);
          return json({
            status: {
              indicator: reachable ? "none" : "minor",
              description: reachable
                ? "API 可达（非官方检测）"
                : "响应异常（非官方检测）",
            },
            incidents: [],
            fetchedAt: new Date().toISOString(),
            source: "https://api.telegram.org (reachability)",
          });
        } catch {
          return json({
            status: {
              indicator: "critical",
              description: "API 不可达（非官方检测）",
            },
            incidents: [],
            fetchedAt: new Date().toISOString(),
            source: "https://api.telegram.org (reachability)",
          });
        }
      }
'''
        if anchor in s:
            s = s.replace(anchor, block + anchor, 1)
            open(p, 'w', encoding='utf-8').write(s)
            print('  已插入 /status/telegram 分支')
        else:
            print('  ! 未找到插入锚点')
PYEOF

echo '=== [7/7] 补充 Telegram 状态相关英文翻译 ==='
python3 - <<'PYEOF'
import json, os
p = 'src/i18n/en.json'
if not os.path.exists(p):
    print('  ! 缺少 en.json')
else:
    en = json.load(open(p, encoding='utf-8'))
    additions = {
        'API 可达（非官方检测）': 'API reachable (unofficial check)',
        '响应异常（非官方检测）': 'Abnormal response (unofficial check)',
        'API 不可达（非官方检测）': 'API unreachable (unofficial check)',
    }
    changed = 0
    for k, v in additions.items():
        if en.get(k) != v:
            en[k] = v
            changed += 1
    if changed:
        json.dump(en, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'  已新增 {changed} 条')
    else:
        print('  无需修改')
PYEOF

echo '=== [8/8] 归属地查询修复（并发竞速 + 兜底源）==='
if [ -f patch-geo-fallback.py ]; then
  python3 patch-geo-fallback.py
else
  echo '  ! 缺少 patch-geo-fallback.py'
fi

echo '=== 自定义应用完成 ==='
