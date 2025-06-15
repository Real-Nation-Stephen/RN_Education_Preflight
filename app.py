import streamlit as st
import pandas as pd
import docx
import fitz  # PyMuPDF for PDFs
import re
import gspread
import json
import base64
from google.oauth2 import service_account
from io import BytesIO
from review_interface import ReviewInterface, SuggestedFix
from spellchecker import SpellChecker
import textblob
from docx import Document
from collections import Counter
from pathlib import Path
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.corpus import wordnet

# Download required NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('taggers/averaged_perceptron_tagger')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)

# --- Display functions moved to global scope ---
def display_results(issues, review_interface):
    """Display the results in an organized manner"""
    if not issues:
        st.success("No issues found!")
        return

    # Group issues by type
    issues_by_type = {}
    for issue in issues:
        category = issue.issue_type.split(":")[0].strip()  # Get main category
        if category not in issues_by_type:
            issues_by_type[category] = []
        issues_by_type[category].append(issue)

    # Display issues by category
    for category in ['Spelling', 'Banned Phrase', 'American Spelling', 'Em Dash Usage']:
        # Create a unique key for each expander
        expander_key = f"expander_{category}"
        
        # Update expander state based on user interaction
        with st.expander(f"{category} ({len(issues_by_type.get(category, []))} issues)", 
                        expanded=False) as exp:
            display_category_issues(issues_by_type.get(category, []), category, review_interface)

def display_category_issues(issues, category, review_interface):
    """Display issues for a specific category"""
    if not issues:
        st.write("No issues found in this category.")
        return

    for i, issue in enumerate(issues):
        # Use id(issue) for uniqueness
        issue_key = f"{category}_{i}_{id(issue)}"
        st.markdown(f"**Original:** {issue.original_text}")
        review_interface.render_fix(issue, i, issue_key)
        st.markdown("---")
# --- End of display functions ---

# === UI SETUP ===
# Load the thumbnail image
ASSETS_DIR = Path(__file__).parent / "assets"
with open(ASSETS_DIR / "Edu Copy Checker_Thumbnail.png", "rb") as f:
    thumbnail = f.read()

st.set_page_config(
    page_title="RN Copy Checker",
    page_icon=thumbnail,
    layout="centered"
)

# === PASSWORD PROTECTION ===
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "Realsafe2025":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False
            st.error("😕 Password incorrect. Please try again.")

    # First run or password incorrect
    if "password_correct" not in st.session_state:
        # Show the login form
        st.markdown("## Welcome to RN Copy Checker")
        st.markdown("Please enter your password to access the application.")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    # Password correct
    elif st.session_state["password_correct"]:
        return True

# If the password is correct, show the app
if check_password():
    st.title("📝 RN Copy Checker")

    # Initialize tools
    review_interface = ReviewInterface()
    spell = SpellChecker()

    # Define formal and informal word lists
    formal_words = {
        'therefore', 'furthermore', 'consequently', 'nevertheless', 'however',
        'moreover', 'thus', 'hence', 'accordingly', 'subsequently',
        'demonstrate', 'indicate', 'suggest', 'propose', 'conclude',
        'implement', 'utilize', 'facilitate', 'establish', 'determine'
    }

    informal_words = {
        'like', 'just', 'maybe', 'kind of', 'sort of', 'lots', 'stuff',
        'thing', 'pretty', 'really', 'very', 'totally', 'basically',
        'actually', 'literally', 'awesome', 'amazing', 'cool', 'huge',
        'okay', 'ok', 'yeah', 'hey', 'guys'
    }

    descriptive_words = {
        'detailed', 'comprehensive', 'thorough', 'extensive', 'in-depth',
        'specific', 'precise', 'explicit', 'clear', 'vivid', 'elaborate',
        'nuanced', 'meticulous', 'rigorous', 'exhaustive'
    }

    def score_descriptiveness(text, word_count):
        """
        Calculate descriptiveness score based on adjectives, adverbs, sensory language, and figurative language.
        Returns a score between 0 and 100.
        """
        if not text or word_count == 0:
            return 0.0
        
        # Sensory and emotive adjectives/adverbs (weighted higher)
        sensory_emotive_words = {
            # Visual
            'golden', 'vivid', 'bright', 'brilliant', 'gleaming', 'shimmering', 'radiant', 
            'dazzling', 'luminous', 'glowing', 'sparkling', 'crystalline', 'translucent',
            'shadowy', 'gloomy', 'dim', 'murky', 'hazy', 'blurred', 'sharp', 'crisp',
            
            # Tactile
            'smooth', 'rough', 'silky', 'velvety', 'coarse', 'tender', 'soft', 'hard',
            'warm', 'cool', 'freezing', 'burning', 'sticky', 'slippery', 'dry', 'moist',
            
            # Auditory
            'thunderous', 'whispered', 'melodic', 'harsh', 'gentle', 'piercing', 'muffled',
            'resonant', 'echoing', 'silent', 'deafening', 'rhythmic', 'harmonious',
            
            # Olfactory/Gustatory
            'fragrant', 'aromatic', 'pungent', 'sweet', 'bitter', 'sour', 'fresh', 'stale',
            'savory', 'spicy', 'bland', 'rich', 'delicate', 'robust',
            
            # Emotional/Atmospheric
            'serene', 'tranquil', 'chaotic', 'peaceful', 'turbulent', 'mysterious',
            'enchanting', 'haunting', 'melancholy', 'joyful', 'somber', 'vibrant',
            'dramatic', 'subtle', 'intense', 'gentle', 'fierce', 'delicate',
            
            # Adverbs
            'gracefully', 'effortlessly', 'dramatically', 'gently', 'fiercely', 'subtly',
            'vividly', 'brilliantly', 'mysteriously', 'elegantly', 'powerfully', 'tenderly'
        }
        
        # Figurative language patterns
        simile_patterns = [
            r'\blike\s+a\b', r'\bas\s+\w+\s+as\b', r'\blike\s+\w+ing\b'
        ]
        
        metaphor_indicators = {
            'bathed', 'drenched', 'flooded', 'swept', 'embraced', 'kissed', 'caressed',
            'whispered', 'sang', 'danced', 'painted', 'carved', 'sculpted', 'woven'
        }
        
        # Tokenize and get POS tags
        try:
            tokens = word_tokenize(text.lower())
            pos_tags = pos_tag(tokens)
        except:
            # Fallback to simple tokenization if NLTK fails
            tokens = tokenize_text(text)
            pos_tags = [(token, 'UNKNOWN') for token in tokens]
        
        # Count adjectives and adverbs
        adjective_count = 0
        adverb_count = 0
        sensory_count = 0
        
        for word, pos in pos_tags:
            # Count adjectives (JJ, JJR, JJS)
            if pos.startswith('JJ'):
                adjective_count += 1
                # Weight sensory/emotive adjectives higher
                if word in sensory_emotive_words:
                    sensory_count += 2
            # Count adverbs (RB, RBR, RBS)
            elif pos.startswith('RB'):
                adverb_count += 1
                # Weight sensory/emotive adverbs higher
                if word in sensory_emotive_words:
                    sensory_count += 2
            # Check for metaphor indicators
            elif word in metaphor_indicators:
                sensory_count += 1
        
        # Count figurative language
        figurative_count = 0
        text_lower = text.lower()
        
        # Count similes
        for pattern in simile_patterns:
            figurative_count += len(re.findall(pattern, text_lower))
        
        # Calculate base descriptiveness from adjectives/adverbs per 100 words
        base_descriptiveness = ((adjective_count + adverb_count) / word_count) * 100
        
        # Add bonus for sensory/emotive language
        sensory_bonus = (sensory_count / word_count) * 50
        
        # Add bonus for figurative language
        figurative_bonus = (figurative_count / word_count) * 30
        
        # Combine scores with diminishing returns
        total_score = base_descriptiveness + sensory_bonus + figurative_bonus
        
        # Apply scaling to make scores more intuitive
        if total_score > 0:
            # Use a more generous scaling that rewards descriptive writing
            total_score = min(100, 30 * (1 + 2.5 * (total_score / 100) ** 0.6))
        
        return max(0, min(100, total_score))

    def score_formality(text, all_words, word_count):
        """
        Calculate formality score based on contractions, informal vocabulary, 
        exclamations, pronouns, and formal language patterns.
        Returns a score between 0 and 100.
        """
        if not text or word_count == 0:
            return 50.0
        
        # Expanded informal vocabulary
        informal_vocabulary = {
            # Casual words
            'like', 'just', 'maybe', 'kinda', 'sorta', 'gonna', 'gotta', 'wanna',
            'lots', 'stuff', 'thing', 'things', 'pretty', 'really', 'very', 'super',
            'totally', 'basically', 'actually', 'literally', 'honestly', 'seriously',
            'awesome', 'amazing', 'cool', 'huge', 'tiny', 'massive', 'epic',
            'okay', 'ok', 'yeah', 'yep', 'nope', 'hey', 'guys', 'folks',
            'crazy', 'insane', 'wild', 'sick', 'sweet', 'dope', 'rad',
            'whatever', 'anyways', 'dunno', 'lemme', 'gimme'
        }
        
        # Interjections and exclamatory words
        interjections = {
            'wow', 'oh', 'ah', 'ugh', 'hmm', 'oops', 'yay', 'hooray',
            'alas', 'darn', 'gosh', 'jeez', 'phew', 'whoa', 'bam', 'boom'
        }
        
        # Formal/business vocabulary (rewards formality)
        formal_vocabulary = {
            'regarding', 'concerning', 'pertaining', 'submit', 'forthcoming', 'pursuant',
            'heretofore', 'henceforth', 'notwithstanding', 'nevertheless', 'furthermore',
            'consequently', 'therefore', 'accordingly', 'subsequently', 'moreover',
            'demonstrate', 'indicate', 'suggest', 'propose', 'conclude', 'establish',
            'implement', 'utilize', 'facilitate', 'determine', 'ascertain', 'endeavor',
            'commence', 'terminate', 'acquire', 'procure', 'obtain', 'maintain',
            'substantial', 'significant', 'considerable', 'appropriate', 'adequate',
            'sufficient', 'comprehensive', 'extensive', 'preliminary', 'subsequent'
        }
        
        # Personal pronouns (context-dependent penalty)
        personal_pronouns = {'i', 'you', 'we', 'me', 'us', 'my', 'your', 'our'}
        
        # Count various formality indicators
        contraction_count = 0
        informal_count = 0
        interjection_count = 0
        exclamation_count = 0
        formal_count = 0
        personal_pronoun_count = 0
        
        # Count contractions
        contraction_patterns = [
            r"\b\w+'\w+\b",  # General contractions like don't, can't, you're
            r"\b\w+'ll\b",   # will contractions
            r"\b\w+'ve\b",   # have contractions
            r"\b\w+'re\b",   # are contractions
            r"\b\w+'d\b",    # would/had contractions
        ]
        
        for pattern in contraction_patterns:
            contraction_count += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Count exclamation marks
        exclamation_count = text.count('!')
        
        # Count word-based indicators
        for word in all_words:
            if word in informal_vocabulary:
                informal_count += 1
            elif word in interjections:
                interjection_count += 1
            elif word in formal_vocabulary:
                formal_count += 1
            elif word in personal_pronouns:
                personal_pronoun_count += 1
        
        # Calculate penalty factors (higher = less formal)
        contraction_penalty = (contraction_count / word_count) * 100
        informal_penalty = (informal_count / word_count) * 80
        interjection_penalty = (interjection_count / word_count) * 60
        exclamation_penalty = (exclamation_count / word_count) * 40
        pronoun_penalty = (personal_pronoun_count / word_count) * 20
        
        # Calculate reward factors (higher = more formal)
        formal_reward = (formal_count / word_count) * 60
        
        # Base formality score starts at 50 (neutral)
        formality_score = 50.0
        
        # Apply penalties
        total_penalty = contraction_penalty + informal_penalty + interjection_penalty + exclamation_penalty + pronoun_penalty
        formality_score -= total_penalty
        
        # Apply rewards
        formality_score += formal_reward
        
        # Ensure score stays within bounds
        return max(0, min(100, formality_score))

    def tokenize_text(text):
        """
        A robust tokenizer that splits text into a list of words, 
        preserving contractions and hyphenated words, while ignoring standalone punctuation.
        Returns a list of all words (with duplicates).
        """
        # Normalize text to lowercase
        text = text.lower()
        # This regex finds sequences of letters that can be optionally separated by an apostrophe or hyphen.
        # The regex has been corrected to handle hyphens properly.
        words = re.findall(r"[a-z]+(?:['\-][a-z]+)*", text)
        return words

    def simple_sentence_split(text):
        """More robust sentence splitting using regex."""
        if not text:
            return []
        # This regex splits the text after a sentence-ending punctuation mark (. ! ?)
        # that is followed by a space or a newline. The regex has been corrected
        # to look for whitespace (\s) instead of a literal backslash.
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        # Filter out any empty strings that might result.
        return [s for s in sentences if s]

    def analyze_tone(text):
        """
        Analyzes the tone of the text with corrected and robust logic.
        """
        # If the input text is empty or just whitespace, return a zeroed-out dictionary.
        if not text or not text.strip():
            return {
                'formality': 50.0, 'descriptiveness': 0.0, 'sentiment': 50.0,
                'avg_sentence_length': 0.0, 'vocabulary_richness': 0.0,
                'word_count': 0, 'sentence_count': 0
            }

        # --- 1. Core Counts (Words and Sentences) ---
        all_words = tokenize_text(text)
        word_count = len(all_words)
        
        sentences = simple_sentence_split(text)
        sentence_count = len(sentences)

        # If there are no words or sentences, we can't calculate ratios.
        if word_count == 0 or sentence_count == 0:
            return {
                'formality': 50.0, 'descriptiveness': 0.0, 'sentiment': 50.0,
                'avg_sentence_length': 0.0, 'vocabulary_richness': 0.0,
                'word_count': word_count, 'sentence_count': sentence_count
            }

        # --- 2. Richness and Length Metrics ---
        unique_word_count = len(set(all_words))
        vocabulary_richness = (unique_word_count / word_count) * 100
        avg_sentence_length = word_count / sentence_count

        # --- 3. Content-Based Metrics ---
        # Use new improved scoring functions
        formality_score = score_formality(text, all_words, word_count)
        descriptiveness_score = score_descriptiveness(text, word_count)
        
        # Sentiment score: uses TextBlob's polarity, scaled to 0-100.
        blob = textblob.TextBlob(text)
        sentiment = (blob.sentiment.polarity + 1) / 2 * 100 # Scale from -1:1 to 0:100

        return {
            'formality': formality_score,
            'descriptiveness': descriptiveness_score,
            'sentiment': sentiment,
            'avg_sentence_length': avg_sentence_length,
            'vocabulary_richness': vocabulary_richness,
            'word_count': word_count,
            'sentence_count': sentence_count
        }

    def render_tone_analysis(metrics):
        """Render the tone analysis metrics"""
        st.markdown("## 📊 Tone Analysis")
        
        # Create three columns for the main metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Formality",
                f"{metrics['formality']:.1f}%",
                help="Higher scores indicate more formal language"
            )
            
        with col2:
            st.metric(
                "Descriptiveness",
                f"{metrics['descriptiveness']:.1f}%",
                help="Higher scores indicate more descriptive language"
            )
            
        with col3:
            st.metric(
                "Sentiment",
                f"{metrics['sentiment']:.1f}%",
                help="50% is neutral, higher is more positive, lower is more negative"
            )
        
        # Create two columns for additional metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Average Sentence Length",
                f"{metrics['avg_sentence_length']:.1f} words",
                help="The average number of words per sentence"
            )
            st.metric(
                "Vocabulary Richness",
                f"{metrics['vocabulary_richness']:.1f}%",
                help="Percentage of unique words in the text"
            )
        
        with col2:
            st.metric(
                "Word Count",
                metrics['word_count'],
                help="Total number of words in the text"
            )
            st.metric(
                "Sentence Count",
                metrics['sentence_count'],
                help="Total number of sentences in the text"
            )
        
        # Add interpretation
        st.markdown("### 💡 Interpretation")
        
        formality = "very formal" if metrics['formality'] > 75 else "formal" if metrics['formality'] > 60 else "neutral" if metrics['formality'] > 40 else "informal" if metrics['formality'] > 25 else "very informal"
        descriptiveness = "highly descriptive" if metrics['descriptiveness'] > 75 else "moderately descriptive" if metrics['descriptiveness'] > 50 else "somewhat descriptive" if metrics['descriptiveness'] > 25 else "minimally descriptive"
        sentiment = "very positive" if metrics['sentiment'] > 75 else "positive" if metrics['sentiment'] > 60 else "neutral" if metrics['sentiment'] > 40 else "negative" if metrics['sentiment'] > 25 else "very negative"
        
        st.markdown(f"""
        This text appears to be:
        - **Tone**: {formality}
        - **Detail Level**: {descriptiveness}
        - **Emotional Tone**: {sentiment}
        
        The vocabulary richness score of {metrics['vocabulary_richness']:.1f}% suggests {'a diverse vocabulary' if metrics['vocabulary_richness'] > 50 else 'some repetition in word choice'}.
        
        The average sentence length of {metrics['avg_sentence_length']:.1f} words is {'quite long' if metrics['avg_sentence_length'] > 20 else 'moderate' if metrics['avg_sentence_length'] > 15 else 'concise'}.
        """)

    # === STEP 1: UPLOAD FILE ===
    uploaded_file = st.file_uploader(
        "Upload a Word or PDF file",
        type=["docx", "pdf"],
        help="Select a Word (.docx) or PDF (.pdf) file to analyze"
    )

    # === STEP 2: LOAD CLIENT RULES FROM GOOGLE SHEETS ===
    def load_client_rules():
        # Uses credentials from Streamlit secrets
        creds = service_account.Credentials.from_service_account_info(
            json.loads(base64.b64decode(st.secrets["gcp_creds"])),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1VJ7Ox1MNVkWx4nTaVW4ifoYWcKb4eq7GovgpLNX4wfo/edit")
        worksheet = sheet.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df

    try:
        client_df = load_client_rules()
        client_names = client_df["Client"].unique().tolist()
    except Exception as e:
        st.error(f"Error loading Google Sheet: {str(e)}")
        st.error("Using fallback client list.")
        client_names = ["AL4L", "Demo Client"]

    selected_client = st.selectbox("Optional: Select a client for custom rules", ["None"] + client_names)

    # === STEP 3: EXTRACT TEXT ===
    def extract_text(file):
        """Extract text from supported file types"""
        if not file:
            return ""
        
        if file.name.endswith(".docx"):
            doc = docx.Document(file)
            return "\n".join([p.text for p in doc.paragraphs])
        elif file.name.endswith(".pdf"):
            pdf = fitz.open(stream=file.read(), filetype="pdf")
            text = "\n".join([page.get_text() for page in pdf])
            pdf.close()
            return text
        else:
            st.error(f"Unsupported file type. Please upload a .docx or .pdf file.")
            return ""

    # === STEP 4: RUN BASE CHECKS (universal) ===
    def run_base_checks(text):
        """Run base checks including spelling, grammar, banned phrases, and em dash usage"""
        issues = []
        
        # Spell check
        words = tokenize_text(text)
        # Don't spell check contractions
        words_to_check = [word for word in words if "'" not in word]
        # Don't spell check hyphenated words as a whole, but check their parts
        hyphenated_parts = []
        for word in words_to_check[:]:
            if '-' in word:
                words_to_check.remove(word)
                parts = word.split('-')
                hyphenated_parts.extend(parts)
                # Only check the word if any of its parts are misspelled
                misspelled_parts = spell.unknown(parts)
                if misspelled_parts:
                    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                    matches = list(pattern.finditer(text))
                    
                    for match in matches:
                        word_index = match.start()
                        start = max(0, word_index - 50)
                        end = min(len(text), word_index + len(word) + 50)
                        context = f"...{text[start:end]}..."
                        
                        # Get suggestions for misspelled parts
                        suggestions_by_part = {}
                        for part in misspelled_parts:
                            suggestions = spell.candidates(part)
                            if suggestions:
                                suggestions_by_part[part] = list(suggestions)[:3]
                        
                        # Format suggestions
                        suggestion_text = "Possible issues in parts: " + ", ".join(
                            f"{part}: {', '.join(suggs)}"
                            for part, suggs in suggestions_by_part.items()
                        )
                        
                        issues.append(SuggestedFix(
                            issue_type="Spelling (Hyphenated Word)",
                            original_text=match.group(),
                            suggested_text=suggestion_text,
                            context=context
                        ))
        
        # Add hyphenated parts back to the words to check
        words_to_check.extend(hyphenated_parts)
        misspelled = spell.unknown(words_to_check)
        
        for word in misspelled:
            # Skip parts that are already handled in hyphenated words
            if word in hyphenated_parts:
                continue
                
            # Find the word in context (using word boundaries)
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))
            
            for match in matches:
                word_index = match.start()
                start = max(0, word_index - 50)
                end = min(len(text), word_index + len(word) + 50)
                context = f"...{text[start:end]}..."
                
                # Get suggestions
                suggestions = spell.candidates(word)
                if suggestions:
                    suggestions_str = ", ".join(list(suggestions)[:3])  # Take top 3 suggestions
                else:
                    suggestions_str = "No suggestions available"
                
                issues.append(SuggestedFix(
                    issue_type="Spelling",
                    original_text=match.group(),  # Use the actual matched text to preserve case
                    suggested_text=suggestions_str,
                    context=context
                ))
        
        # Check banned phrases
        banned_phrases = {
            "world-class": "leading, premier, exceptional",
            "innovative": "advanced, pioneering, groundbreaking",
            "cutting-edge": "advanced, modern, state-of-the-art",
            "best-in-class": "leading, superior, outstanding",
            "industry-leading": "prominent, distinguished, renowned",
            "game-changing": "transformative, revolutionary, groundbreaking",
            "revolutionary": "transformative, innovative, pioneering",
            "next-generation": "advanced, modern, enhanced",
            "state-of-the-art": "modern, advanced, cutting-edge"
        }
        
        for phrase, suggestions in banned_phrases.items():
            if phrase in text.lower():
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                for match in pattern.finditer(text):
                    original = match.group()
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = f"...{text[start:end]}..."
                    
                    issues.append(SuggestedFix(
                        issue_type="Banned Phrase",
                        original_text=original,
                        suggested_text=suggestions,
                        context=context
                    ))
        
        # Check for American vs British spelling
        blob = textblob.TextBlob(text)
        # Add specific word pairs to check
        spelling_pairs = {
            "color": "colour",
            "center": "centre",
            "analyze": "analyse",
            "organize": "organise",
            # Add more pairs as needed
        }
        
        for am, br in spelling_pairs.items():
            pattern = re.compile(r'\b' + re.escape(am) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                original = match.group()
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = f"...{text[start:end]}..."
                
                issues.append(SuggestedFix(
                    issue_type="American Spelling",
                    original_text=original,
                    suggested_text=br,
                    context=context
                ))
        
        # Check for em dashes
        em_dash_matches = list(re.finditer(r'\u2014|\u2013', text))  # Match both em and en dashes
        for match in em_dash_matches:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = f"...{text[start:end]}..."
            
            issues.append(SuggestedFix(
                issue_type="Em Dash Usage",
                original_text=match.group(),
                suggested_text=" , | ; | - ",  # Add spaces around each option
                context=context
            ))
        
        return issues

    # === STEP 5: RUN CLIENT CHECKS (if selected) ===
    def run_client_checks(text, client_df, selected_name):
        issues = []
        
        # Get all rows for the selected client
        client_rows = client_df[client_df["Client"] == selected_name]
        
        # Debug print
        print(f"\nProcessing rules for client: {selected_name}")
        print(f"Found {len(client_rows)} rules")
        print(f"Text to check: {text[:200]}...")  # Print first 200 chars of text
        
        for _, row in client_rows.iterrows():
            # Split both banned words and replacements, and normalize them
            banned_words = []
            replacements = []
            
            # Handle banned words
            raw_banned = str(row.get("Banned Words", "")).strip()
            if raw_banned:
                banned_words = [word.strip() for word in raw_banned.split(",") if word.strip()]
                print(f"\nRaw banned words: {raw_banned}")
                print(f"Processed banned words: {banned_words}")
            
            # Handle replacements
            raw_replacements = str(row.get("Suggested Replacements", "")).strip()
            if raw_replacements:
                replacements = [word.strip() for word in raw_replacements.split(",") if word.strip()]
                print(f"Raw replacements: {raw_replacements}")
                print(f"Processed replacements: {replacements}")
            
            # Create a mapping of banned words to their replacements
            word_mapping = {}
            for i, banned_word in enumerate(banned_words):
                # If there's a corresponding replacement, use it; otherwise use a default
                replacement = replacements[i] if i < len(replacements) else "[NEEDS REPLACEMENT]"
                word_mapping[banned_word] = replacement
            
            print(f"\nWord mapping: {word_mapping}")
            
            # Process each banned word with its specific replacement
            for banned_word, replacement in word_mapping.items():
                # Create pattern with optional capitalization
                pattern = re.compile(fr'\b{re.escape(banned_word)}\b', re.IGNORECASE)
                
                # Find all matches
                matches = list(pattern.finditer(text))
                print(f"\nChecking for word: '{banned_word}'")
                print(f"Pattern used: {pattern.pattern}")
                print(f"Found {len(matches)} matches")
                
                for match in matches:
                    original = match.group()
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = f"...{text[start:end]}..."
                    
                    print(f"Found match: '{original}' -> '{replacement}'")
                    print(f"Context: {context}")
                    
                    # Create the fix with proper initialization
                    fix = SuggestedFix(
                        issue_type=f"Client ({selected_name}) Banned Word",
                        original_text=original,
                        suggested_text=replacement,
                        context=context
                    )
                    issues.append(fix)
        
        print(f"\nTotal issues found: {len(issues)}")
        return issues

    # === STEP 6: PROCESS FILE AND SHOW RESULTS ===
    if uploaded_file is not None:
        if 'document_scanned' not in st.session_state:
            st.session_state.document_scanned = False
            
        if not st.session_state.document_scanned:
            with st.spinner("Scanning document..."):
                # Clear previous fixes
                review_interface.clear_fixes()
                
                # Extract text
                text = extract_text(uploaded_file)
                if text:  # Only proceed if we have text
                    st.session_state.original_text = text
                    
                    # Run tone analysis
                    st.session_state.tone_metrics = analyze_tone(text)
                    
                    # Run checks
                    base_issues = run_base_checks(text)
                    for issue in base_issues:
                        review_interface.add_fix(issue)
                    
                    if selected_client != "None":
                        client_issues = run_client_checks(text, client_df, selected_client)
                        for issue in client_issues:
                            review_interface.add_fix(issue)
                            
                    st.session_state.document_scanned = True
                else:
                    st.error("No text could be extracted from the file. Please check the file and try again.")
                    st.session_state.document_scanned = False
        
        # Show tone analysis before the review interface
        render_tone_analysis(st.session_state.tone_metrics)
        
        # Show review interface
        review_interface.render_interface()
        
        # Show document versions and downloads
        if st.session_state.fixes:
            st.markdown("## Document Versions")
            
            tab1, tab2, tab3 = st.tabs(["📄 Original", "🔍 Marked-up", "✨ Clean"])
            
            with tab1:
                st.markdown("### Original Document")
                st.text_area(
                    "Original document content",
                    st.session_state.original_text,
                    height=300,
                    key="original_text_display",
                    help="The original unmodified text"
                )
                st.download_button(
                    "📥 Download Original Text",
                    st.session_state.original_text,
                    "original_text.txt",
                    "text/plain",
                    key="download_original",
                    help="Download the original unmodified text as a .txt file"
                )
            
            with tab2:
                st.markdown("### Marked-up Document")
                marked_text = review_interface.generate_marked_document(st.session_state.original_text)
                st.markdown(marked_text, unsafe_allow_html=True)
                st.download_button(
                    "📥 Download Marked-up Version",
                    marked_text,
                    "marked_up_text.html",
                    "text/html",
                    key="download_marked",
                    help="Download the marked-up version with all changes highlighted as an HTML file"
                )
            
            with tab3:
                st.markdown("### Clean Document")
                clean_text = review_interface.generate_clean_document(st.session_state.original_text)
                st.text_area(
                    "Clean document content",
                    clean_text,
                    height=300,
                    key="clean_text",
                    help="The clean text with all accepted changes applied"
                )
                st.download_button(
                    "📥 Download Clean Version",
                    clean_text,
                    "clean_text.txt",
                    "text/plain",
                    key="download_clean",
                    help="Download the clean version with all accepted changes as a .txt file"
                )
            
            # Add PDF report download
            report_bytes = review_interface.create_downloadable_report(st.session_state.original_text)
            st.download_button(
                "📊 Download Full Report (PDF)",
                report_bytes,
                "copy_check_report.pdf",
                "application/pdf",
                key="download_report",
                help="Download a detailed PDF report of all changes and decisions"
            )

            # Display review sections
            display_results(st.session_state.fixes, review_interface)
    else:
        # Reset the scan state when no file is uploaded
        if 'document_scanned' in st.session_state:
            del st.session_state.document_scanned

    # === Notes ===
    # UI/layout ideas can be borrowed from /reference folder
    # DO NOT copy functionality from that file
