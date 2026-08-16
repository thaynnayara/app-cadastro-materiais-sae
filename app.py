import streamlit as st
import pandas as pd
import re
from datetime import datetime
from PIL import Image, ImageOps
import pytesseract
from pyzbar.pyzbar import decode
from streamlit_gsheets import GSheetsConnection

funcionarios_db = {
    "Arnaldo Calebe (Operacional)": "1234",
    "Carlos (Operacional)": "5678",
    "Ana (Manutenção)": "9012"
}

st.set_page_config(page_title="Saída de Materiais - SAE", layout="centered")
st.title("💧 Registro de Saída de Materiais")

# --- 1. IDENTIFICAÇÃO ---
st.subheader("1. Identificação do Funcionário")
funcionario_selecionado = st.selectbox("Selecione seu Nome:", [""] + list(funcionarios_db.keys()))

pin_digitado = ""
if funcionario_selecionado != "":
    pin_digitado = st.text_input("Digite seu PIN de 4 dígitos:", type="password", max_chars=4)

# --- 2. LEITURA DO MATERIAL ---
st.subheader("2. Leitura do Material")
tipo_item = st.radio("Selecione o Item:", ["Hidrômetro", "Lacre"])

foto_capturada = st.camera_input("Tire a foto da etiqueta")

def extrair_serial_especifico(imagem_pil, tipo):
    # Tentativa 1: Decodificar código de barras em 4 rotações
    for angulo in [0, 90, 180, 270]:
        img_rot = imagem_pil.rotate(angulo, expand=True)
        barcodes = decode(img_rot)
        for b in barcodes:
            texto = b.data.decode('utf-8').strip()
            if tipo == "Hidrômetro" and re.search(r'Z\d{2}[A-Z]{2}\d+', texto, re.I):
                return re.search(r'Z\d{2}[A-Z]{2}\d+', texto, re.I).group(0).upper()
            if tipo == "Lacre" and re.search(r'\d{2}[A-Z]\d{6,}', texto, re.I):
                return re.search(r'\d{2}[A-Z]\d{6,}', texto, re.I).group(0).upper()

    # Tentativa 2: OCR com correção de orientação e escala de cinza
    img_gray = ImageOps.grayscale(imagem_pil)
    for angulo in [0, 90, 270]:
        img_rot = img_gray.rotate(angulo, expand=True)
        texto_ocr = pytesseract.image_to_string(img_rot)
        
        if tipo == "Hidrômetro":
            match = re.search(r'(Z26BR\d{7,8}|[A-Z0-9]{2,4}BR\d{6,8}|\d{7})', texto_ocr, re.I)
            if match:
                return match.group(0).upper()
        else:
            match = re.search(r'(\d{2}[A-Z]\d{6,7})', texto_ocr, re.I)
            if match:
                return match.group(0).upper()
    return ""

serial_detectado = ""
if foto_capturada is not None:
    img = Image.open(foto_capturada)
    serial_detectado = extrair_serial_especifico(img, tipo_item)
    if serial_detectado:
        st.success(f"Código isolado com sucesso: **{serial_detectado}**")
    else:
        st.warning("Código não detectado automaticamente. Você pode digitar abaixo.")

serial_inicial = st.text_input("Serial Inicial:", value=serial_detectado)
quantidade = st.number_input("Quantidade Retirada", min_value=1, max_value=1000, value=10 if tipo_item == "Hidrômetro" else 100)

# --- 3. GRAVAÇÃO ---
if st.button("Registrar Saída"):
    if funcionario_selecionado == "":
        st.error("Selecione um funcionário.")
    elif pin_digitado != funcionarios_db.get(funcionario_selecionado):
        st.error("PIN incorreto!")
    elif not serial_inicial:
        st.warning("Informe o serial inicial.")
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
            
            lista_seriais = [f"{prefixo}{str(numero_inicial + i).zfill(tamanho_numero)}" for i in range(quantidade)]
            
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
                st.success(f"Saída de {quantidade} {tipo_item}s salva na nuvem!")
                st.dataframe(df_novos_dados)
            except Exception as e:
                st.error(f"Erro ao conectar com a planilha: {e}")
        else:
            st.error("Formato inválido. O serial deve conter números no final.")