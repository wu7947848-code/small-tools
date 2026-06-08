import os, re, zipfile, io

BASE = r'C:\Users\wangl\raw_data'
OUTPUT_ZIP = os.path.join(BASE, 'dify_perfect_payload.zip')

# ── 第一步：确认源码处于 Obsidian 黄金状态 ─────────

files = sorted(f for f in os.listdir(BASE) if f.endswith('.md'))
total_links = 0
nav_count = 0
for fn in files:
    path = os.path.join(BASE, fn)
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    total_links += len(re.findall(r'\[\[', c))
    if '🌐 政策拓扑链路导航' in c:
        nav_count += 1

print(f'[1] 源码检查: {len(files)} 文件, {total_links} 双链, {nav_count} 导航节')

if total_links < 150 or nav_count < 36:
    print('  !! 源码非黄金状态，请先确保 [[双链]] 和导航节完整')
    raise SystemExit(1)
print('  >> Obsidian 黄金 Vault，开始编译')

# ── 第二步：内存脱水编译 ───────────────────────────

compiled = 0
samples = []
zip_buffer = io.BytesIO()

with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    for fn in files:
        path = os.path.join(BASE, fn)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # --- 物理截断：切除 ## 🌐 政策拓扑链路导航 及之后 ---
        marker = '## 🌐 政策拓扑链路导航'
        idx = content.find(marker)
        if idx != -1:
            content = content[:idx].rstrip('\n') + '\n'

        # --- 带显示名：[[target#anchor|display]] → display（详见 target#anchor）---
        def replace_with_display(m):
            target = m.group(1)
            anchor = m.group(2) if m.group(2) else ''
            display = m.group(3)
            return f'{display}（详见 {target}{anchor}）'

        content = re.sub(
            r'\[\[([^\]|#]+)(#[^\]|]*)?\|([^\]]+)\]\]',
            replace_with_display,
            content
        )

        # --- 裸双链：[[target#anchor]] → target#anchor ---
        content = re.sub(
            r'\[\[([^\]]+?)\]\]',
            r'\1',
            content
        )

        # --- 收集样本 ---
        if len(samples) < 5:
            for m in re.finditer(r'(.{10,90}（详见 [^）]+）)', content):
                sample = m.group(1).strip()
                ok = True
                for ch in sample:
                    if ord(ch) > 0x10000:  # skip emoji
                        ok = False; break
                if ok and sample not in samples:
                    samples.append(sample)

        # --- 写进 zip ---
        zf.writestr(fn, content.encode('utf-8'))
        compiled += 1

with open(OUTPUT_ZIP, 'wb') as f:
    f.write(zip_buffer.getvalue())

print(f'[2] 编译: {compiled} 文件 -> dify_perfect_payload.zip')

# ── 第三步：样本展示 ──────────────────────────────

print('[3] 平替样本:')
for s in samples[:5]:
    print(f'    {s}')

# ── 第四步：验证 ──────────────────────────────────

verify_brackets = 0
verify_nav = 0
with zipfile.ZipFile(OUTPUT_ZIP, 'r') as zf:
    for name in zf.namelist():
        c = zf.read(name).decode('utf-8')
        verify_brackets += len(re.findall(r'\[\[', c))
        if '🌐 政策拓扑链路导航' in c:
            verify_nav += 1

print(f'[4] Zip 验证: [[残留={verify_brackets}, 导航节残留={verify_nav}')

# 源码完整性
src_links = 0
for fn in files:
    with open(os.path.join(BASE, fn), 'r', encoding='utf-8') as f:
        src_links += len(re.findall(r'\[\[', f.read()))
print(f'[5] 源码: {src_links} 双链完好，Vault 未变')
