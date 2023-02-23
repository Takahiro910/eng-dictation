from dotenv import load_dotenv
from google.cloud import texttospeech
from google.oauth2 import service_account
from oauth2client.service_account import ServiceAccountCredentials
from googletrans import Translator
import gspread
import json
import os
import pandas as pd
import random
import streamlit as st


# Set up 
load_dotenv(verbose=True, dotenv_path='.env')
JSON_FILE_PATH = os.environ.get("JSON_FILE_PATH")
SHEET_KEY = os.environ.get("SHEET_KEY")
translator = Translator(service_urls=['translate.googleapis.com'])
st.set_page_config(page_title="AI English", page_icon="🤖")
st.markdown("""
<style>
.big-font {
    font-size:50px !important;
}
</style>
""", unsafe_allow_html=True)
secrets = st.secrets["gcp_service_account"]
my_secrets = dict(secrets)
secrets_json = json.dumps(my_secrets)
secrets_dict = json.loads(secrets_json)

# Load spreadsheet data
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE_PATH, scope) # For local
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = JSON_FILE_PATH
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope) # For Streamlit Share
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secrets_dict["gcp_service_account"]
gs = gspread.authorize(credentials)
spreadsheet_key = SHEET_KEY
wb = gs.open_by_key(spreadsheet_key)
ws = wb.worksheet("dictation")

# Setting for GTTS
client = texttospeech.TextToSpeechClient()
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Neural2-I"
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Setting for DataFrame
df = pd.DataFrame(ws.get_all_values())
df.columns = list(df.loc[0, :])
df.drop(0, inplace=True)
df.reset_index(inplace=True)
df.drop('index', axis=1, inplace=True)

themes = df.theme.unique()

st.title("English Dictation!")

# Set up session state to store generated text
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""
if "japanese_text" not in st.session_state:
    st.session_state.japanese_text = ""
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None

# Get theme input
theme = st.selectbox("Select theme which you want to hear.", themes)
random_theme = st.checkbox("If this on, AI generate English sentence randomly from all themes.")
if random_theme:
    theme = ""
if theme:
    df = df[df["theme"] == theme]
n = len(df)
sentences = df["sentences"].to_list()

# Generate button and AI start generating sentence
st.header("Generate English🤖")
st.write("Click the 'Generate' button to generate audio.")
if st.button("Generate"):
    rand_int = random.randint(0, n-1)
    generated_text = sentences[rand_int]

    # Translate generated text to Japanese
    japanese_text = translator.translate(generated_text, dest="ja").text

    # Convert generated text to audio using gTTS
    tts = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=generated_text),
        voice=voice,
        audio_config=audio_config
        )
    audio_content = tts.audio_content
    audio_bytes = bytes(audio_content)

    # Update session state with generated text and translation
    st.session_state.generated_text = generated_text
    st.session_state.japanese_text = japanese_text
    st.session_state.audio_file = audio_bytes

# Display audio player if audio file has been generated
if st.session_state.audio_file:
    st.audio(st.session_state.audio_file, format="audio/mp3", start_time=0)

# Get user input
st.header("Dictate Here!🖋️")
user_text = st.text_input("What did you hear?")

# Check if user input matches generated text
if user_text and st.session_state.generated_text:
    if user_text.lower() == st.session_state.generated_text.lower():
        st.markdown('<p class="big-font">You Got It !!</p>', unsafe_allow_html=True)
    else:
        st.write("Try again.")

# Display generated text and Japanese translation
if st.session_state.generated_text:
    st.header("Hint💭")
    show_jpn_text = st.checkbox("Show Japanese translation")
    if show_jpn_text:
        st.write("Japanese translation: ", st.session_state.japanese_text)
    show_eng_text = st.checkbox("Show English sentence (Answer)")
    if show_eng_text:
        st.write("Generated text: ", st.session_state.generated_text)
