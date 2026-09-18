# -*- coding: utf-8 -*-
import re

def get_tikz(src):
    with open(src, encoding='utf-8') as f:
        t = f.read()
    m = re.search(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', t, re.S)
    return m.group(0)

arch = get_tikz('fig_arch.tex')
wf = get_tikz('fig_workflow.tex')

with open('CPEC2026_draft.tex', encoding='utf-8') as f:
    main = f.read()

def replace_figure(main, label, new_tikz):
    lab_idx = main.find('\\label{' + label + '}')
    fig_start = main.rfind('\\begin{figure}[htbp]', 0, lab_idx)
    fig_end = main.find('\\end{figure}', lab_idx) + len('\\end{figure}')
    seg = main[fig_start:lab_idx]
    cap_m = re.search(r'\\caption\{[^}]*\}', seg)
    cap = cap_m.group(0) if cap_m else '\\caption{}'
    new_fig = ('\\begin{figure}[htbp]\n'
               '  \\centering\n'
               '  \\resizebox{\\linewidth}{!}{%\n'
               + new_tikz + '%\n'
               '  }\n'
               '  ' + cap + '\n'
               '  \\label{' + label + '}\n'
               '\\end{figure}')
    return main[:fig_start] + new_fig + main[fig_end:]

main = replace_figure(main, 'fig:arch', arch)
main = replace_figure(main, 'fig:workflow', wf)

with open('CPEC2026_draft.tex', 'w', encoding='utf-8') as f:
    f.write(main)

print('synced. arch tikz len=', len(arch), '| workflow tikz len=', len(wf))
# 验证
print('fig:arch appears:', main.count('\\label{fig:arch}'))
print('fig:workflow appears:', main.count('\\label{fig:workflow}'))
