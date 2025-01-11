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

class SentenceGenerator:
    def __init__(self, api_key):
        try:
            openai.api_key = api_key
            self.model_name = "gpt-3.5-turbo"
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def get_language_prompt(self, language_pair, difficulty, word_or_phrase):
        # Define language configurations
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
        
        prompt = f"""Create 3 short, {difficulty} level sentences using '{word_or_phrase}' in {config['to_lang']} with {config['from_lang']} translations for daily conversations.
        Format as JSON:
        {{
            "language_pair": "{config['lang_code']}",
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
        
    def generate_sentences(self, word_or_phrase, language_pair, difficulty):
        prompt = self.get_language_prompt(language_pair, difficulty, word_or_phrase)
        
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
            st.error(f"Error generating sentences: {str(e)}")
            return None

# Rest of the classes remain the same (AnkiDeckCreator and initialize_session_state)

def main():
    st.title("Anki Language Sentence Generator")
    
    # Initialize session state
    initialize_session_state()
    
    # Language pair selection with flags
    language_pairs = {
        "tr-en": "🇹🇷 Turkish → 🇬🇧 English",
        "tr-de": "🇹🇷 Turkish → 🇩🇪 German"
    }
    selected_language_pair = st.selectbox(
        "Select language pair:",
        options=list(language_pairs.keys()),
        format_func=lambda x: language_pairs[x]
    )
    
    # Difficulty level selection
    difficulty_levels = [
        "beginner",
        "basic",
        "intermediate",
        "upper-intermediate",
        "advanced"
    ]
    selected_difficulty = st.selectbox(
        "Select difficulty level:",
        options=difficulty_levels
    )
    
    # API Key input
    api_key = st.text_input("Enter your OpenAI API key:", type="password")
    
    # Only proceed if API key is provided
    if api_key:
        try:
            # Create new generator only if API key changes
            if api_key != st.session_state.api_key:
                st.session_state.sentence_gen = SentenceGenerator(api_key)
                st.session_state.api_key = api_key
                st.success("API key validated successfully!")
            
            # Input word/phrase
            word = st.text_input("Enter a word or phrase:")
            
            if st.button("Generate Sentences"):
                with st.spinner("Generating sentences..."):
                    sentences_data = st.session_state.sentence_gen.generate_sentences(
                        word,
                        selected_language_pair,
                        selected_difficulty
                    )
                    if sentences_data:
                        st.session_state.generated_sets.append(sentences_data)
                        st.success("Sentences generated successfully!")
            
            # Display all generated sets
            if st.session_state.generated_sets:
                st.subheader("Generated Sentence Sets")
                for idx, sentences_data in enumerate(st.session_state.generated_sets):
                    # Get language pair display text
                    lang_pair_display = language_pairs[sentences_data['language_pair']]
                    st.write(f"Set {idx + 1} - {lang_pair_display}")
                    
                    # Create a DataFrame for better display
                    df_data = []
                    for sentence in sentences_data['sentences']:
                        df_data.append({
                            sentences_data['language_pair'].split('-')[1].upper(): sentence['sentence'],
                            sentences_data['language_pair'].split('-')[0].upper(): sentence['translation'],
                            'Context': sentence['context']
                        })
                    df = pd.DataFrame(df_data)
                    st.dataframe(df)
                    
                    # Checkbox for selection
                    if st.checkbox(f"Select Set {idx + 1}", key=f"select_{idx}"):
                        if sentences_data not in st.session_state.selected_sets:
                            st.session_state.selected_sets.append(sentences_data)
                    else:
                        if sentences_data in st.session_state.selected_sets:
                            st.session_state.selected_sets.remove(sentences_data)
            
            # Create and download deck button
            if st.session_state.selected_sets:
                if st.button("Create Anki Deck from Selected Sets"):
                    with st.spinner("Creating Anki deck..."):
                        anki_creator = AnkiDeckCreator()
                        output_file = anki_creator.create_deck(st.session_state.selected_sets)
                        
                        with open(output_file, 'rb') as f:
                            deck_data = f.read()
                        
                        st.download_button(
                            label="Download Anki Deck",
                            data=deck_data,
                            file_name="language_deck.apkg",
                            mime="application/octet-stream"
                        )
                        
                        os.remove(output_file)
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Please check your API key and try again.")

if __name__ == "__main__":
    main()
