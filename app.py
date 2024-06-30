from flask import Flask, render_template, request, redirect, url_for, flash, session
import fitz
import spacy
import zipfile
import requests
import os


app = Flask(__name__)
app.secret_key = 'a_hard_guess_string.__.'

@app.route('/')
def ranking():
   return render_template('ranking.html')

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return None

def extract_name(text):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return None
@app.route('/process_resumes', methods=['POST'])
def process_resumes():
    
    job_description = request.form['job_description']
    resume_zip = request.files['resume_zip']
    search_k = int(request.form.get('search_k'))
    
    if not job_description or not resume_zip:
        flash('Job description and resume file are required.', 'error')
        return redirect(url_for('ranking'))

    # Check if the uploaded file is a ZIP file
    if not zipfile.is_zipfile(resume_zip):
        flash('Please upload a ZIP file.', 'error')
        return redirect(url_for('ranking'))

    # Extract resumes from the zip file
    resumes = []
    resume_ids = []
    resume_metadatas = []
    with zipfile.ZipFile(resume_zip) as z:
        # Check if the zip file contains at least one PDF file
        pdf_files = [name for name in z.namelist() if name.endswith('.pdf')]
        if not pdf_files:
            flash('The ZIP file does not contain any PDF files.', 'error')
            return redirect(url_for('ranking'))

        for filename in pdf_files:
            # Extract the file name from the full path
            resume_name = os.path.basename(filename)
            with z.open(filename) as f:
                pdf_path = os.path.join('/tmp', resume_name)
                with open(pdf_path, 'wb') as pdf_file:
                    pdf_file.write(f.read())
                    pdf_file.close()
                text = extract_text_from_pdf(pdf_path)
                if text is not None:
                    resumes.append(text)
                    resume_ids.append(resume_name)
                    resume_metadatas.append({"entity": "resume", "source": "uploaded"})
                else:
                    continue
    payload = {
        "job_description": job_description,
        "resumes": resumes,
        "k": search_k
    }

    api_endpoint = "http://40.71.228.21:8000/process_resumes/"
    
    try:
        response = requests.post(api_endpoint, json=payload)
        results = response.json()
        #print(results)
        formatted_results = [{'rank': i + 1, 'name': extract_name(doc["content"])} for i, doc in enumerate(results)]
        return render_template('ranking.html', results=formatted_results)
    except Exception as e:
        return f"Error: {str(e)}"
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
