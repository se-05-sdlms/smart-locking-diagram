import sys, os, re
from pathlib import Path

be = Path(r'D:\code_capstone\smart-locking-be')

print("=== ALL CONTROLLERS IN BE ===")
controllers = sorted((be / 'smart-locking-be.API' / 'Controllers').glob('*.cs'))
for c in controllers:
    text = c.read_text(encoding='utf-8')
    route = re.findall(r'Route\("([^"]+)"\)', text)
    methods = re.findall(r'\[(Http[A-Za-z]+)(?:\("([^"]*)"\))?\]', text)
    print(f"{c.name:<35} route={route} endpoints={len(methods)}")

print("\n=== ALL BACKGROUND WORKERS IN BE ===")
services = sorted((be / 'smart-locking-be.Infrastructure' / 'Services').glob('*Worker*.cs'))
for s in services:
    print(f"Worker: {s.name}")

print("\n=== ALL MIGRATIONS IN BE (RECENT) ===")
migrations = sorted((be / 'smart-locking-be.Infrastructure' / 'Persistence' / 'Migrations').glob('*.cs'))
for m in migrations[-10:]:
    if not m.name.endswith('Designer.cs'):
        print(f"Migration: {m.name}")
