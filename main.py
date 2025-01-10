import streamlit as st
import openai
import json
import genanki
from gtts import gTTS
import os
import random
import shutil
from tempfile import NamedTemporaryFile
import pandas as pd

class SentenceGenerator:
    def __init__(self, api_key, language_pair):
        self.api_key = api_key
        openai.api_key = api_key
        self.language_pair = language_pair
        self.model_name = "gpt-3.5-turbo"
    
    def generate_sentences(self, word_or_phrase):
        if self.language_pair == "en-tr":
            prompt = f"""Create 3 short, simple sentences using '{word_or_phrase}' in English with Turkish translations.
            Format as JSON:
            {{
                "language_pair": "en-tr",
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
        elif self.language_pair == "de-tr":
            prompt = f"""Create 3 short, simple sentences using '{word_or_phrase}' in German with Turkish translations.
            Format as JSON:
            {{
                "language_pair": "de-tr",
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
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            content = response.choices[0].message["content"]
            return json.loads(content)
        except openai.error.APIError as e:
            st.error(f"OpenAI API Error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Error generating sentences: {str(e)}")
            return None

class AnkiDeckCreator:
    def __init__(self):
        self.model = genanki.Model(
            random.randrange(1 << 30, 1 << 31),
            'Sentence Model with Audio',
            fields=[
                {'name': 'Sentence'},
                {'name': 'Translation'},
                {'name': 'Context'},
                {'name': 'Audio'}
            ],
            templates=[{
                'name': 'Card 1',
                'qfmt': '{{Sentence}}<br>{{Audio}}',
                'afmt': '{{FrontSide}}<hr>{{Translation}}<br><br>Context: {{Context}}',
            }]
        )
    
    def create_audio(self, text):
        """Create audio file and return the filename"""
        with NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            tts = gTTS(text=text, lang='en')
            tts.save(temp_file.name)
            return temp_file.name
    
    def create_deck(self, all_sentences_data, deck_name="Language Learning"):
        deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)
        media_files = []
        
        for sentences_data in all_sentences_data:
            for sentence in sentences_data['sentences']:
                # Create audio file
                audio_filename = f"sentence_{random.randrange(1 << 30, 1 << 31)}.mp3"
                temp_audio = self.create_audio(sentence['sentence'])
                
                # Copy the file to the destination directory
                shutil.copy(temp_audio, audio_filename)
                media_files.append(audio_filename)
                
                note = genanki.Note(
                    model=self.model,
                    fields=[
                        sentence['sentence'],
                        sentence['translation'],
                        sentence['context'],
                        f'[sound:{audio_filename}]'
                    ]
                )
                deck.add_note(note)
        
        # Create package
        package = genanki.Package(deck)
        package.media_files = media_files
        output_file = 'language_deck.apkg'
        package.write_to_file(output_file)
        
        # Clean up audio files
        for audio_file in media_files:
            try:
                os.remove(audio_file)
            except OSError:
                pass
                
        return output_file

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

def main():
    st.title("Anki Language Sentence Generator")
    
    # Initialize session state
    initialize_session_state()
    
    # API Key input
    api_key = st.text_input("Enter your OpenAI API key:", type="password")
    
    # Language pair input
    language_pair = st.selectbox("Select language pair:", ["en-tr", "de-tr"])
    
    # Only proceed if API key is provided
    if api_key:
        try:
            # Create new generator only if API key or language pair changes
            if api_key != st.session_state.api_key or language_pair != st.session_state.language_pair:
                st.session_state.sentence_gen = SentenceGenerator(api_key, language_pair)
                st.session_state.api_key = api_key
                st.session_state.language_pair = language_pair
                st.success("API key and language pair validated successfully!")
            
            # Input word/phrase
            word = st.text_input("Enter a word or phrase:")
            
            if st.button("Generate Sentences"):
                with st.spinner("Generating sentences..."):
                    sentences_data = st.session_state.sentence_gen.generate_sentences(word)
                    if sentences_data:
                        st.session_state.generated_sets.append(sentences_data)
                        st.success("Sentences generated successfully!")
            
            # Display all generated sets
            if st.session_state.generated_sets:
                st.subheader("Generated Sentence Sets")
                for idx, sentences_data in enumerate(st.session_state.generated_sets):
                    st.write(f"Set {idx + 1} - Word/Phrase: {sentences_data['sentences'][0]['sentence'].split()[0]}")
                    
                    # Create a DataFrame for better display
                    df_data = []
                    for sentence in sentences_data['sentences']:
                        df_data.append({
                            'Sentence': sentence['sentence'],
                            'Translation': sentence['translation'],
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
                        
                        # Read the file for download
                        with open(output_file, 'rb') as f:
                            deck_data = f.read()
                        
                        # Create download button
                        st.download_button(
                            label="Download Anki Deck",
                            data=deck_data,
                            file_name="language_deck.apkg",
                            mime="application/octet-stream"
                        )
                        
                        # Clean up the file
                        os.remove(output_file)
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Please check your API key and try again.")

if __name__ == "__main__":
    main()
