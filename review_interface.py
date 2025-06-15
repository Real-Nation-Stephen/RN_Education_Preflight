import streamlit as st
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict
import difflib
import re
from fpdf import FPDF
import html
import base64

class PDF(FPDF):
    """Custom PDF class to handle Unicode characters"""
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font('Helvetica', '', 12)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        """Add a chapter title"""
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, title, ln=True)
        self.set_font('Helvetica', '', 12)
        self.ln(5)

    def issue_header(self, text):
        """Add an issue type header"""
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, text, ln=True)
        self.set_font('Helvetica', '', 12)
        self.ln(2)

    def accepted_text(self, text):
        """Add text in green"""
        self.set_text_color(0, 128, 0)  # Dark green
        self.cell(0, 10, text, ln=True)
        self.set_text_color(0, 0, 0)  # Reset to black

    def rejected_text(self, text):
        """Add text in red"""
        self.set_text_color(200, 0, 0)  # Dark red
        self.cell(0, 10, text, ln=True)
        self.set_text_color(0, 0, 0)  # Reset to black

@dataclass
class SuggestedFix:
    issue_type: str
    original_text: str
    suggested_text: str
    context: str
    accepted: bool = False
    rejected: bool = False
    capitalize: bool = False  # Track capitalization
    _selected_replacement: str = ""  # Private storage for selected replacement

    def __post_init__(self):
        """Initialize the selected_replacement with the first suggestion"""
        # Special handling for em dash replacements
        if self.issue_type == "AI Pattern: Em Dash Usage":
            suggestions = [s.strip() for s in self.suggested_text.split('|')]
            self._selected_replacement = suggestions[0] if suggestions else self.suggested_text
        # For patterns that don't need replacements, use original text
        elif self.issue_type in ["AI Pattern: Repetitive Sentence Structure", 
                               "AI Pattern: Business Cliché",
                               "AI Pattern: Long Sentences"]:
            self._selected_replacement = self.original_text
        # Normal handling for other cases
        else:
            suggestions = [s.strip() for s in self.suggested_text.split(',')]
            self._selected_replacement = suggestions[0] if suggestions else self.suggested_text
        
        if self.capitalize or self.original_text[0].isupper():
            self._selected_replacement = self._selected_replacement.capitalize()

    @property
    def selected_replacement(self) -> str:
        """Get the current selected replacement"""
        if not self._selected_replacement:
            # Special handling for em dash replacements
            if self.issue_type == "AI Pattern: Em Dash Usage":
                suggestions = [s.strip() for s in self.suggested_text.split('|')]
                self._selected_replacement = suggestions[0] if suggestions else self.suggested_text
            # For patterns that don't need replacements, use original text
            elif self.issue_type in ["AI Pattern: Repetitive Sentence Structure", 
                                   "AI Pattern: Business Cliché",
                                   "AI Pattern: Long Sentences"]:
                self._selected_replacement = self.original_text
            # Normal handling for other cases
            else:
                suggestions = [s.strip() for s in self.suggested_text.split(',')]
                self._selected_replacement = suggestions[0] if suggestions else self.suggested_text
            
            if self.capitalize or self.original_text[0].isupper():
                self._selected_replacement = self._selected_replacement.capitalize()
        return self._selected_replacement

    @selected_replacement.setter
    def selected_replacement(self, value: str):
        """Set the selected replacement"""
        self._selected_replacement = value
        if self.capitalize or self.original_text[0].isupper():
            self._selected_replacement = self._selected_replacement.capitalize()

    def get_selected_replacement(self) -> str:
        """Get the current selected replacement (legacy method)"""
        return self.selected_replacement

class ReviewInterface:
    def __init__(self):
        if 'fixes' not in st.session_state:
            st.session_state.fixes = []
        if 'decisions' not in st.session_state:
            st.session_state.decisions = {'accepted': [], 'rejected': []}
        if 'changes_to_apply' not in st.session_state:
            st.session_state.changes_to_apply = False
        if 'batch_decisions' not in st.session_state:
            st.session_state.batch_decisions = {}
    
    def add_fix(self, fix: SuggestedFix):
        """Add a new fix to the list"""
        # Check if the original text is capitalized
        if fix.original_text[0].isupper() or fix.original_text.isupper():
            fix.capitalize = True
        st.session_state.fixes.append(fix)
    
    def clear_fixes(self):
        """Clear all fixes and reset state"""
        st.session_state.fixes = []
        st.session_state.decisions = {'accepted': [], 'rejected': []}
        st.session_state.changes_to_apply = False
        st.session_state.batch_decisions = {}
    
    def get_accepted_fixes(self) -> List[SuggestedFix]:
        """Get all accepted fixes"""
        return [fix for fix in st.session_state.fixes if fix.accepted]
    
    def get_rejected_fixes(self) -> List[SuggestedFix]:
        """Get all rejected fixes"""
        return [fix for fix in st.session_state.fixes if fix.rejected]
    
    def render_diff(self, original: str, suggested: str) -> str:
        """Create a HTML diff view of the changes"""
        diff = difflib.ndiff(original.split(), suggested.split())
        html_diff = []
        for word in diff:
            if word.startswith('+ '):
                html_diff.append(f'<span style="background-color: #90EE90">{word[2:]}</span>')
            elif word.startswith('- '):
                html_diff.append(f'<span style="background-color: #FFB6C1">{word[2:]}</span>')
            elif word.startswith('  '):
                html_diff.append(word[2:])
        return ' '.join(html_diff)

    def reset_all_fixes(self):
        """Reset all fixes to their initial state"""
        for fix in st.session_state.fixes:
            fix.accepted = False
            fix.rejected = False

    def render_fix(self, fix: SuggestedFix, index: int = 0, issue_key: str = None):
        """Render a single fix with its context and actions"""
        if fix.accepted or fix.rejected:
            return

        # Create a unique key for this fix using the issue_key if provided
        unique_key = f"{issue_key}" if issue_key else f"{fix.issue_type}_{index}_{hash(fix.context)}"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Context:**")
            st.markdown(fix.context.replace(fix.original_text, f"**{fix.original_text}**"))
            
            # Show replacement options if they exist
            if fix.suggested_text:
                # Handle em dash replacements
                if fix.issue_type == "Em Dash Usage":
                    replacement_options = [opt.strip() + " " for opt in fix.suggested_text.split('|')]  # Add space after each option
                # Handle normal comma-separated replacements
                else:
                    replacement_options = [opt.strip() for opt in fix.suggested_text.split(',')]
                
                # Add custom input option
                use_custom = st.checkbox(
                    label=f"Use custom replacement for '{fix.original_text}'",
                    value=False,
                    key=f"use_custom_{unique_key}",
                    help="Check to enter your own replacement word"
                )
                
                if use_custom:
                    # Custom input field
                    custom_replacement = st.text_input(
                        label=f"Enter custom replacement for '{fix.original_text}'",
                        value=fix.get_selected_replacement(),
                        key=f"custom_{unique_key}",
                        help="Enter your own replacement word"
                    )
                    fix.selected_replacement = custom_replacement
                else:
                    try:
                        selected_idx = replacement_options.index(fix.get_selected_replacement()) if fix.get_selected_replacement() else 0
                    except (ValueError, AttributeError):
                        selected_idx = 0
                        fix.selected_replacement = replacement_options[0]
                        if fix.capitalize:
                            fix.selected_replacement = fix.selected_replacement.capitalize()
                    
                    # Create a unique label for each selectbox
                    select_label = f"Choose replacement for '{fix.original_text}' (Issue {index+1})"
                    selected = st.selectbox(
                        label=select_label,
                        options=replacement_options,
                        index=selected_idx,
                        key=f"replacement_{unique_key}",
                        help=f"Select a replacement for the text '{fix.original_text}'"
                    )
                    fix.selected_replacement = selected
                
                # Capitalization option
                fix.capitalize = st.checkbox(
                    label=f"Capitalize first letter of replacement for '{fix.original_text}'",
                    value=fix.capitalize,
                    key=f"capitalize_{unique_key}",
                    help="Check to capitalize the first letter of the replacement"
                )
                
                # Update capitalization if needed
                if fix.capitalize and fix.selected_replacement:
                    fix.selected_replacement = fix.selected_replacement.capitalize()
                
                # Show preview
                st.markdown("**Preview:**")
                preview = fix.context.replace(
                    fix.original_text,
                    f"<span style='background-color: #90EE90'>{fix.selected_replacement}</span>"
                )
                st.markdown(preview, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Actions:**")
            col2a, col2b = st.columns(2)
            with col2a:
                st.button(
                    label=f"✅ Accept {index+1}",
                    key=f"accept_{unique_key}",
                    help=f"Accept the change from '{fix.original_text}' to '{fix.selected_replacement}'",
                    on_click=lambda fix=fix: setattr(fix, 'accepted', True),
                    use_container_width=True
                )
            
            with col2b:
                st.button(
                    label=f"❌ Reject {index+1}",
                    key=f"reject_{unique_key}",
                    help=f"Reject the change and keep '{fix.original_text}'",
                    on_click=lambda fix=fix: setattr(fix, 'rejected', True),
                    use_container_width=True
                )
        
        st.markdown("---")

    def render_interface(self):
        """Render the review interface with all suggested fixes"""
        # Load and inject CSS
        with open('style.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        
        # Convert logos to base64
        with open("assets/Logo Studio.png", "rb") as f:
            logo_studio_base64 = base64.b64encode(f.read()).decode()
            
        with open("assets/Logo Sparkle.png", "rb") as f:
            logo_sparkle_base64 = base64.b64encode(f.read()).decode()
        
        # Add logos with theme-aware display
        st.sidebar.markdown(f"""
            <div class="sidebar-logo">
                <img src="data:image/png;base64,{logo_studio_base64}" class="studio-mode-logo light" alt="RN Education Logo Light Mode">
                <img src="data:image/png;base64,{logo_sparkle_base64}" class="studio-mode-logo dark" alt="RN Education Logo Dark Mode">
            </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.fixes:
            st.info("No issues found to review.")
            return
        
        st.markdown("## Review Suggested Fixes")
        
        # Add batch action buttons at the top
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button(
                label="✅ Accept All Changes",
                type="primary",
                key="accept_all_btn",
                help="Accept all pending changes",
                on_click=lambda: [setattr(fix, 'accepted', True) for fix in st.session_state.fixes if not fix.rejected],
                use_container_width=True
            )
        with col2:
            st.button(
                label="❌ Reject All Changes",
                type="secondary",
                key="reject_all_btn",
                help="Reject all pending changes",
                on_click=lambda: [setattr(fix, 'rejected', True) for fix in st.session_state.fixes if not fix.accepted],
                use_container_width=True
            )
        with col3:
            st.button(
                label="🔄 Reset All Changes",
                key="reset_all_btn",
                help="Reset all decisions",
                on_click=self.reset_all_fixes,
                use_container_width=True
            )
        
        st.markdown("---")
        
        # Group fixes by type for better organization
        fixes_by_type = {}
        for fix in st.session_state.fixes:
            if fix.issue_type not in fixes_by_type:
                fixes_by_type[fix.issue_type] = []
            fixes_by_type[fix.issue_type].append(fix)
        
        # Show fixes grouped by type
        for issue_type, fixes in fixes_by_type.items():
            with st.expander(f"{issue_type} ({len(fixes)} issues)", expanded=False):
                for i, fix in enumerate(fixes):
                    self.render_fix(fix, i)
        
        # Show apply changes button if there are decisions to apply
        if any(not (fix.accepted or fix.rejected) for fix in st.session_state.fixes):
            st.warning("⚠️ Some changes are still pending review")
        else:
            st.success("✅ All changes have been reviewed!")
        
        # Show summary of decisions
        if any(fix.accepted or fix.rejected for fix in st.session_state.fixes) or any(not (fix.accepted or fix.rejected) for fix in st.session_state.fixes):
            with st.expander("📊 Summary Report", expanded=False):
                st.markdown(f"**Total Issues Found:** {len(st.session_state.fixes)}")
                
                accepted = [fix for fix in st.session_state.fixes if fix.accepted]
                rejected = [fix for fix in st.session_state.fixes if fix.rejected]
                pending = [fix for fix in st.session_state.fixes if not (fix.accepted or fix.rejected)]
                
                if accepted:
                    st.markdown("### ✅ Accepted Changes")
                    for fix in accepted:
                        st.markdown(f"- {fix.issue_type}: '{fix.original_text}' → '{fix.get_selected_replacement()}'")
                
                if rejected:
                    st.markdown("### ❌ Rejected Changes")
                    for fix in rejected:
                        st.markdown(f"- {fix.issue_type}: Kept '{fix.original_text}'")
                
                if pending:
                    st.markdown("### ⏳ Pending Reviews")
                    for fix in pending:
                        st.markdown(f"- {fix.issue_type}: '{fix.original_text}'")
    
    def generate_marked_document(self, text: str) -> str:
        """Generate a marked-up version of the document with issues highlighted"""
        marked_text = text
        for fix in st.session_state.fixes:
            if fix.accepted:
                color = "#90EE90"  # Light green for accepted
                replacement = fix.selected_replacement
            elif fix.rejected:
                color = "#FFB6C1"  # Light red for rejected
                replacement = fix.original_text
            else:
                color = "#FFE4B5"  # Light orange for pending
                replacement = fix.original_text
            
            marked_text = marked_text.replace(
                fix.original_text,
                f'<span style="background-color: {color}">{replacement}</span>'
            )
        return marked_text
    
    def generate_clean_document(self, text: str) -> str:
        """Generate a clean version with all accepted changes applied"""
        clean_text = text
        for fix in self.get_accepted_fixes():
            clean_text = clean_text.replace(fix.original_text, fix.selected_replacement)
        return clean_text
    
    def generate_report(self) -> Dict:
        """Generate a summary report of all changes"""
        return {
            'total_issues': len(st.session_state.fixes),
            'accepted': [(fix.issue_type, fix.original_text, fix.suggested_text) 
                        for fix in self.get_accepted_fixes()],
            'rejected': [(fix.issue_type, fix.original_text) 
                        for fix in self.get_rejected_fixes()],
            'pending': [(fix.issue_type, fix.original_text) 
                       for fix in st.session_state.fixes 
                       if not (fix.accepted or fix.rejected)]
        }

    def create_downloadable_report(self, text: str) -> bytes:
        """Create a PDF report of all changes"""
        def sanitize_text(text: str) -> str:
            """Replace Unicode characters with ASCII equivalents"""
            replacements = {
                '\u2014': '--',  # em dash
                '\u2013': '-',   # en dash
                '\u2018': "'",   # left single quote
                '\u2019': "'",   # right single quote
                '\u201C': '"',   # left double quote
                '\u201D': '"',   # right double quote
                '\u2026': '...', # ellipsis
                '\u2022': '*',   # bullet
                '\u2012': '-',   # figure dash
                '\u2015': '--',  # horizontal bar
                '\u00A0': ' ',   # non-breaking space
            }
            for unicode_char, ascii_char in replacements.items():
                text = text.replace(unicode_char, ascii_char)
            return text

        pdf = PDF()
        
        # Title Page
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 24)
        pdf.cell(0, 20, "Copy Check Report", ln=True, align='C')
        pdf.set_font('Helvetica', '', 12)
        pdf.cell(0, 10, f"Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        
        # Summary statistics
        pdf.add_page()
        pdf.chapter_title("Summary Statistics")
        total_issues = len(st.session_state.fixes)
        accepted_count = len([fix for fix in st.session_state.fixes if fix.accepted])
        rejected_count = len([fix for fix in st.session_state.fixes if fix.rejected])
        pending_count = total_issues - accepted_count - rejected_count
        
        pdf.cell(0, 10, f"Total Issues Found: {total_issues}", ln=True)
        pdf.accepted_text(f"Accepted Changes: {accepted_count}")
        pdf.rejected_text(f"Rejected Changes: {rejected_count}")
        if pending_count > 0:
            pdf.cell(0, 10, f"Pending Decisions: {pending_count}", ln=True)
        pdf.ln(10)
        
        # Group fixes by type
        fixes_by_type = {}
        for fix in st.session_state.fixes:
            if fix.issue_type not in fixes_by_type:
                fixes_by_type[fix.issue_type] = []
            fixes_by_type[fix.issue_type].append(fix)
        
        # Issues by Type
        pdf.add_page()
        pdf.chapter_title("Issues by Type")
        
        for issue_type, fixes in fixes_by_type.items():
            pdf.issue_header(sanitize_text(f"{issue_type} ({len(fixes)} issues)"))
            
            for fix in fixes:
                # Original text and context
                pdf.cell(0, 10, sanitize_text(f"Original: '{fix.original_text}'"), ln=True)
                pdf.cell(0, 10, sanitize_text(f"Context: {fix.context}"), ln=True)
                
                # Show decision and replacement
                if fix.accepted:
                    pdf.accepted_text(sanitize_text(f"ACCEPTED - Changed to: '{fix.get_selected_replacement()}'"))
                elif fix.rejected:
                    pdf.rejected_text(sanitize_text(f"REJECTED - Kept original: '{fix.original_text}'"))
                else:
                    pdf.cell(0, 10, "PENDING DECISION", ln=True)
                
                # If there were multiple suggestions, show them
                if fix.issue_type == "AI Pattern: Em Dash Usage":
                    suggestions = [s.strip() for s in fix.suggested_text.split('|')]
                    if len(suggestions) > 1:
                        pdf.cell(0, 10, "Available replacements:", ln=True)
                        for i, suggestion in enumerate(suggestions, 1):
                            pdf.cell(0, 10, sanitize_text(f"  {i}. {suggestion}"), ln=True)
                elif fix.suggested_text and ',' in fix.suggested_text:
                    suggestions = [s.strip() for s in fix.suggested_text.split(',')]
                    if len(suggestions) > 1:
                        pdf.cell(0, 10, "Available replacements:", ln=True)
                        for i, suggestion in enumerate(suggestions, 1):
                            pdf.cell(0, 10, sanitize_text(f"  {i}. {suggestion}"), ln=True)
                
                pdf.ln(5)
            pdf.ln(10)
        
        # Add Tone Analysis section if available
        if 'tone_metrics' in st.session_state:
            metrics = st.session_state.tone_metrics
            pdf.add_page()
            pdf.chapter_title("Tone Analysis")
            
            # Main metrics
            metrics_text = (
                f"Formality Score: {metrics['formality']:.1f}%\n"
                f"Descriptiveness Score: {metrics['descriptiveness']:.1f}%\n"
                f"Sentiment Score: {metrics['sentiment']:.1f}%\n\n"
                f"Average Sentence Length: {metrics['avg_sentence_length']:.1f} words\n"
                f"Vocabulary Richness: {metrics['vocabulary_richness']:.1f}%\n"
                f"Word Count: {metrics['word_count']}\n"
                f"Sentence Count: {metrics['sentence_count']}"
            )
            pdf.multi_cell(0, 10, metrics_text)
            pdf.ln(10)
            
            # Interpretation
            formality = "very formal" if metrics['formality'] > 75 else "formal" if metrics['formality'] > 60 else "neutral" if metrics['formality'] > 40 else "informal" if metrics['formality'] > 25 else "very informal"
            descriptiveness = "highly descriptive" if metrics['descriptiveness'] > 75 else "moderately descriptive" if metrics['descriptiveness'] > 50 else "somewhat descriptive" if metrics['descriptiveness'] > 25 else "minimally descriptive"
            sentiment = "very positive" if metrics['sentiment'] > 75 else "positive" if metrics['sentiment'] > 60 else "neutral" if metrics['sentiment'] > 40 else "negative" if metrics['sentiment'] > 25 else "very negative"
            
            interpretation_text = (
                f"The text appears to be {formality} in tone, {descriptiveness} in detail, "
                f"and {sentiment} in emotional tone.\n\n"
                f"The vocabulary richness score suggests "
                f"{'a diverse vocabulary' if metrics['vocabulary_richness'] > 50 else 'some repetition in word choice'}.\n\n"
                f"The average sentence length is "
                f"{'quite long' if metrics['avg_sentence_length'] > 20 else 'moderate' if metrics['avg_sentence_length'] > 15 else 'concise'}."
            )
            pdf.multi_cell(0, 10, interpretation_text)
        
        try:
            return pdf.output(dest='S').encode('latin1', 'replace')
        except Exception:
            # If encoding fails, try a more aggressive replacement strategy
            return pdf.output(dest='S').encode('ascii', 'replace') 