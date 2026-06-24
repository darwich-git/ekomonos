import sys, io, glob, json, uuid, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pdfplumber

matches = glob.glob(r'C:\Users\darwi.PCDARWICH\OneDrive\Desktop\PROMT*.pdf')
with pdfplumber.open(matches[0]) as pdf:
    full = ''
    for page in pdf.pages:
        t = page.extract_text()
        if t: full += t + '\n'

lines = full.split('\n')

def extract_block(start_idx, end_idx):
    block = '\n'.join(lines[start_idx:end_idx]).strip()
    # Remove footer lines
    cleaned = []
    for l in block.split('\n'):
        if 'Arte de Invertir' in l or 'Material de uso exclusivo' in l:
            continue
        if l.strip().isdigit():
            continue
        cleaned.append(l)
    return '\n'.join(cleaned).strip()

prompts_to_add = [
    {
        'id': str(uuid.uuid4()),
        'title': 'M&A - Situacion Previa y Contexto',
        'category': 'Metodo Alpha - M&A Arbitraje',
        'text': extract_block(67, 367)
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'M&A - Metodo Alpha Completo (Puntos de Comprobacion)',
        'category': 'Metodo Alpha - M&A Arbitraje',
        'text': extract_block(367, 476)
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'M&A - Valoracion y Estructura Accionarial (Voto)',
        'category': 'Metodo Alpha - M&A Arbitraje',
        'text': extract_block(476, 698)
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'M&A - Analisis de Situacion y Contexto',
        'category': 'Metodo Alpha - M&A Arbitraje',
        'text': extract_block(698, 818)
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'M&A - Valoracion Detallada (Multiplos y Comparables)',
        'category': 'Metodo Alpha - M&A Arbitraje',
        'text': extract_block(818, 993)
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'Spin-Off / Special Div - Situacion Previa y Contexto',
        'category': 'Metodo Alpha - Otras Situaciones',
        'text': extract_block(993, 1105)
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'Valoracion de Activos en Liquidacion',
        'category': 'Metodo Alpha - Otras Situaciones',
        'text': extract_block(1105, 1350)
    },
]

data_path = 'data/prompts.json'
os.makedirs('data', exist_ok=True)
if os.path.exists(data_path):
    with open(data_path, encoding='utf-8') as f:
        existing = json.load(f)
else:
    existing = []

existing_titles = {p['title'] for p in existing}
added = 0
for p in prompts_to_add:
    if p['title'] not in existing_titles:
        existing.append(p)
        added += 1
        print(f"Added: [{p['category']}] {p['title']} ({len(p['text'])} chars)")

with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

print(f'\nDone. Added {added} new prompts. Total in DB: {len(existing)}')
