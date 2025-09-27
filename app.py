import os
import re
import pdfplumber
from flask import Flask, request, jsonify

app = Flask(__name__)

def parse_text(text):
    """
    Função principal para extrair informações do texto de uma página do PDF.
    """
    data = []

    # Padrões de Regex para encontrar as informações
    phone_pattern = re.compile(r'No\.\s*(\+\d{10,})')
    total_volume_pattern = re.compile(r'Volume total:\s*([\d,.]+)\s*MB', re.IGNORECASE)
    data_line_pattern = re.compile(r'\d+\s+(\d{2}/\d{2}/\d{4})\s+([A-Za-zÁ-ú\s]+?)\s+([\d,.]+\s*MB)')

    phone_match = phone_pattern.search(text)
    total_volume_match = total_volume_pattern.search(text)

    phone_number = phone_match.group(1) if phone_match else None
    total_volume_raw = total_volume_match.group(1) if total_volume_match else None
    
    if total_volume_raw:
        # Limpa o valor para um formato numérico padrão antes de formatar
        total_volume_clean = total_volume_raw.replace('.', '').replace(',', '.')
        total_volume = f"{float(total_volume_clean):.2f}".replace('.', ',') + "MB"
    else:
        total_volume = None

    if not phone_number or not total_volume:
        return [] # Retorna vazio se não encontrar informações essenciais

    for line in text.split('\n'):
        match = data_line_pattern.search(line)
        if match:
            # Limpa o nome do país de possíveis quebras de linha ou espaços extras
            country = ' '.join(match.group(2).split()).strip()
            
            # Formata o valor realizado
            realizado_raw = match.group(3).replace('MB', '').strip()
            realizado_clean = realizado_raw.replace('.', '').replace(',', '.')
            realizado = f"{float(realizado_clean):.2f}".replace('.', ',') + "MB"
            
            data.append({
                "numero_do_telefone": phone_number,
                "data": match.group(1),
                "pais": country,
                "realizado": realizado,
                "volume_total": total_volume
            })
            
    return data


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
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_data.extend(parse_text(text))
            
            return jsonify({"dados": extracted_data}), 200
        except Exception as e:
            return jsonify({"error": f"Erro ao processar o PDF: {str(e)}"}), 500

    return jsonify({"error": "Formato de arquivo inválido. Envie um PDF."}), 400

if __name__ == '__main__':
    # Usado para testes locais, não para produção no Render
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))