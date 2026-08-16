import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- DADOS DE FUNCIONÁRIOS E PINs ---
funcionarios_db = {
    "Alan (Equipe Rua 1)": "1234",
    "Arnaldo Calebe (Operacional)": "4321",
    "Fernando ": "3214",
    "Gustavo Henrick": "2143",
    "Rafael ": "1432",
    "Felipe": "0123",
    "Marcel": "3210"

}

st.set_page_config(page_title="Saída de Materiais - SAE", layout="centered")
st.title("💧 Registro de Saída de Materiais")

# --- ÁREA DE AUTENTICAÇÃO ---
st.subheader("1. Identificação do Funcionário")
funcionario_selecionado = st.selectbox("Selecione seu Nome:", [""] + list(funcionarios_db.keys()))

pin_digitado = ""
if funcionario_selecionado != "":
    pin_digitado = st.text_input("Digite seu PIN de 4 dígitos:", type="password", max_chars=4)

# --- ÁREA DE CADASTRO DO MATERIAL ---
st.subheader("2. Leitura do Material")
tipo_item = st.radio("Selecione o Item:", ["Hidrômetro", "Lacre"])
serial_inicial = st.text_input("Serial Inicial (Use a câmera do teclado para ler):")
quantidade = st.number_input("Quantidade Retirada", min_value=1, max_value=1000, value=10)

# --- BOTÃO DE REGISTRO E LÓGICA DE NUVEM ---
if st.button("Registrar Saída"):
    if funcionario_selecionado == "":
        st.error("Por favor, selecione um funcionário.")
    elif pin_digitado != funcionarios_db.get(funcionario_selecionado):
        st.error("PIN incorreto! Registro bloqueado.")
    elif not serial_inicial:
        st.warning("Por favor, preencha o serial inicial.")
    else:
        match = re.search(r'^(.*?)(\d+)$', serial_inicial.strip())
        
        if match:
            prefixo = match.group(1)
            numero_str = match.group(2)
            tamanho_numero = len(numero_str)
            numero_inicial = int(numero_str)
            
            agora = datetime.now()
            data_atual = agora.strftime("%d/%m/%Y")
            hora_atual = agora.strftime("%H:%M:%S")
            
            lista_seriais = []
            
            for i in range(quantidade):
                num_atual = str(numero_inicial + i).zfill(tamanho_numero)
                lista_seriais.append(f"{prefixo}{num_atual}")
            
            # Prepara os dados para envio
            df_novos_dados = pd.DataFrame({
                'Data': [data_atual] * quantidade,
                'Hora': [hora_atual] * quantidade,
                'Funcionário': [funcionario_selecionado] * quantidade,
                'Tipo': [tipo_item] * quantidade,
                'Serial': lista_seriais,
                'Status': ['Em Uso'] * quantidade
            })
            
            try:
                # Conecta ao Google Sheets e envia os dados
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # Lê a planilha atual (para não apagar o que já existe)
                df_existente = conn.read()
                
                # Junta os dados antigos com os novos
                df_atualizado = pd.concat([df_existente, df_novos_dados], ignore_index=True)
                
                # Atualiza a planilha na nuvem
                conn.update(data=df_atualizado)
                
                st.success(f"Saída de {quantidade} {tipo_item}s registrada com sucesso na nuvem!")
                st.dataframe(df_novos_dados)
                
            except Exception as e:
                st.error(f"Erro ao conectar com a planilha: {e}")
        else:
            st.error("Formato inválido. O serial deve terminar com números.")