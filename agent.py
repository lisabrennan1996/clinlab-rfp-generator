#!/usr/bin/env python3
"""Local AI agent for filling regex-gap fields.
Uses Hugging Face transformers (distilbert QA) — no API key needed.
Model downloads once (~250 MB), cached locally thereafter.
"""
import logging
logger = logging.getLogger(__name__)

class RFPAgent:
    """Question-answering model for clinical trial field extraction."""

    def __init__(self):
        self._pipe = None
        self._ready = False

    @property
    def is_ready(self):
        return self._ready

    def load_model(self):
        """Load the QA model. Downloads if not cached."""
        from transformers import pipeline
        logger.info('Loading QA model (first download ~250 MB)...')
        self._pipe = pipeline(
            'question-answering',
            model='distilbert-base-uncased-distilled-squad',
            tokenizer='distilbert-base-uncased-distilled-squad',
        )
        self._ready = True
        logger.info('QA model ready.')

    def answer(self, context: str, field_name: str) -> dict | None:
        """Ask a single question about a field."""
        if not self._pipe:
            return None
        question = self._question_for(field_name)
        try:
            result = self._pipe(question=question, context=context)
            if result and result.get('score', 0) > 0.1:
                return {'value': result['answer'].strip(), 'confidence': result['score']}
        except Exception:
            pass
        return None

    @staticmethod
    def _question_for(field_name: str) -> str:
        q = {
            'General Information — requestor phone': 'What is the requestor phone number?',
            'Date RFP submitted': 'What date was the RFP submitted?',
            'Date budget required': 'What date is the budget required?',
            'General Information — requestor contact': 'Who is the requestor contact and what is their email?',
            'Planned Enrollment (total sites)': 'How many total participants will be enrolled?',
            'Planned Enrollment (US sites)': 'How many participants will be enrolled in the US?',
            'Planned Enrollment (OUS sites)': 'How many participants will be enrolled outside the US?',
            'Number of Countries': 'How many countries are participating?',
            'Number of Sites': 'How many sites are participating?',
            'First Patient First Visit': 'What is the first patient first visit date?',
            'Last Patient Last Visit': 'What is the last patient last visit date?',
            'Therapeutic Area': 'What is the therapeutic area for this study?',
            'Compound': 'What is the compound or drug being studied?',
            'Protocol Number': 'What is the protocol number?',
            'Phase': 'What phase is this study?',
            'Indication': 'What is the indication or disease being studied?',
        }
        return q.get(field_name, f'What is the {field_name.lower()}?')
