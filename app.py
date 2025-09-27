import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Função principal para extrair informações do texto de uma página do PDF. (v4 - Agregado)
    """
    # Regex para o número de telefone e para as linhas de dados
    phone_pattern = re.compile(r'No\.\s*(\+\d+)')
    data_line_pattern = re.compile(r'^\s*\d+\s+(\d{2}/\d{2}/\d{4})\s+(.*?)\s+([\d.]+\s*MB)', re.MULTILINE)

    phone_match = phone_pattern.search(text)
    
    # --- Extração e Limpeza do Telefone ---
    phone_number = None
    if phone_match:
        phone_raw = phone_match.group(1)
        if phone_raw.startswith("+55"):
            phone_number = phone_raw[3:] # Remove "+55"
        else:
            phone_number = phone_raw
    
    if not phone_number:
        return []

    # Encontra todas as correspondências de linhas de dados no texto da página
    matches = data_line_pattern.findall(text)
    
    total_consumption = 0.0
    chile_consumption = 0.0
    
    for match in matches:
        # --- Limpeza do País ---
        country_raw = match[1]
        country = re.sub(r'\s+', ' ', country_raw).strip()

        # --- Limpeza do Realizado ---
        realizado_raw = match[2].replace('MB', '').strip()
        realizado_float = float(realizado_raw)
        
        # --- Soma dos consumos ---
        total_consumption += realizado_float
        # Verifica se o país é "Chile" (ignorando maiúsculas/minúsculas)
        if country.lower() == 'chile':
            chile_consumption += realizado_float

    # Formata os totais para o padrão brasileiro (duas casas decimais com vírgula)
    formatted_total = f"{total_consumption:.2f}".replace('.', ',')
    formatted_chile = f"{chile_consumption:.2f}".replace('.', ',')

    summary_data = {
        "numero": phone_number,
        "consumo_total": formatted_total,
        "consumo_chile": formatted_chile
    }
        
    # Retorna uma lista com um único dicionário para simplificar o Make.com
    return [summary_data]


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
