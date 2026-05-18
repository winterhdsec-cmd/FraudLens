"""Remove duplicate destructuring blocks in all views"""
import os

VIEWS = r'c:\Users\hd\Desktop\学习生涯\项目\FraudLens\frontend\src\views'

for fname in sorted(os.listdir(VIEWS)):
    if not fname.endswith('.vue'):
        continue
    fp = os.path.join(VIEWS, fname)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the pattern: first } = state followed by const { ... } = state
    idx = content.find('} = state')
    if idx < 0:
        continue
    
    after = content[idx + len('} = state'):]
    # Check if there's another const { ... } = state block after this
    second = after.find('const {')
    if second < 0:
        continue
    
    # Remove everything from second const { to its closing } = state
    end = after.find('} = state', second)
    if end < 0:
        continue
    
    content = content[:idx + len('} = state')] + after[end + len('} = state'):]
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed {fname}')

print('DONE')