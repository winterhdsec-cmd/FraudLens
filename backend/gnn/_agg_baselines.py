import json
import numpy as np
from scipy import stats

d = json.load(open('baseline_v2_results.json', encoding='utf-8'))
print('=== summary ===')
print(json.dumps(d['summary'], ensure_ascii=False, indent=1))
print('=== scale_summary ===')
print(json.dumps(d['scale_summary'], ensure_ascii=False, indent=1))

ps = d['per_seed']
methods = ['HAN', 'RGCN', 'GAT', 'KMeans', 'Semantic', 'CurrentSystem']
print('=== per-cross mean+-std f1 (n=15) ===')
for c in [0.0, 0.2, 0.4]:
    rows = [r for r in ps if abs(r['cross'] - c) < 1e-9]
    line = 'cross=%s n=%d: ' % (c, len(rows))
    for m in methods:
        v = np.array([r[m]['f1'] for r in rows])
        line += '%s=%.3f+-%.3f  ' % (m, v.mean(), v.std(ddof=1))
    print(line)

print('=== paired tests (HAN vs X) per cross ===')
for c in [0.0, 0.2, 0.4]:
    rows = [r for r in ps if abs(r['cross'] - c) < 1e-9]
    h = np.array([r['HAN']['f1'] for r in rows])
    for m in ['RGCN', 'GAT', 'CurrentSystem', 'KMeans']:
        x = np.array([r[m]['f1'] for r in rows])
        dif = h - x
        if np.allclose(dif, 0):
            print(' cross=%s HAN vs %s: identical' % (c, m))
            continue
        try:
            w = stats.wilcoxon(h, x).pvalue
        except Exception:
            w = float('nan')
        t = stats.ttest_rel(h, x).pvalue
        print(' cross=%s HAN vs %s: diff=%+.3f wilcoxon_p=%.4g t_p=%.4g' % (c, m, dif.mean(), w, t))

print('=== overall all-45 ===')
for m in methods:
    v = np.array([r[m]['f1'] for r in ps])
    print(' %s: %.3f+-%.3f min=%.3f' % (m, v.mean(), v.std(ddof=1), v.min()))

print('=== NMI per cross ===')
for c in [0.0, 0.2, 0.4]:
    rows = [r for r in ps if abs(r['cross'] - c) < 1e-9]
    line = 'cross=%s: ' % c
    for m in methods:
        v = np.array([r[m]['nmi'] for r in rows])
        line += '%s=%.3f  ' % (m, v.mean())
    print(line)

print('=== scale_robustness raw ===')
sr = d.get('scale_robustness', [])
print('n=', len(sr))
if sr:
    print(json.dumps(sr[0], ensure_ascii=False)[:400])
    for g in sorted(set(r.get('n_gangs') for r in sr)):
        rows = [r for r in sr if r.get('n_gangs') == g]
        line = 'n_gangs=%s n=%d: ' % (g, len(rows))
        for m in methods:
            if m in rows[0]:
                v = np.array([r[m]['f1'] for r in rows])
                line += '%s=%.3f+-%.3f  ' % (m, v.mean(), v.std(ddof=1))
        print(line)
