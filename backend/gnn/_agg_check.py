import json, statistics as st
d = json.load(open("eval_full_results.json"))
print("top-level keys:", list(d.keys()))

e1 = d.get("exp1_baselines", {})
for setting in ("clean", "hard"):
    rows = e1.get(setting, [])
    hanfull = [r.get("CurrentGNN(HAN-true)_f1") for r in rows if "CurrentGNN(HAN-true)_f1" in r]
    gains = [r.get("dual_channel_gain_f1") for r in rows if "dual_channel_gain_f1" in r]
    print(f"\n[exp1_baselines:{setting}] n={len(rows)}")
    print(f"  HAN-true F1 mean={st.mean(hanfull):.4f} std={st.pstdev(hanfull):.4f} min={min(hanfull)} max={max(hanfull)}")
    if gains:
        print(f"  dual_channel_gain_f1 mean={st.mean(gains):.4f} std={st.pstdev(gains):.4f} n={len(gains)} pos={sum(g>0 for g in gains)} neg={sum(g<0 for g in gains)}")
        for r in rows:
            print(f"    seed={r.get('seed')} han_full={r.get('CurrentGNN(HAN-true)_f1')} han_notext={r.get('han_no_text_channel_f1')} gain={r.get('dual_channel_gain_f1')}")

e2 = d.get("exp2_a1_dual_channel", {})
for setting in ("clean", "hard"):
    rows = e2.get(setting, [])
    if not rows:
        print(f"\n[exp2_a1_dual_channel:{setting}] EMPTY"); continue
    full = [r.get("han_full_f1") for r in rows]
    notext = [r.get("han_notext_f1") for r in rows]
    gains = [r.get("dual_channel_gain_f1") for r in rows]
    print(f"\n[exp2_a1_dual_channel:{setting}] n={len(rows)}")
    print(f"  han_full F1 mean={st.mean(full):.4f} std={st.pstdev(full):.4f}")
    print(f"  han_notext F1 mean={st.mean(notext):.4f} std={st.pstdev(notext):.4f}")
    print(f"  dual_channel_gain_f1 mean={st.mean(gains):.4f} std={st.pstdev(gains):.4f} pos={sum(g>0 for g in gains)} neg={sum(g<0 for g in gains)}")
    for r in rows:
        print(f"    seed={r.get('seed')} full={r.get('han_full_f1')} notext={r.get('han_notext_f1')} gain={r.get('dual_channel_gain_f1')}")

# also check experiment_all.py for any other recorded exp
for k in d.keys():
    if k not in ("exp1_baselines", "exp2_a1_dual_channel", "env", "seeds", "cross"):
        print("\nOTHER KEY:", k, "->", type(d[k]))
