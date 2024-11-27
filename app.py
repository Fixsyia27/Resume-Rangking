import streamlit as st
import os
import spacy
import fitz
import re
from werkzeug.utils import secure_filename
import io
import pathlib
from pymongo import MongoClient
from bson.objectid import ObjectId


# Path and MongoDB connection setup
UPLOAD_FOLDER = 'static/uploaded_resumes'
st.set_page_config(page_title="Resume Screening", page_icon="📄")

# MongoDB setup (make sure to replace the Mongo URI)
client = MongoClient('Your Mongo URI here')
db = client['your_db_name']  # Replace with your actual db name
resumeFetchedData = db.resumeFetchedData
IRS_USERS = db.IRS_USERS

# Spacy model
nlp = spacy.load('assets/ResumeModel/output/model-best')

# Allowed file extensions
def allowedExtension(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['docx', 'pdf']

# Streamlit app
st.title("Resume Screening Application")

def upload_resume():
    uploaded_file = st.file_uploader("Upload your resume", type=['pdf', 'docx'])
    
    if uploaded_file is not None:
        filename = secure_filename(uploaded_file.name)
        # Save the file temporarily
        with open(os.path.join(UPLOAD_FOLDER, filename), "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success("Resume uploaded successfully!")
        return os.path.join(UPLOAD_FOLDER, filename)
    
    return None


def process_resume(file_path):
    # Open the resume file
    doc = fitz.open(file_path)
    text_of_resume = ""
    for page in doc:
        text_of_resume += page.get_text()

    # Extract entities using Spacy
    doc = nlp(text_of_resume)
    entities = {"NAME": None, "LINKEDIN LINK": None, "SKILLS": [], "CERTIFICATION": [], "WORKED AS": [], "YEARS OF EXPERIENCE": []}
    
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities["NAME"] = ent.text
        elif ent.label_ == "URL":
            entities["LINKEDIN LINK"] = ent.text
        elif ent.label_ == "SKILL":
            entities["SKILLS"].append(ent.text)
        elif ent.label_ == "CERTIFICATION":
            entities["CERTIFICATION"].append(ent.text)
        elif ent.label_ == "WORKED AS":
            entities["WORKED AS"].append(ent.text)
        elif ent.label_ == "YEARS OF EXPERIENCE":
            entities["YEARS OF EXPERIENCE"].append(ent.text)
    
    return entities


def save_resume_data(entities, file_path):
    # Save the extracted data to MongoDB
    user_id = st.session_state.get('user_id', None)
    
    if user_id:
        resume_data_annotated = " ".join([val for key, value in entities.items() if isinstance(value, list) for val in value])
        resume_data = {
            "UserId": ObjectId(user_id),
            "Name": entities["NAME"],
            "LINKEDIN LINK": entities["LINKEDIN LINK"],
            "SKILLS": entities["SKILLS"],
            "CERTIFICATION": entities["CERTIFICATION"],
            "WORKED AS": entities["WORKED AS"],
            "YEARS OF EXPERIENCE": entities["YEARS OF EXPERIENCE"],
            "ResumeTitle": os.path.basename(file_path),
            "ResumeAnnotatedData": resume_data_annotated,
            "ResumeData": entities,
        }

        result = resumeFetchedData.insert_one(resume_data)
        if result:
            st.success("Resume data saved successfully!")
        else:
            st.error("Error saving resume data.")


def view_resume_details(user_id):
    result = resumeFetchedData.find_one({"UserId": ObjectId(user_id)})
    if result:
        st.json(result)
    else:
        st.error("No resume data found.")


# Main interface
if 'user_id' in st.session_state:
    st.sidebar.write(f"Logged in as {st.session_state['user_name']}")

    st.sidebar.header("Upload Resume")
    file_path = upload_resume()
    
    if file_path:
        entities = process_resume(file_path)
        st.write("Extracted Information:")
        st.json(entities)

        if st.button("Save Resume Data"):
            save_resume_data(entities, file_path)

    st.sidebar.header("View Resume Details")
    if st.button("View My Resume"):
        view_resume_details(st.session_state['user_id'])

else:
    st.warning("Please log in first.")
