# Deploy e atualização no servidor (VPS)

Integração **eContador → ifPonto/stou** (projeto Python **olp**).

| Item | Valor |
|------|--------|
| Caminho no servidor | `/home/gogotech/integracao/olp` |
| Repositório | https://github.com/AndrewsGama-Dev/olp.git |
| Fonte | API eContador (`dp.pack.alterdata.com.br`) |
| Destino | ifPonto (`https://stou.ifractal.com.br/olp/rest/`) |
| Empresas | IDs no `.config` (`codigo_empresa`) |
| Orquestrador | `main.py` / `integrador.sh` |

O arquivo **`.config` não vai no Git**. Criar só no servidor (ou enviar por `scp`).

## 1. Primeira instalação no VPS

```bash
sudo mkdir -p /home/gogotech/integracao/olp
sudo chown -R gogotech:gogotech /home/gogotech/integracao/olp
chmod 755 /home/gogotech/integracao/olp

cd /home/gogotech/integracao/olp
git clone https://github.com/AndrewsGama-Dev/olp.git .

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

chmod +x integrador.sh
```

Criar o `.config` no servidor (não vem do Git):

```bash
cp .config.exemplo .config
nano .config
# preencher token eContador, token_base ifPonto e senha SOAP
chmod 600 .config
chown gogotech:gogotech .config
```

Ou, do PC (depois do clone):

```powershell
scp .config gogotech@147.79.110.186:/home/gogotech/integracao/olp/.config
```

No VPS: `chmod 600 .config`

## 2. Atualizar código (Git)

**No PC:** commit + push em `main` (**sem** `.config`).

**No VPS:**

```bash
cd /home/gogotech/integracao/olp
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
```

O `.config` de produção **não** é sobrescrito pelo `git pull`.

## 3. Teste

```bash
cd /home/gogotech/integracao/olp
source .venv/bin/activate

# Primeira carga: departamentos e cargos antes dos funcionarios
python departamentos.py
python cargos.py
python funcionarios.py csv
python funcionarios.py enviar

# Fluxo completo (envia ao stou)
./integrador.sh
```

## 4. Cron

```bash
crontab -u gogotech -e
```

```cron
*/30 * * * * cd /home/gogotech/integracao/olp && flock -n /tmp/integrador_olp.lock ./integrador.sh >> /home/gogotech/integracao/olp/integrador.log 2>&1
```

## 5. Checklist

```bash
cd /home/gogotech/integracao/olp
test -f .config && echo "OK .config" || echo "FALTA .config"
test -x integrador.sh && echo "OK integrador.sh" || chmod +x integrador.sh
source .venv/bin/activate
python -c "import requests, pandas, pytz; print('OK deps')"
```

Saída **HTTPS (443)** para `dp.pack.alterdata.com.br` e `stou.ifractal.com.br`.
