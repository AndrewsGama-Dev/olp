import configparser
import os
import time

import requests

def ler_config():
    """
    Lê o arquivo .config e retorna um dicionário com todas as seções
    """
    try:
        if not os.path.exists('.config'):
            print("❌ Arquivo .config não encontrado")
            return None
        
        config = configparser.ConfigParser()
        config.read('.config', encoding='utf-8')
        
        # Converter para dicionário para facilitar o uso
        config_dict = {}
        for secao in config.sections():
            config_dict[secao] = dict(config[secao])
        
        return config_dict
        
    except Exception as e:
        print(f"❌ Erro ao ler arquivo .config: {e}")
        return None

def ler_token_config():
    """
    Lê especificamente o token da seção APISOURCE
    """
    try:
        config = ler_config()
        if config and 'APISOURCE' in config:
            token = config['APISOURCE'].get('token')
            if token:
                print("✅ Token carregado do arquivo .config")
                return token.strip('"')  # Remove aspas se houver
        
        print("❌ Token não encontrado na seção [APISOURCE]")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao ler token: {e}")
        return None

def obter_headers_api():
    """
    Obtém os headers necessários para chamadas à API da Alterdata
    """
    token = ler_token_config()
    if not token:
        return None
    
    headers = {
        'Content-Type': 'application/vnd.api+json',
        'Authorization': f'Bearer {token}'
    }
    
    return headers


def get_jsonapi_paginado(url, headers, params=None, page_limit=100, max_paginas=200, timeout=60, pausa=0.2):
    """
    Percorre páginas JSON:API reaplicando os filtros em toda requisição.

    A URL em links.next da eContador costuma omitir filter[...], então
    não deve ser usada quando há filtro de empresa/status.
    Yields: (pagina, data_json, itens)
    """
    params = dict(params or {})
    limit = int(params.get("page[limit]", page_limit))
    offset = 0

    for pagina in range(1, max_paginas + 1):
        req = dict(params)
        req["page[limit]"] = str(limit)
        req["page[offset]"] = str(offset)
        response = requests.get(url, headers=headers, params=req, timeout=timeout)
        if response.status_code == 429:
            time.sleep(10)
            response = requests.get(url, headers=headers, params=req, timeout=timeout)
        if response.status_code != 200:
            print(f"Erro API {response.status_code}: {response.text[:200]}")
            return
        data = response.json()
        itens = data.get("data") or []
        yield pagina, data, itens
        if len(itens) < limit:
            return
        offset += limit
        if pausa:
            time.sleep(pausa)


def _parse_ids_separados(valor):
    """Aceita '9' ou '9,10,11' (vírgula ou ponto e vírgula)."""
    ids = []
    if valor is None:
        return ids
    texto = str(valor).strip().strip('"').strip("'")
    if not texto:
        return ids
    for parte in texto.replace(';', ',').split(','):
        item = parte.strip()
        if item and item not in ids:
            ids.append(item)
    return ids


def ler_codigos_empresa_filtro():
    """
    Lê os IDs de empresa em [FILTROS].codigo_empresa.

    Aceita um ID (`9`) ou vários separados por vírgula (`9,10,11`).
    Returns:
        list[str]: IDs (ex.: ["9", "10", "11"]) ou lista vazia = todas as empresas.
    """
    try:
        config = ler_config()
        if not config or 'FILTROS' not in config:
            return []
        return _parse_ids_separados(config['FILTROS'].get('codigo_empresa'))
    except Exception as e:
        print(f"❌ Erro ao ler codigo_empresa do .config: {e}")
        return []


def ler_departamentos_ignorar():
    """
    IDs de departamento (eContador) que não entram na integração.
    [FILTROS].departamentos_ignorar — ex.: 940,973 (MAPA AP e MAPA RORAIMA).
    """
    try:
        config = ler_config()
        if not config or 'FILTROS' not in config:
            return []
        return _parse_ids_separados(config['FILTROS'].get('departamentos_ignorar'))
    except Exception as e:
        print(f"❌ Erro ao ler departamentos_ignorar do .config: {e}")
        return []


def id_departamento_do_funcionario(funcionario):
    """ID do departamento no relacionamento JSON:API, ou ''."""
    if not funcionario:
        return ""
    rel = (funcionario.get("relationships") or {}).get("departamento") or {}
    data = rel.get("data")
    if isinstance(data, dict):
        return str(data.get("id") or "").strip()
    return ""


def funcionario_departamento_ignorado(funcionario):
    """True se o funcionário pertence a um departamento em departamentos_ignorar."""
    ignorar = set(ler_departamentos_ignorar())
    if not ignorar:
        return False
    return id_departamento_do_funcionario(funcionario) in ignorar


def ler_codigo_empresa_filtro():
    """
    Compatibilidade: primeiro ID configurado, ou None se vazio.
    Prefira ler_codigos_empresa_filtro() quando houver várias empresas.
    """
    ids = ler_codigos_empresa_filtro()
    return ids[0] if ids else None


def normalizar_codigo_empresa(valor):
    """00132 e 132 viram 132. Texto vazio continua vazio."""
    texto = str(valor or "").strip()
    if texto.isdigit():
        return str(int(texto))
    return texto


_MAPA_EMPRESAS = None


def carregar_empresas_econtador():
    """
    Empresas ativas do token: id interno eContador e externoid.
    Cache no processo para não repetir a listagem em cada módulo.
    """
    global _MAPA_EMPRESAS
    if _MAPA_EMPRESAS is not None:
        return _MAPA_EMPRESAS

    empresas = []
    headers = obter_headers_api()
    if not headers:
        _MAPA_EMPRESAS = empresas
        return empresas

    url = "https://dp.pack.alterdata.com.br/api/v1/empresas"
    offset = 0
    while True:
        params = {
            "filter[empresas][ativa][EQ]": "true",
            "page[limit]": "100",
            "page[offset]": str(offset),
        }
        response = requests.get(url, headers=headers, params=params, timeout=60)
        if response.status_code != 200:
            print(f"❌ Erro ao listar empresas eContador: {response.status_code}")
            break
        itens = response.json().get("data") or []
        for item in itens:
            attrs = item.get("attributes") or {}
            empresas.append({
                "id": str(item.get("id") or ""),
                "externoid": str(attrs.get("externoid") or ""),
                "nome": str(attrs.get("nome") or ""),
            })
        if len(itens) < 100:
            break
        offset += 100
        if offset:
            time.sleep(0.2)

    _MAPA_EMPRESAS = empresas
    return empresas


def _empresa_por_codigo_config(codigo, empresas):
    """Casa o valor do .config com externoid (132) ou, se não achar, com o id interno (71)."""
    chave = normalizar_codigo_empresa(codigo)
    if not chave:
        return None
    for emp in empresas:
        if normalizar_codigo_empresa(emp.get("externoid")) == chave:
            return emp
    for emp in empresas:
        if normalizar_codigo_empresa(emp.get("id")) == chave:
            return emp
    return None


def ids_internos_para_consultar():
    """
    Converte [FILTROS].codigo_empresa no id interno usado em filter[empresa.id].
    O .config guarda o externoid (132, 135).
    """
    codigos = ler_codigos_empresa_filtro()
    if not codigos:
        return []
    empresas = carregar_empresas_econtador()
    internos = []
    for codigo in codigos:
        emp = _empresa_por_codigo_config(codigo, empresas)
        if not emp or not emp.get("id"):
            print(f"❌ codigo_empresa {codigo} não encontrado como externoid nem como id eContador")
            continue
        if emp["id"] not in internos:
            internos.append(emp["id"])
    return internos


def codigo_empresa_para_csv(id_interno, externoid=""):
    """Código da empresa no CSV/ifPonto: externoid sem zeros à esquerda (00132 → 132)."""
    if externoid:
        return normalizar_codigo_empresa(externoid)
    chave = str(id_interno or "").strip()
    if not chave:
        return ""
    for emp in carregar_empresas_econtador():
        if emp.get("id") == chave:
            return normalizar_codigo_empresa(emp.get("externoid")) or chave
    return normalizar_codigo_empresa(chave)


def empresas_para_consultar():
    """
    IDs internos a consultar na API. [None] = não aplicar filter[empresa.id].
    Lista vazia = filtro configurado, mas nenhum código foi resolvido.
    """
    if not ler_codigos_empresa_filtro():
        return [None]
    return ids_internos_para_consultar()


def descrever_filtro_empresa():
    codigos = ler_codigos_empresa_filtro()
    if not codigos:
        return "sem filtro (todas as empresas)"
    empresas = carregar_empresas_econtador()
    partes = []
    for codigo in codigos:
        emp = _empresa_por_codigo_config(codigo, empresas)
        if emp:
            externo = normalizar_codigo_empresa(emp.get("externoid")) or codigo
            partes.append(f"{externo} (id eContador {emp['id']})")
        else:
            partes.append(f"{codigo} (não encontrado)")
    return ", ".join(partes)


def _parse_bool_config(valor, default=True):
    """Interpreta true/false, 1/0, sim/nao, yes/no (case insensitive)."""
    if valor is None:
        return default
    texto = str(valor).strip().strip('"').lower()
    if texto in ('true', '1', 'yes', 'y', 'sim', 's', 'on'):
        return True
    if texto in ('false', '0', 'no', 'n', 'nao', 'não', 'off'):
        return False
    return default


MODULOS_PADRAO = (
    'empresas',
    'departamentos',
    'cargos',
    'funcionarios',
    'afastamentos',
    'demissoes',
)


def ler_modulos_habilitados():
    """
    Lê a seção [MODULOS] do .config (true/false por módulo).

    Se a seção não existir, todos os módulos ficam habilitados (compatibilidade).
    """
    habilitados = {nome: True for nome in MODULOS_PADRAO}
    try:
        config = ler_config()
        if not config or 'MODULOS' not in config:
            return habilitados

        secao = config['MODULOS']
        for nome in MODULOS_PADRAO:
            if nome in secao:
                habilitados[nome] = _parse_bool_config(secao.get(nome), default=True)
        return habilitados
    except Exception as e:
        print(f"❌ Erro ao ler [MODULOS] do .config: {e}")
        return habilitados


def modulo_habilitado(nome_modulo):
    """Retorna True se o módulo deve ser executado conforme [MODULOS]."""
    return bool(ler_modulos_habilitados().get(nome_modulo, True))


# Chaves da seção [AFASTAMENTOS] e valores padrão (ifPonto)
CODIGOS_AFASTAMENTO_PADRAO = {
    'codigo_padrao': '',
    'ferias': '',
    'cat': '',
    'beneficio': '',
    'atestado': '',
    'sat': '',
    'servico_militar': '',
    'abandono_emprego': '',
    'suspensao_contrato': '',
    'licenca_remunerada': '',
    'salario_maternidade': '',
    'licenca_sem_remuneracao': '',
    'aposentadoria_invalidez': '',
    'licenca_paternidade': '',
    'atestado_acidente_trabalho': '',
    'outros': '',
}


def ler_codigos_afastamento():
    """
    Lê [AFASTAMENTOS] do .config (código ifPonto por tipo).
    Chave presente e vazia fica sem código. Chave ausente usa o padrão do código.
    """
    codigos = dict(CODIGOS_AFASTAMENTO_PADRAO)
    try:
        config = ler_config()
        if not config or 'AFASTAMENTOS' not in config:
            return codigos

        secao = config['AFASTAMENTOS']
        for chave in secao:
            valor = str(secao.get(chave) or '').strip().strip('"')
            if valor:
                codigos[chave] = valor
            elif chave in codigos:
                codigos[chave] = ''
        return codigos
    except Exception as e:
        print(f"❌ Erro ao ler [AFASTAMENTOS] do .config: {e}")
        return codigos


def historico_demissoes_habilitado():
    """
    Lê historico_demissoes (true/false).

    Ordem: [FILTROS] e, se não existir, [MODULOS] (compatibilidade).
    true  = usa demissoes_matricula_processados.txt (padrão)
    false = não lê nem grava o histórico (reprocessa demissões)
    """
    try:
        config = ler_config()
        if not config:
            return True

        valor = None
        if 'FILTROS' in config and 'historico_demissoes' in config['FILTROS']:
            valor = config['FILTROS'].get('historico_demissoes')
        elif 'MODULOS' in config and 'historico_demissoes' in config['MODULOS']:
            valor = config['MODULOS'].get('historico_demissoes')

        if valor is None:
            return True

        return _parse_bool_config(valor, default=True)
    except Exception as e:
        print(f"❌ Erro ao ler historico_demissoes do .config: {e}")
        return True