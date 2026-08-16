import streamlit as st
import pandas as pd
import re
from datetime import datetime
from PIL import Image
import pytesseract
from streamlit_gsheets import GSheetsConnection

# --- BANCO DE DADOS SIMULADO ---
funcionarios_db = {
    "Arnaldo Calebe": "1234",
    "Alan": "5678",
    "Gustavo Henrick": "9012",
    "Thaynna Yara": "3456",
    "Rafael": "7890",
    "Felipe": "2345",
    "Marcel": "6789",
    "Luismar": "0123",
    "Renato": "4567",
    "Teste": "0000"
}

st.set_page_config(page_title="Saída de Materiais - SAE", layout="centered")
st.title("💧 Registro de Saída de Materiais")

# --- 1. AUTENTICAÇÃO ---
st.subheader("1. Identificação do Funcionário")
funcionario_selecionado = st.selectbox("Selecione seu Nome:", [""] + list(funcionarios_db.keys()))

pin_digitado = ""
if funcionario_selecionado != "":
    pin_digitado = st.text_input("Digite seu PIN de 4 dígitos:", type="password", max_chars=4)

# --- 2. LEITURA DO MATERIAL ---
st.subheader("2. Leitura do Material")
tipo_item = st.radio("Selecione o Item:", ["Hidrômetro", "Lacre"])

# Captura de foto direto no app
foto_capturada = st.camera_input("Tire a foto da etiqueta/código")

serial_sugerido = ""
if foto_capturada is not None:
    imagem = Image.open(foto_capturada)
    # Extrai o texto da imagem via OCR
    texto_extraido = pytesseract.image_to_string(imagem)
    
    # Busca padrões alfanuméricos comuns (ex: Z26BR0192659 ou 25A022801)
    padroes = re.findall(r'[A-Za-z0-9]{7,15}', texto_extraido)
    if padroes:
        serial_sugerido = padroes[0]
        st.info(f"Código detectado pela foto: **{serial_sugerido}**")

# Campo de texto (preenchido pela foto ou editável manualmente)
serial_inicial = st.text_input(
    "Serial Inicial:", 
    value=serial_sugerido if serial_sugerido else ""
)

quantidade = st.number_input("Quantidade Retirada", min_value=1, max_value=1000, value=10)

# --- 3. PROCESSAMENTO ---
if st.button("Registrar Saída"):
    if funcionario_selecionado == "":
        st.error("Por favor, selecione um funcionário.")
    elif pin_digitado != funcionarios_db.get(funcionario_selecionado):
        st.error("PIN incorreto! Registro bloqueado.")
    elif not serial_inicial:
        st.warning("Por favor, informe ou fotografe o serial inicial.")
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
            
            df_novos_dados = pd.DataFrame({
                'Data': [data_atual] * quantidade,
                'Hora': [hora_atual] * quantidade,
                'Funcionário': [funcionario_selecionado] * quantidade,
                'Tipo': [tipo_item] * quantidade,
                'Serial': lista_seriais,
                'Status': ['Em Uso'] * quantidade
            })
            
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_existente = conn.read()
                df_atualizado = pd.concat([df_existente, df_novos_dados], ignore_index=True)
                conn.update(data=df_atualizado)
                st.success(f"Saída de {quantidade} {tipo_item}s registrada com sucesso na nuvem!")
                st.dataframe(df_novos_dados)
            except Exception as e:
                st.error(f"Erro ao conectar com a planilha: {e}")
        else:
            st.error("Formato inválido. O serial deve terminar com números.")