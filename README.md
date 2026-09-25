# Integração OLP

eContador (Alterdata Pack) → CSV → ifPonto/stou (`https://stou.ifractal.com.br/olp/rest/`).

Empresas no `.config`: **71** e **72**.

## Local

```bash
cp .config.exemplo .config   # preencher credenciais
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Linux:   source .venv/bin/activate
pip install -r requirements.txt

python funcionarios.py csv
python funcionarios.py enviar
# ou fluxo completo:
python main.py
```

O `.config` **não** vai para o Git.

## Servidor

Caminho: `/home/gogotech/integracao/olp`  
Repositório: https://github.com/AndrewsGama-Dev/olp.git  

Passo a passo: **[DEPLOY_SERVIDOR.md](DEPLOY_SERVIDOR.md)**
