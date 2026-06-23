from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
import PyPDF2
import json
import os
import re

load_dotenv()
app = Flask(__name__)
CORS(app)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_quiz():
    try:
        text = ""
        num_questions = 5
        language = "fr"
        difficulty = "medium"
        
        if 'pdf' in request.files:
            pdf_file = request.files['pdf']
            num_questions = int(request.form.get('num_questions', 5))
            language = request.form.get('language', 'fr')
            difficulty = request.form.get('difficulty', 'medium')
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                t = page.extract_text()
                if t: text += t
        else:
            data = request.get_json()
            text = data.get('text', '')
            num_questions = data.get('num_questions', 5)
            language = data.get('language', 'fr')
            difficulty = data.get('difficulty', 'medium')
        
        if not text.strip():
            return jsonify({"error": "النص فارغ"}), 400
        
        lang_map = {"fr": "français", "ar": "العربية", "en": "English"}
        target_lang = lang_map.get(language, "français")
        
        # تعليمات حسب الصعوبة
        difficulty_instructions = {
            "easy": """NIVEAU FACILE:
- Questions directes basées sur des informations explicites dans le texte
- Vocabulaire simple
- Les réponses sont évidentes pour quelqu'un qui a lu le texte
- Pas de pièges, pas de double négation""",
            
            "medium": """NIVEAU MOYEN:
- Mélange de questions directes et de questions nécessitant de la compréhension
- Quelques détails subtils
- Reformulation des concepts du texte
- 1-2 questions un peu tricky""",
            
            "hard": """NIVEAU DIFFICILE:
- Questions nécessitant une analyse profonde du texte
- Détails précis (chiffres, dates, noms exacts)
- Inférences et déductions logiques
- Connections entre différentes parties du texte
- Vocabulaire technique""",
            
            "tricky": """NIVEAU MFAKHKHA (PIÈGES):
- Questions très tricky conçues pour tromper l'étudiant
- Utilise des doubles négations
- Inverse subtilement des concepts (ex: change "augmente" en "diminue")
- Modifie légèrement des chiffres ou des dates
- Mélange des concepts similaires mais différents
- Mots clés modifiés (ex: "toujours" au lieu de "souvent", "tous" au lieu de "certains")
- L'étudiant doit lire TRÈS attentivement pour détecter le piège
- 70% des questions doivent contenir un piège subtil"""
        }
        
        diff_instruction = difficulty_instructions.get(difficulty, difficulty_instructions["medium"])
        
        prompt = f"""Analyse le texte suivant et génère EXACTEMENT {num_questions} questions "Vrai/Faux" en {target_lang}.

{diff_instruction}

Varie les réponses: environ 50% vraies et 50% fausses.

Texte:
\"\"\"
{text[:15000]}
\"\"\"

IMPORTANT: Réponds UNIQUEMENT avec un JSON valide, sans markdown, sans ```, sans texte avant/après.
Format exact:
{{
  "questions": [
    {{"question": "...", "answer": true, "explanation": "Explication détaillée avec citation du texte"}},
    {{"question": "...", "answer": false, "explanation": "Explication détaillée avec citation du texte"}}
  ]
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.8 if difficulty == "tricky" else 0.7
            )
        )
        
        response_text = response.text.strip()
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        result = json.loads(response_text)
        return jsonify(result)
    
    except Exception as e:
        print(f"Erreur: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)