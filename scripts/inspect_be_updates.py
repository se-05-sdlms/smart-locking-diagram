from pathlib import Path
import re

be = Path(r'D:\code_capstone\smart-locking-be')
f = be / 'smart-locking-be.API/Controllers/ParcelsController.cs'
text = f.read_text(encoding='utf-8')
print('ParcelsController endpoints:')
for m in re.finditer(r'\[(Http[A-Za-z]+)(?:\("([^"]*)"\))?\][\s\S]*?public\s+async\s+Task<[^>]+>\s+(\w+)', text):
    print(f'  {m.group(1)} {m.group(2) or ""} -> {m.group(3)}')

print('\nCheck OperationsController:')
print('Exists:', (be / 'smart-locking-be.API/Controllers/OperationsController.cs').exists())

print('\nCheck OverduePaymentsController:')
print('Exists:', (be / 'smart-locking-be.API/Controllers/OverduePaymentsController.cs').exists())
