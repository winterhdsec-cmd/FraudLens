"""Remove redundant v-if from view root divs"""
import os, re

VIEWS = r'c:\Users\hd\Desktop\学习生涯\项目\FraudLens\frontend\src\views'

for fname in sorted(os.listdir(VIEWS)):
    if not fname.endswith('.vue'):
        continue
    fp = os.path.join(VIEWS, fname)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove v-if="activeMenu === 'xxx'" from the root <div>
    content = re.sub(r'<div v-if="activeMenu === \'[^\']+\'"', '<div', content)

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed {fname}')

print('DONE')