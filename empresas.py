import requests
import json
import pandas as pd
from datetime import datetime
import time
import hashlib
import pytz
import configparser
from config_reader import obter_headers_api, ler_token_config, normalizar_codigo_empresa

def carregar_configuracoes_target():
    """
    Carrega configurações da seção [APITARGET] do arquivo .config
    """
    try:
        config = configparser.ConfigParser()
        config.read('.config', encoding='utf-8')
        
        if 'APITARGET' not in config:
            print("❌ Seção [APITARGET] não encontrada no arquivo .config")
            return None
        
        return {
            'url': config['APITARGET'].get('url', '').strip(),
            'integracao': config['APITARGET'].get('integracao', '').strip(),
            'token_base': config['APITARGET'].get('token_base', '').strip()
        }
    except Exception as e:
        print(f"❌ Erro ao carregar configurações [APITARGET]: {e}")
        return None

def gerar_token_target():
    """
    Gera o token para a API de destino usando a data atual
    """
    config_target = carregar_configuracoes_target()
    if not config_target:
        return None, None
    
    # ==========================================
    # IMPLEMENTAR EXATAMENTE COMO FUNCIONOU NO DEBUG_TOKEN.PY
    # ==========================================
    
    # Configurar timezone para São Paulo
    tz_sao_paulo = pytz.timezone('America/Sao_Paulo')
    data_atual = datetime.now(tz_sao_paulo).strftime('%d/%m/%Y')
    
    # Gerar token final
    token_concatenado = config_target['token_base'] + data_atual
    token_final = hashlib.sha256(token_concatenado.encode('utf-8')).hexdigest()
    
    print(f"\n🔑 GERAÇÃO DO TOKEN (PADRÃO QUE FUNCIONOU):")
    print(f"Data atual: {data_atual}")
    print(f"Token concatenado: {token_concatenado}")
    print(f"Token final: {token_final}")
    print("=" * 50)
    
    return config_target, token_final

def enviar_csv_para_api_target(nome_arquivo_csv):
    """
    Envia o CSV de empresas para a API de destino via POST
    """
    import os
    
    if not os.path.exists(nome_arquivo_csv):
        print(f"❌ Arquivo {nome_arquivo_csv} não encontrado!")
        return False
    
    print(f"✅ Arquivo {nome_arquivo_csv} encontrado")
    
    # Obter configurações e token
    config_target, token_final = gerar_token_target()
    if not config_target or not token_final:
        print("❌ Falha ao gerar token para API de destino")
        return False
    
    # CORREÇÃO: Usar 'gotech' como usuário conforme documentação original
    usuario_correto = 'gotech'  # Fixo conforme configuração original
    
    # Preparar headers e dados
    headers = {
        "user": usuario_correto,  # Mudança aqui!
        "token": token_final
    }
    
    data = {
        "pag": "configuracao_empresa",
        "cmd": "importar_cad",
        "separador": ";"
    }
    
    try:
        print(f"📤 Enviando POST para API de destino...")
        print(f"🌐 URL: {config_target['url']}")
        print(f"👤 Usuário: {usuario_correto}")  # Mostra usuário correto
        print(f"📄 Endpoint: configuracao_empresa")
        print(f"🔑 Token: {token_final[:32]}...")  # Mostra parte do token
        
        with open(nome_arquivo_csv, 'rb') as arquivo:
            files = {
                'arquivo': (nome_arquivo_csv, arquivo, 'text/csv')
            }
            
            response = requests.post(
                config_target['url'], 
                data=data, 
                files=files,
                headers=headers,
                timeout=30
            )
        
        print(f"📊 Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            try:
                resultado = response.json()
                
                # CORREÇÃO: Verificar se realmente teve sucesso
                if resultado.get('success') == False:
                    print(f"❌ API retornou erro:")
                    print(f"📝 Resposta: {json.dumps(resultado, indent=2, ensure_ascii=False)}")
                    
                    # Sugestões de correção
                    if 'login' in str(resultado.get('info', '')).lower():
                        print(f"\n💡 SUGESTÕES PARA CORRIGIR ERRO DE LOGIN:")
                        print(f"1. ❌ Verificar se token_base está correto: '{config_target['token_base']}'")
                        print(f"2. ❌ Verificar formato da data (atual: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y')})")
                        print(f"3. ❌ Confirmar usuário correto (usando: '{usuario_correto}')")
                        print(f"4. ❌ Execute debug_token.py para mais detalhes")
                    
                    return False
                else:
                    print(f"✅ POST de empresas realizado com sucesso!")
                    print(f"📋 Resposta da API:")
                    print(json.dumps(resultado, indent=2, ensure_ascii=False))
                    
                    cadastrados = resultado.get('ok', 0)
                    if cadastrados > 0:
                        print(f"🎉 {cadastrados} empresa(s) cadastrada(s) com sucesso!")
                    
                    return True
                
            except json.JSONDecodeError:
                print(f"⚠️ Resposta não é JSON válido:")
                print(f"📝 Resposta: {response.text[:500]}...")
                return False
                
        else:
            print(f"❌ ERRO no POST - Status: {response.status_code}")
            print(f"📝 Resposta: {response.text[:500]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO na requisição para API de destino: {e}")
        return False

def consultar_todas_empresas():
    """
    Coleta todas as empresas da API eContador
    """
    print("🔍 INICIANDO COLETA DE EMPRESAS...")
    
    # Obter headers do arquivo .config
    headers = obter_headers_api()
    if not headers:
        print("❌ Não foi possível obter o token do arquivo .config")
        return [], None
    
    # Configurações da API
    base_url = "https://dp.pack.alterdata.com.br/api/v1/empresas"
    
    # Filtrar apenas empresas ativas
    params = {
        "filter[empresas][ativa][EQ]": "true"
    }
    
    todas_empresas = []
    url_atual = base_url
    pagina = 1
    
    # Coletar todas as empresas com paginação
    while url_atual:
        try:
            print(f"  📄 Coletando página {pagina}... ", end="")
            
            if pagina == 1:
                response = requests.get(url_atual, headers=headers, params=params)
            else:
                response = requests.get(url_atual, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                empresas_pagina = data.get('data', [])
                todas_empresas.extend(empresas_pagina)
                
                print(f"✅ {len(empresas_pagina)} empresas")
                
                # Verificar se há próxima página
                url_atual = data.get('links', {}).get('next')
                pagina += 1
                
                # Pausa para não sobrecarregar a API
                time.sleep(0.5)
            else:
                print(f"❌ Erro {response.status_code}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na conexão: {e}")
            break
    
    print(f"\n✅ Total coletado: {len(todas_empresas)} empresas")
    return todas_empresas, headers

def consultar_empresa_detalhada(empresa_id, headers):
    """
    Busca informações detalhadas de uma empresa específica
    """
    try:
        url_empresa = f"https://dp.pack.alterdata.com.br/api/v1/empresas/{empresa_id}"
        response = requests.get(url_empresa, headers=headers)
        
        if response.status_code == 200:
            empresa_data = response.json()
            return empresa_data.get('data', {})
    except:
        pass
    
    return None

def mapear_empresa_para_csv(empresa_api, detalhes=None):
    """
    Mapeia uma empresa da API para o formato esperado no CSV
    """
    attributes = empresa_api.get('attributes', {})
    empresa_id = empresa_api.get('id', '')
    
    # Se temos detalhes, usar os atributos dos detalhes
    if detalhes and detalhes.get('attributes'):
        attributes.update(detalhes.get('attributes', {}))
    
    # externoid (00132) vai no CSV como 132. id interno fica só na consulta da API.
    codigo_empresa = normalizar_codigo_empresa(attributes.get('externoid') or empresa_id)
    empresa_csv = {
        'codigo_legado': codigo_empresa,
        'campo_chave': 'codigo_legado',  # Valor fixo
        'nro': codigo_empresa,
        'nome': attributes.get('nome', ''),  # p.nome - campo disponível na API
        'cnpj': attributes.get('cpfcnpj', ''),  # c.cnpj - usando o campo cpfcnpj da API
        'inscricao_estadual': '',  # Campo não disponível na API atual
        'cep': '',  # Campo não disponível na API atual
        'endereco': attributes.get('endereco', ''),  # ee.logradouro AS endereco - campo disponível na API
        'bairro': '',  # Campo não disponível na API atual
        'cidade': 'Manaus',  # Campo não disponível na API atual
        'uf': 'AM',  # Valor fixo pois não está disponível na API atual
        'telefone': '',  # Campo não disponível na API atual
        'email': '',  # Campo não disponível na API atual
        'site': '',  # Campo não disponível na API atual
        'nome_relatorio': None  # NULL AS nome_relatorio (valor nulo conforme query)
    }
    
    return empresa_csv

def gerar_csv_empresas():
    """
    Função principal para gerar o CSV das empresas
    """
    print("=" * 80)
    print("         🏢 GERAÇÃO DE CSV DE EMPRESAS - API eContador")
    print("=" * 80)
    
    # Verificar se token está disponível
    token = ler_token_config()
    if not token:
        print("❌ Falha ao carregar token do arquivo .config")
        return None
    
    # Coletar empresas da API
    empresas_api, headers = consultar_todas_empresas()
    
    if not empresas_api:
        print("❌ Nenhuma empresa foi coletada da API")
        return
    
    print(f"\n🔄 Convertendo {len(empresas_api)} empresas para formato CSV...")
    print("   (Buscando detalhes completos de cada empresa)")
    
    # Converter para formato CSV
    empresas_csv = []
    erros = []
    
    for i, empresa_api in enumerate(empresas_api, 1):
        try:
            empresa_id = empresa_api.get('id', '')
            
            # Buscar detalhes completos da empresa
            detalhes = None
            if empresa_id:
                detalhes = consultar_empresa_detalhada(empresa_id, headers)
            
            empresa_csv = mapear_empresa_para_csv(empresa_api, detalhes)
            empresas_csv.append(empresa_csv)
            
            if i % 5 == 0:
                print(f"  ✅ Processadas {i}/{len(empresas_api)} empresas...")
                # Pausa para não sobrecarregar a API
                time.sleep(1)
                
        except Exception as e:
            erros.append({'id': empresa_api.get('id', 'N/A'), 'erro': str(e)})
            print(f"  ❌ Erro ao processar empresa {empresa_api.get('id', 'N/A')}: {e}")
    
    if not empresas_csv:
        print("❌ Nenhuma empresa foi convertida com sucesso")
        return
    
    # Criar DataFrame
    print(f"\n📊 Criando DataFrame com {len(empresas_csv)} empresas...")
    df = pd.DataFrame(empresas_csv)
    
    # Gerar arquivo CSV
    nome_arquivo = "empresas_api.csv"
    
    try:
        df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig', sep=';')
        print(f"✅ CSV gerado com sucesso: {nome_arquivo}")
        
        # Estatísticas
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"  🏢 Total de empresas processadas: {len(empresas_csv)}")
        print(f"  ❌ Erros de conversão: {len(erros)}")
        print(f"  📋 Colunas no CSV: {len(df.columns)}")
        print(f"  💾 Arquivo gerado: {nome_arquivo}")
        
        # Mostrar preview dos dados
        print(f"\n👁️  PREVIEW DOS DADOS (primeiras 3 linhas):")
        print(df.head(3).to_string())
        
        # Salvar relatório de erros se houver
        if erros:
            arquivo_erros = "erros_empresas.json"
            with open(arquivo_erros, 'w', encoding='utf-8') as f:
                json.dump(erros, f, indent=2, ensure_ascii=False)
            print(f"\n⚠️  Relatório de erros salvo em: {arquivo_erros}")
        
        # Verificar campos com dados
        print(f"\n🔍 ANÁLISE DE PREENCHIMENTO DOS CAMPOS:")
        for coluna in df.columns:
            valores_nao_vazios = df[coluna].notna().sum() - (df[coluna] == '').sum()
            percentual = (valores_nao_vazios / len(df)) * 100
            status = "✅" if percentual > 0 else "⭕"
            print(f"  {status} {coluna:<20}: {valores_nao_vazios:3d}/{len(df)} ({percentual:5.1f}%)")
        
        return nome_arquivo
        
    except Exception as e:
        print(f"❌ Erro ao gerar CSV: {e}")
        return None

def processar_integracao_completa():
    """
    Função principal que executa todo o processo: coleta da API -> CSV -> POST para destino
    """
    print("=" * 80)
    print("    🚀 INTEGRAÇÃO COMPLETA DE EMPRESAS - eContador → Sistema Destino")
    print("=" * 80)
    
    # Etapa 1: Gerar CSV das empresas
    print("\n📋 ETAPA 1: Coletando empresas da API eContador...")
    arquivo_csv = gerar_csv_empresas()
    
    if not arquivo_csv:
        print("❌ Falha na geração do CSV. Processo interrompido.")
        return False
    
    # Etapa 2: Validar dados
    print("\n🔍 ETAPA 2: Validando dados do CSV...")
    validar_dados_empresas_csv(arquivo_csv)
    
    # Etapa 3: Enviar para API de destino
    print("\n📤 ETAPA 3: Enviando CSV para API de destino...")
    sucesso_envio = enviar_csv_para_api_target(arquivo_csv)
    
    if sucesso_envio:
        print("\n🎉 INTEGRAÇÃO COMPLETA FINALIZADA COM SUCESSO!")
        print(f"✅ Empresas coletadas da API eContador")
        print(f"✅ CSV gerado: {arquivo_csv}")
        print(f"✅ Dados enviados para sistema de destino")
        return True
    else:
        print("\n💥 FALHA NA INTEGRAÇÃO!")
        print(f"✅ CSV gerado: {arquivo_csv}")
        print(f"❌ Falha no envio para sistema de destino")
        return False

def validar_dados_empresas_csv(nome_arquivo):
    """
    Valida os dados do CSV de empresas gerado
    """
    if not nome_arquivo:
        return
    
    try:
        print(f"\n🔍 VALIDANDO DADOS DO CSV: {nome_arquivo}")
        
        # Ler o CSV gerado
        df = pd.read_csv(nome_arquivo, sep=';', encoding='utf-8-sig')
        
        print(f"  📊 Total de registros: {len(df)}")
        print(f"  📋 Total de colunas: {len(df.columns)}")
        
        # Verificar campos obrigatórios
        campos_obrigatorios = ['codigo_legado', 'nro', 'nome']
        
        for campo in campos_obrigatorios:
            if campo in df.columns:
                vazios = df[campo].isna().sum() + (df[campo] == '').sum()
                if vazios > 0:
                    print(f"  ⚠️  Campo '{campo}': {vazios} registros vazios")
                else:
                    print(f"  ✅ Campo '{campo}': todos preenchidos")
            else:
                print(f"  ❌ Campo obrigatório '{campo}' não encontrado")
        
        # Verificar duplicatas por CNPJ
        if 'cnpj' in df.columns:
            cnpjs_validos = df[df['cnpj'] != '']['cnpj']
            cnpjs_duplicados = cnpjs_validos.duplicated().sum()
            if cnpjs_duplicados > 0:
                print(f"  ⚠️  CNPJs duplicados encontrados: {cnpjs_duplicados}")
            else:
                print(f"  ✅ Nenhum CNPJ duplicado encontrado")
        
        # Verificar duplicatas por código legado
        if 'codigo_legado' in df.columns:
            codigos_duplicados = df['codigo_legado'].duplicated().sum()
            if codigos_duplicados > 0:
                print(f"  ⚠️  Códigos legados duplicados: {codigos_duplicados}")
            else:
                print(f"  ✅ Nenhum código legado duplicado")
        
        print(f"  ✅ Validação concluída")
        
    except Exception as e:
        print(f"  ❌ Erro na validação: {e}")

def explorar_estrutura_empresas():
    """
    Função para explorar a estrutura de dados das empresas na API
    """
    print("\n🔬 EXPLORANDO ESTRUTURA DE DADOS DAS EMPRESAS...")
    
    empresas_api, headers = consultar_todas_empresas()
    
    if not empresas_api:
        print("❌ Não foi possível coletar empresas para análise")
        return
    
    # Analisar estrutura dos dados
    todos_campos = set()
    campos_detalhados = set()
    
    print(f"\n📋 Analisando {len(empresas_api)} empresas...")
    
    # Analisar dados básicos
    for empresa in empresas_api[:5]:  # Apenas as primeiras 5 para não sobrecarregar
        attributes = empresa.get('attributes', {})
        todos_campos.update(attributes.keys())
    
    # Analisar dados detalhados
    for i, empresa in enumerate(empresas_api[:3]):  # Apenas as primeiras 3 para detalhes
        empresa_id = empresa.get('id', '')
        if empresa_id:
            print(f"  🔍 Analisando detalhes da empresa {empresa_id}...")
            detalhes = consultar_empresa_detalhada(empresa_id, headers)
            if detalhes:
                attributes_det = detalhes.get('attributes', {})
                campos_detalhados.update(attributes_det.keys())
            time.sleep(1)  # Pausa entre consultas
    
    print(f"\n📊 CAMPOS ENCONTRADOS:")
    print(f"  📋 Campos básicos ({len(todos_campos)}): {sorted(list(todos_campos))}")
    print(f"  🔍 Campos detalhados ({len(campos_detalhados)}): {sorted(list(campos_detalhados))}")
    
    # Campos únicos nos detalhes
    campos_exclusivos_detalhes = campos_detalhados - todos_campos
    if campos_exclusivos_detalhes:
        print(f"  ⭐ Campos exclusivos dos detalhes: {sorted(list(campos_exclusivos_detalhes))}")
    
    # Salvar análise
    analise = {
        'campos_basicos': sorted(list(todos_campos)),
        'campos_detalhados': sorted(list(campos_detalhados)),
        'campos_exclusivos_detalhes': sorted(list(campos_exclusivos_detalhes)),
        'total_empresas_analisadas': len(empresas_api),
        'timestamp': datetime.now().isoformat()
    }
    
    with open('analise_estrutura_empresas.json', 'w', encoding='utf-8') as f:
        json.dump(analise, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Análise salva em 'analise_estrutura_empresas.json'")

# Exemplo de uso
if __name__ == "__main__":
    # Executar integração completa automaticamente
    sucesso = processar_integracao_completa()
    if sucesso:
        print(f"\n🚀 INTEGRAÇÃO FINALIZADA COM SUCESSO!")
    else:
        print(f"\n💥 INTEGRAÇÃO FALHOU - Verifique os logs acima")