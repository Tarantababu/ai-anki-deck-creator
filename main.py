import streamlit as st
import openai
import json
import genanki
from gtts import gTTS
import os
import random
from tempfile import NamedTemporaryFile
import shutil
import pandas as pd

def initialize_session_state():
    """Initialize session state variables"""
    if 'generated_sets' not in st.session_state:
        st.session_state.generated_sets = []
    if 'selected_sets' not in st.session_state:
        st.session_state.selected_sets = []
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'sentence_gen' not in st.session_state:
        st.session_state.sentence_gen = None
    if 'select_all' not in st.session_state:
        st.session_state.select_all = False

class SentenceGenerator:
    def __init__(self, api_key):
        try:
            openai.api_key = api_key
            self.model_name = "gpt-3.5-turbo"
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def validate_language_content(self, sentences_data):
        """Validate that sentences are in the correct language"""
        lang_pair = sentences_data['language_pair']
        target_lang = lang_pair.split('-')[1]  # 'de' or 'en'
        
        for sentence in sentences_data['sentences']:
            # Basic validation rules for German
            if target_lang == 'de':
                # Check for common German markers
                has_german_chars = any(char in sentence['sentence'].lower() for char in 'äöüß')
                has_german_words = any(word in sentence['sentence'].lower() for word in ['der', 'die', 'das', 'ist', 'und', 'in'])
                
                if not (has_german_chars or has_german_words):
                    # If validation fails, request regeneration with explicit language instruction
                    return False
                    
            # Basic validation for Turkish translation
            has_turkish_chars = any(char in sentence['translation'].lower() for char in 'ğıİöüşç')
            has_turkish_words = any(word in sentence['translation'].lower() for word in ['ve', 'bu', 'bir', 'için'])
            
            if not (has_turkish_chars or has_turkish_words):
                return False
                
        return True
    
    def get_language_prompt(self, language_pair, difficulty, word_or_phrase, topic):
        language_configs = {
            "tr-en": {
                "from_lang": "Turkish",
                "to_lang": "English",
                "lang_code": "tr-en"
            },
            "tr-de": {
                "from_lang": "Turkish",
                "to_lang": "German",
                "lang_code": "tr-de"
            }
        }
        
        config = language_configs[language_pair]
        
        # Enhanced prompt with explicit language instructions
        prompt = f"""Create 3 short, {difficulty} level sentences using '{word_or_phrase}' in {config['to_lang']} with {config['from_lang']} translations for {topic.lower()}.
        IMPORTANT: 
        - For {config['to_lang']} sentences, use ONLY {config['to_lang']} language
        - For {config['from_lang']} translations, use ONLY {config['from_lang']} language
        - If generating German sentences, include German articles (der/die/das) and proper German sentence structure
        - Ensure Turkish translations use Turkish characters (ğ, ı, İ, ö, ü, ş, ç) where appropriate
        
        Format as JSON:
        {{
            "language_pair": "{config['lang_code']}",
            "topic": "{topic}",
            "word": "{word_or_phrase}",
            "sentences": [
                {{
                    "id": 1,
                    "sentence": "",
                    "translation": "",
                    "context": "",
                    "tags": []
                }}
            ]
        }}"""
        return prompt
        
    def generate_sentences_batch(self, words, language_pair, difficulty, topic):
        all_sentences_data = []
        
        for word in words:
            word = word.strip()
            if word:  # Skip empty strings
                sentences_data = self.generate_sentences(word, language_pair, difficulty, topic)
                if sentences_data:
                    # Validate language content
                    max_attempts = 3
                    attempt = 1
                    while not self.validate_language_content(sentences_data) and attempt <= max_attempts:
                        st.warning(f"Regenerating sentences for '{word}' due to language validation failure (attempt {attempt}/{max_attempts})")
                        sentences_data = self.generate_sentences(word, language_pair, difficulty, topic)
                        attempt += 1
                    
                    if attempt <= max_attempts:
                        all_sentences_data.append(sentences_data)
                    else:
                        st.error(f"Failed to generate valid sentences for '{word}' after {max_attempts} attempts")
        
        return all_sentences_data
    
    def generate_sentences(self, word_or_phrase, language_pair, difficulty, topic):
        prompt = self.get_language_prompt(language_pair, difficulty, word_or_phrase, topic)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            content = response['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            st.error(f"Error generating sentences for word '{word_or_phrase}': {str(e)}")
            return None

# [Rest of the classes remain the same...]

def main():
    st.title("Anki Language Sentence Generator")
    
    initialize_session_state()
    
    language_pairs = {
        "tr-en": "🇹🇷 Turkish → 🇬🇧 English",
        "tr-de": "🇹🇷 Turkish → 🇩🇪 German"
    }
    
    # [Previous UI code remains the same until the generated sets section...]
    
    if st.session_state.generated_sets:
        st.subheader("Generated Sentence Sets")
        
        # Add "Select All" checkbox
        select_all = st.checkbox("Select All Sets", value=st.session_state.select_all)
        
        # Update all checkboxes if "Select All" status changes
        if select_all != st.session_state.select_all:
            st.session_state.select_all = select_all
            if select_all:
                st.session_state.selected_sets = st.session_state.generated_sets.copy()
            else:
                st.session_state.selected_sets = []
        
        for idx, sentences_data in enumerate(st.session_state.generated_sets):
            lang_pair_display = language_pairs[sentences_data['language_pair']]
            st.write(f"Set {idx + 1} - {lang_pair_display}")
            st.write(f"Topic: {sentences_data.get('topic', 'General')}")
            st.write(f"Word: {sentences_data.get('word', '')}")
            
            df_data = []
            for sentence in sentences_data['sentences']:
                df_data.append({
                    sentences_data['language_pair'].split('-')[1].upper(): sentence['sentence'],
                    sentences_data['language_pair'].split('-')[0].upper(): sentence['translation'],
                    'Context': sentence['context']
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df)
            
            # Update individual checkboxes based on "Select All" status
            is_selected = st.checkbox(
                f"Select Set {idx + 1}",
                key=f"select_{idx}",
                value=sentences_data in st.session_state.selected_sets
            )
            
            if is_selected and sentences_data not in st.session_state.selected_sets:
                st.session_state.selected_sets.append(sentences_data)
            elif not is_selected and sentences_data in st.session_state.selected_sets:
                st.session_state.selected_sets.remove(sentences_data)
    
    # [Rest of the code remains the same...]

if __name__ == "__main__":
    main()
