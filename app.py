import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from datetime import datetime
from PIL import Image, ImageOps
import pytesseract
from pyzbar.pyzbar import decode
from streamlit_gsheets import GSheetsConnection

funcionarios_db = {
    "ALAN SANTOS OLIVEIRA": "1111",
    "ARNALDO CALEBE OLIVEIRA GARCIA": "2222",
    "FELIPE FRANCO GUIMARAES": "3333",
    "FERNANDO HENRIQUE DOS SANTOS SILVA": "4444",
    "GUSTAVO ENRICK FRANCO": "5555",
    "LUISMAR JOSE GARCIA": "6666",
    "MARCEL SILVA DE ALMEIDA": "7777",
    "RAFAEL NOGUEIRA DA SILVA": "8888",
    "RENATO CARDOSO DOS SANTOS": "9999"
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

def pre_processar_imagem(img_pil):
    img_np = np.array(img_pil)
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return gray, thresh

def tratar_leitura_lacre(texto_ocr):
    # 1. Procura o padrão perfeito: 2 dígitos + Letra A-Z + 6 a 7 dígitos (ex: 25A022801)
    match_perfeito = re.findall(r'\b(\d{2}[A-Za-z]\d{6,7})\b', texto_ocr)
    if match_perfeito:
        return match_perfeito[0].upper()

    # 2. Busca após o bloco "NUMERADO" mesmo com quebra de linha ou espaço
    match_bloco = re.search(r'NUMERAD[O0]?[:\s]*([A-Z0-9]{8,11})', texto_ocr, re.IGNORECASE)
    if match_bloco:
        candidato = match_bloco.group(1).upper()
        # Se tiver 9 dígitos e o 3º caractere foi lido como número ('0' ou '4'), corrige para 'A'
        if len(candidato) >= 9 and candidato[2].isdigit():
            candidato = candidato[:2] + 'A' + candidato[3:9]
        return candidato

    # 3. Se achou sequência numérica de 9 dígitos iniciada por 24, 25 ou 26, reconstrói o prefixo 'A'
    match_numerico = re.findall(r'\b(2[3-7])([04])(\d{6})\b', texto_ocr)
    if match_numerico:
        ano, _, resto = match_numerico[0]
        return f"{ano}A{resto}"

    return ""

def extrair_serial_especifico(imagem_pil, tipo):
    # Tentativa 1: Barcode / QR Code
    for angulo in [0, 90, 180, 270]:
        img_rot = imagem_pil.rotate(angulo, expand=True)
        barcodes = decode(img_rot)
        if barcodes:
            barcodes = sorted(barcodes, key=lambda b: b.rect.top)
            for b in barcodes:
                texto = b.data.decode('utf-8').strip()
                if tipo == "Hidrômetro" and re.search(r'Z\d{2}[A-Z]{2}\d+', texto, re.I):
                    return re.search(r'Z\d{2}[A-Z]{2}\d+', texto, re.I).group(0).upper()
                if tipo == "Lacre" and re.search(r'\d{2}[A-Z]\d{6,}', texto, re.I):
                    return re.search(r'\d{2}[A-Z]\d{6,}', texto, re.I).group(0).upper()

    # Tentativa 2: OCR
    gray_img, thresh_img = pre_processar_imagem(imagem_pil)
    versoes_imagem = [Image.fromarray(gray_img), Image.fromarray(thresh_img), imagem_pil]

    for base_img in versoes_imagem:
        for angulo in [0, 90, 270]:
            img_rot = base_img.rotate(angulo, expand=True)
            texto_ocr = pytesseract.image_to_string(img_rot)

            if tipo == "Lacre":
                lacre_encontrado = tratar_leitura_lacre(texto_ocr)
                if lacre_encontrado:
                    return lacre_encontrado
            else:
                match_hidro = re.search(r'(Z\d{2}[A-Z]{2}\d{7,8}|[A-Z0-9]{2,4}BR\d{6,8}|\d{7})', texto_ocr, re.I)
                if match_hidro:
                    return match_hidro.group(0).upper().replace(' ', '')
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
quantidade = st.number_input(
    "Quantidade Retirada", 
    min_value=1, 
    max_value=1000, 
    value=10 if tipo_item == "Hidrômetro" else 100
)

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