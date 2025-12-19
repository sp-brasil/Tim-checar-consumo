import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Função robusta para extrair informações agregadas (v5 - Ultra Flexível).
    """
    # Limpeza inicial: remove aspas que podem vir na extração de tabelas
    text = text.replace('"', '').replace("'", "")
    
    # Regex flexível para o número de telefone (captura com ou sem +55)
    phone_pattern = re.compile(r'No\.\s*(\+?\d+)')
    # Regex flexível para Volume Total (pega o número antes de MB)
    total_volume_pattern = re.compile(r'Volume total:\s*([\d,.]+)', re.IGNORECASE)
    
    phone_match = phone_pattern.search(text)
    total_volume_match = total_volume_pattern.search(text)
    
    # --- Extração do Telefone ---
    phone_number = "Não encontrado"
    if phone_match:
        phone_raw = phone_match.group(1)
        phone_number = phone_raw[3:] if phone_raw.startswith("+55") else phone_raw
    
    # --- Extração do Volume Total do Cabeçalho ---
    total_header_volume = "0,00"
    if total_volume_match:
        val = total_volume_match.group(1).replace(',', '')
        total_header_volume = f"{float(val):.2f}".replace('.', ',')

    # Regex para identificar a linha pela DATA (formato DD/MM/AAAA)
    # Captura a data e o restante da linha para processamento manual
    date_regex = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.*)')

    total_sum = 0.0
    chile_sum = 0.0
    
    lines = text.split('\n')
    for line in lines:
        match = date_regex.search(line)
        if match:
            data_str = match.group(1)
            resto_linha = match.group(2)
            
            # Busca todos os valores de consumo na linha (números seguidos de MB)
            consumos = re.findall(r'([\d.]+)\s*MB', resto_linha, re.IGNORECASE)
            
            if consumos:
                # O primeiro valor de MB na linha costuma ser o 'Realizado'
                valor_realizado = float(consumos[0])
                total_sum += valor_realizado
                
                # Verifica se a palavra 'Chile' aparece em qualquer lugar desta linha
                if 'chile' in line.lower():
                    chile_sum += valor_realizado

    # Formatação Final
    formatted_total = f"{total_sum:.2f}".replace('.', ',')
    formatted_chile = f"{chile_sum:.2f}".replace('.', ',')

    # Se o total somado for 0, usamos o volume do cabeçalho como fallback para o total
    if total_sum == 0 and total_header_volume != "0,00":
        formatted_total = total_header_volume

    return [{
        "numero": phone_number,
        "consumo_total": formatted_total,
        "consumo_chile": formatted_chile
    }]

@app.route('/processar', methods=['POST'])
def process_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file and file.filename.lower().endswith('.pdf'):
        try:
            with pdfplumber.open(file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += (page.extract_text() or "") + "\n"
                
                dados = parse_text(full_text)
                return jsonify({"dados": dados}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Arquivo inválido"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
