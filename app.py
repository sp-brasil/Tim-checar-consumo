import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Função principal para extrair informações do texto de uma página do PDF. (v3)
    """
    # Regex para informações do cabeçalho
    phone_pattern = re.compile(r'No\.\s*(\+\d+)')
    total_volume_pattern = re.compile(r'Volume total:\s*([\d,.]+)\s*MB', re.IGNORECASE)
    
    # Regex para as linhas de dados, agora mais robusta para capturar nomes de países com quebras de linha.
    data_line_pattern = re.compile(r'^\s*\d+\s+(\d{2}/\d{2}/\d{4})\s+(.*?)\s+([\d.]+\s*MB)', re.MULTILINE)

    phone_match = phone_pattern.search(text)
    total_volume_match = total_volume_pattern.search(text)
    
    # --- Extração e Limpeza do Telefone ---
    phone_number = None
    if phone_match:
        phone_raw = phone_match.group(1)
        if phone_raw.startswith("+55"):
            phone_number = phone_raw[3:] # Remove "+55"
        else:
            phone_number = phone_raw
    
    # --- Extração e Limpeza do Volume Total ---
    total_volume = None
    if total_volume_match:
        total_volume_raw = total_volume_match.group(1)
        total_volume_clean = total_volume_raw.replace(',', '')
        total_volume_float = float(total_volume_clean)
        # Formata para o padrão brasileiro (duas casas decimais com vírgula) - SEM MB
        total_volume = f"{total_volume_float:.2f}".replace('.', ',')

    if not phone_number or not total_volume:
        return []

    # Encontra todas as correspondências de linhas de dados no texto da página
    matches = data_line_pattern.findall(text)
    
    extracted_data = []
    for match in matches:
        # --- Limpeza do País ---
        country_raw = match[1]
        country = re.sub(r'\s+', ' ', country_raw).strip()

        # --- Limpeza do Realizado ---
        realizado_raw = match[2].replace('MB', '').strip()
        realizado_float = float(realizado_raw)
        # Formata para o padrão brasileiro (duas casas decimais com vírgula) - SEM MB
        realizado = f"{realizado_float:.2f}".replace('.', ',')

        extracted_data.append({
            "numero_do_telefone": phone_number,
            "data": match[0],
            "pais": country,
            "realizado": realizado,
            "volume_total": total_volume
        })
        
    return extracted_data


@app.route('/processar', methods=['POST'])
def process_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome de arquivo vazio"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        try:
            extracted_data = []
            with pdfplumber.open(file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                
                if full_text:
                    extracted_data = parse_text(full_text)
            
            return jsonify({"dados": extracted_data}), 200
        except Exception as e:
            return jsonify({"error": f"Erro ao processar o PDF: {str(e)}"}), 500

    return jsonify({"error": "Formato de arquivo inválido. Envie um PDF."}), 400

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
