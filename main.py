import base64
from dotenv import load_dotenv
from google.cloud import texttospeech
from google.oauth2 import service_account
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import os
import pandas as pd
import random
import streamlit as st


# Set up 
load_dotenv(verbose=True, dotenv_path='.env')
JSON_FILE_PATH = os.environ.get("JSON_FILE_PATH")
SHEET_KEY = os.environ.get("SHEET_KEY")
st.set_page_config(page_title="AI English", page_icon="🤖")
st.markdown("""<style>.big-font {font-size:50px !important;}</style>""", unsafe_allow_html=True)

# Load spreadsheet data
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/cloud-translation']
# credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE_PATH, scope) # For local
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope) # For Streamlit Share
gs = gspread.authorize(credentials)
spreadsheet_key = SHEET_KEY
wb = gs.open_by_key(spreadsheet_key)
ws = wb.worksheet("dictation")

# Setting for GTTS
client = texttospeech.TextToSpeechClient(credentials=credentials)
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Neural2-I"
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Set up session state to store generated text
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""
if "japanese_text" not in st.session_state:
    st.session_state.japanese_text = ""
if "hints" not in st.session_state:
    st.session_state.hints = ""
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "gs_data" not in st.session_state:
    st.session_state.gs_data = ws.get_all_values()

# Setting for DataFrame
df = pd.DataFrame(st.session_state.gs_data)
df.columns = list(df.loc[0, :])
df.drop(0, inplace=True)
df.reset_index(inplace=True)
df.drop('index', axis=1, inplace=True)

st.title("English Dictation!")

# Get theme input
themes = df.theme.unique()
theme = st.selectbox("Select theme which you want to hear.", themes)
random_theme = st.checkbox("Random Theme: If this on, AI generate English sentence randomly from all themes.")
if random_theme:
    theme = ""
if theme:
    df = df[df["theme"] == theme]
n = len(df)
sentences = df["sentences"].to_list()
hints = df["hints"].to_list()
translations = df["translations"].to_list()

# Generate button and AI start generating sentence
st.header("Generate English🤖")
st.write("Click the 'Generate' button to generate audio.")
if st.button("Generate"):
    rand_int = random.randint(0, n-1)
    generated_text = sentences[rand_int]
    
    # Get japanese translation from dataframe
    japanese_text = translations[rand_int]
    
    # Get hints from dataframe
    hint = json.loads(hints[rand_int])

    # Convert generated text to audio using gTTS
    tts = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=generated_text),
        voice=voice,
        audio_config=audio_config
        )
    audio_content = tts.audio_content
    audio_base = "data:audio/ogg;base64,%s"%(base64.b64encode(audio_content).decode())
    # audio_bytes = bytes(audio_content)
    st.write(generated_text)
    mymidia_placeholder = st.empty()

    # Update session state with generated text and translation
    st.session_state.generated_text = generated_text
    st.session_state.japanese_text = japanese_text
    st.session_state.hints = hint
    st.session_state.audio_file = """
                    <audio controls autoplay=True>
                    <source src="%s" type="audio/ogg" autoplay=True>
                    Your browser does not support the audio element.
                    </audio>
                """ %audio_base
    mymidia_placeholder.empty()

# Display audio player if audio file has been generated
if st.session_state.audio_file:
    mymidia_placeholder.markdown(st.session_state.audio_file, unsafe_allow_html=True)

# Get user input
st.header("Dictate Here!🖋️")
user_text = st.text_area("What did you hear?", height=70)

# Check if user input matches generated text
if user_text and st.session_state.generated_text:
    if user_text.lower() == st.session_state.generated_text.lower():
        st.markdown('<p class="big-font">You Got It !!</p>', unsafe_allow_html=True)
    else:
        st.write("Try again.")

# Display generated text and Japanese translation
if st.session_state.generated_text:
    st.header("Hint💭")
    show_jpn_text = st.checkbox("Show Japanese translation", value=False)
    if show_jpn_text:
        st.write(st.session_state.japanese_text)
    show_words = st.checkbox("Show hints of words and idioms", value=False)
    if show_words:
        for key, value in st.session_state.hints.items():
            st.write(f"{key}: {value}")
    show_eng_text = st.checkbox("Show English sentence (Answer)", value=False)
    if show_eng_text:
        st.write(st.session_state.generated_text)