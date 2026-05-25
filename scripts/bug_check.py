"""Pre-submission bug check: scan manuscript + supplement + assets for issues.

Checks:
  1.  Figure file existence (every referenced path resolves on disk)
  2.  Citation resolution (every [@key] in paper.bib)
  3.  Section reference consistency (every Section N referenced has a heading)
  4.  Figure reference consistency (every Figure N referenced has an embed)
  5.  Supplementary figure reference consistency
  6.  Table reference inventory
  7.  TODO/FIXME/XXX/HACK markers
  8.  Em-dash (U+2014) / en-dash (U+2013) count (user rule: zero)
  9.  Vendor mentions (Claude/Anthropic/OpenAI/...)
  10. Banned phrases (user style guide)
  11. AI-tell phrases (user style guide; warnings)
  12. Manuscript word count

Exit code 0 if no hard issues, 1 if any.

Run:  python3 scripts/bug_check.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M_PATH = ROOT / "paper" / "manuscript.md"
S_PATH = ROOT / "paper" / "supplement.md"
BIB_PATH = ROOT / "paper" / "paper.bib"

M = M_PATH.read_text()
S = S_PATH.read_text() if S_PATH.exists() else ""
BIB = BIB_PATH.read_text() if BIB_PATH.exists() else ""
ALL = M + "\n" + S
ALL_LOWER = ALL.lower()

issues = []
warnings = []

print("=" * 60)
print("BUG CHECK")
print("=" * 60)

# --- 1. Figure files ---
figs = set(re.findall(r'paper/figures/[\w_/]+\.(?:png|pdf|svg|jpg|jpeg)', ALL))
figs |= set(re.findall(r'results/[\w_/]+\.(?:png|pdf|svg|jpg|jpeg)', ALL))
print(f"\n[1] Figure files ({len(figs)} unique paths referenced)")
for f in sorted(figs):
    if not (ROOT / f).exists():
        print(f"  MISSING  {f}")
        issues.append(f"Missing file: {f}")

# --- 2. Citations ---
cited = set(re.findall(r'\[@(\w+)', ALL))
bib_keys = set(re.findall(r'@\w+\{(\w+),', BIB))
missing = cited - bib_keys
print(f"\n[2] Citations ({len(cited)} cited, {len(bib_keys)} in bib)")
if missing:
    for k in sorted(missing):
        print(f"  UNRESOLVED  [@{k}]")
        issues.append(f"[@{k}] not in paper.bib")
else:
    print("  All cited keys resolve")

# --- 3. Section references ---
sec_refs = set(re.findall(r'Section[s]?\s+(\d+(?:\.\d+)?)', M))
sec_defs = set(re.findall(r'^###?\s+(\d+(?:\.\d+)?)', M, re.MULTILINE))
missing_secs = sec_refs - sec_defs
print(f"\n[3] Sections ({len(sec_defs)} defined, {len(sec_refs)} referenced)")
if missing_secs:
    for n in sorted(missing_secs, key=lambda x: tuple(int(p) for p in x.split('.'))):
        print(f"  REFERENCED, UNDEFINED  Section {n}")
        issues.append(f"Section {n} undefined")
else:
    print("  All section references resolve")

# --- 4. Figure references ---
fig_refs = set(re.findall(r'\bFigure (\d+)\b', M))
fig_embeds = set(re.findall(r'!\[Figure (\d+)\.', M))
missing_figs = fig_refs - fig_embeds
print(f"\n[4] Figures ({len(fig_embeds)} embedded, {len(fig_refs)} referenced)")
if missing_figs:
    for f in sorted(missing_figs, key=int):
        print(f"  REFERENCED, NOT EMBEDDED  Figure {f}")
        warnings.append(f"Figure {f} not embedded")
else:
    print("  All main figures embedded")

# --- 5. Supplementary figures ---
sup_refs = set(re.findall(r'Supplementary Figure S(\d+)', ALL))
sup_embeds = set(re.findall(r'!\[Supplementary Figure S(\d+)', S))
sup_embeds.add('1')  # S1 is the existing STARD flow PNG, referenced by path
missing_sup = sup_refs - sup_embeds
print(f"\n[5] Sup Figures (embedded: S{sorted(sup_embeds, key=int)}, ref'd: S{sorted(sup_refs, key=int)})")
if missing_sup:
    for f in sorted(missing_sup, key=int):
        print(f"  REFERENCED, NOT EMBEDDED  Sup Fig S{f}")
        warnings.append(f"Sup Fig S{f} not embedded")
else:
    print("  All sup figures accounted for")

# --- 6. Tables ---
tab_refs = sorted(set(re.findall(r'\bTable (\d+)\b', M)), key=int)
print(f"\n[6] Tables ({len(tab_refs)} numbers referenced): {tab_refs}")

# --- 7. TODO/FIXME ---
markers = re.findall(r'\b(TODO|FIXME|XXX|HACK)\b[^\n]*', ALL)
print(f"\n[7] TODO/FIXME markers: {len(markers)}")
for marker in markers[:5]:
    print(f"  {marker[:100]}")
    warnings.append(f"Marker: {marker[:60]}")

# --- 8. Em/en dashes ---
em = ALL.count("\u2014")
en = ALL.count("\u2013")
print(f"\n[8] Em-dashes (U+2014): {em}, En-dashes (U+2013): {en}")
if em or en:
    issues.append(f"{em} em + {en} en dashes (user rule: zero)")
    for ch_name, ch in [("em-dash", "\u2014"), ("en-dash", "\u2013")]:
        for i, line in enumerate(M.split("\n")):
            if ch in line:
                idx = line.find(ch)
                print(f"  {ch_name} at manuscript line {i+1}: ...{line[max(0,idx-30):idx+30]}...")
                break

# --- 9. Vendor mentions ---
vendors = re.findall(r'\b(Claude|Anthropic|OpenAI|ChatGPT|GPT|LLM)\b', ALL, re.IGNORECASE)
print(f"\n[9] Vendor mentions: {len(vendors)}")
if vendors:
    print(f"  {set(vendors)}")
    issues.append(f"Vendor mentions: {set(vendors)}")

# --- 10. Banned phrases ---
banned = ['deliberately', 'on purpose', 'by design', 'crucially', 'importantly',
          'notably', 'furthermore', 'moreover', 'leverage', 'seamless',
          'holistic', 'delve']
print(f"\n[10] Banned phrases")
any_banned = False
for phrase in banned:
    count = ALL_LOWER.count(phrase)
    if count:
        any_banned = True
        idx = ALL_LOWER.find(phrase)
        ctx = ALL[max(0, idx - 50):idx + 50 + len(phrase)].replace("\n", " ")
        print(f"  '{phrase}' ({count}x): ...{ctx}...")
        issues.append(f"Banned phrase '{phrase}' x{count}")
if not any_banned:
    print("  None")

# --- 11. AI-tell phrases ---
ai_tells = ['comprehensive', 'elegant', 'powerful', 'cutting-edge', 'cutting edge',
            'state-of-the-art', 'state of the art', 'streamline', 'unleash',
            'empower', 'plethora', 'myriad']
print(f"\n[11] AI-tells (warnings)")
any_tell = False
for phrase in ai_tells:
    count = ALL_LOWER.count(phrase)
    if count:
        any_tell = True
        idx = ALL_LOWER.find(phrase)
        ctx = ALL[max(0, idx - 50):idx + 50 + len(phrase)].replace("\n", " ")
        print(f"  '{phrase}' ({count}x): ...{ctx}...")
        warnings.append(f"AI-tell '{phrase}' x{count}")
# robust (allowed in doubly-robust)
non_doubly = []
for i, l in enumerate(M.split("\n")):
    if 'robust' in l.lower() and 'doubly-robust' not in l.lower() and 'doubly robust' not in l.lower():
        non_doubly.append((i + 1, l))
if non_doubly:
    print(f"  'robust' (non-doubly): {len(non_doubly)} lines")
    for ln, line in non_doubly[:3]:
        idx = line.lower().find('robust')
        print(f"    Line {ln}: ...{line[max(0,idx-30):idx+40]}...")

# --- 12. Word count ---
text = re.sub(r'```.*?```', '', M, flags=re.DOTALL)
text = '\n'.join(l for l in text.split('\n') if not l.strip().startswith('|'))
text = re.sub(r'^:\s+.*$', '', text, flags=re.MULTILINE)
text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
text = re.sub(r'\*([^*]+)\*', r'\1', text)
text = re.sub(r'\[@[^\]]+\]', '', text)
text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
if '## References' in text:
    text = text.split('## References')[0]
wc = len(text.split())
print(f"\n[12] Manuscript word count: {wc:,}")

# --- Summary ---
print("\n" + "=" * 60)
print(f"SUMMARY: {len(issues)} hard issue(s), {len(warnings)} warning(s)")
print("=" * 60)
if issues:
    print("\nHARD ISSUES:")
    for i in issues:
        print(f"  - {i}")
if warnings:
    print(f"\nWARNINGS ({len(warnings)}):")
    for w in warnings:
        print(f"  - {w}")
if not issues and not warnings:
    print("\nClean. Nothing to address.")

sys.exit(1 if issues else 0)
