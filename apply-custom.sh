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
python3 -c "print('  已跳过：该功能已由上游原生实现（同步后原生自带）')"

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
python3 -c "print('  已跳过：该功能已由上游原生实现（同步后原生自带）')"

echo '=== [7/7] 补充 Telegram 状态相关英文翻译 ==='
python3 -c "print('  已跳过：该功能已由上游原生实现（同步后原生自带）')"

echo '=== 自定义应用完成 ==='
