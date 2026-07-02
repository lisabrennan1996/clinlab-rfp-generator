#!/usr/bin/env python3
"""Local AI agent for filling regex-gap fields.
Uses BioBERT fine-tuned on PubMed + SQuAD — understands biomedical terminology.
No API key needed. Model downloads once (~440 MB), cached locally thereafter.
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
        logger.info('Loading BioBERT QA model (first download ~440 MB)...')
        self._pipe = pipeline(
            'question-answering',
            model='ktrapeznikov/biobert_v1.1_pubmed_squad_v2',
            tokenizer='ktrapeznikov/biobert_v1.1_pubmed_squad_v2',
        )
        self._ready = True
        logger.info('BioBERT QA model ready.')

    def answer(self, context: str, field_name: str) -> dict | None:
        """Ask a single question about a field using biomedical QA."""
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
        """Map report field names to natural language questions optimized for biomedical QA."""
        q = {
            # Contact / dates
            'General Information — requestor phone': 'What is the requestor phone number?',
            'General Information — requestor contact': 'Who is the requestor contact and what is their email?',
            'Date RFP submitted': 'What date was the RFP submitted?',
            'Date budget required': 'What date is the budget required?',
            'Protocol Approval (PA) date': 'What is the protocol approval date?',
            'Planned First Patient Visit (FPV) date': 'When is the first patient first visit planned?',
            'Planned Last Patient Visit (LPV) date': 'When is the last patient last visit planned?',
            'Protocol duration (FPV-DBL)': 'What is the protocol duration from first patient visit to database lock?',
            'Initial SIV date': 'When is the initial site initiation visit?',

            # Protocol identity
            'Protocol Number': 'What is the protocol number?',
            'Protocol alias': 'What is the protocol number?',
            'Protocol title': 'What is the full protocol title?',
            'Compound': 'What is the compound or drug being studied?',
            'Phase': 'What phase is this study?',
            'Indication': 'What is the indication or disease being studied?',
            'Therapeutic Area': 'What is the therapeutic area for this study?',

            # Enrollment / countries
            'Planned Enrollment (total sites)': 'How many total participants will be enrolled?',
            'Planned Enrollment (US sites)': 'How many participants will be enrolled in the US?',
            'Planned Enrollment (OUS sites)': 'How many participants will be enrolled outside the US?',
            'Patients enrolled (randomized)': 'How many participants will be randomized?',
            'Patients screened': 'How many participants will be screened?',
            'Number of Countries': 'How many countries are participating?',
            'Countries in scope': 'Which countries are participating in this study?',
            'Number of Sites': 'How many sites are participating?',
            'Country where initial FPV planned': 'In which country is the first patient visit planned?',

            # Design
            'First Patient First Visit': 'What is the first patient first visit date?',
            'Last Patient Last Visit': 'What is the last patient last visit date?',
            'Immunogenicity testing needed': 'Is immunogenicity testing needed for this study?',
            'Genetics/PGx sample collected': 'Will genetics or pharmacogenomic samples be collected?',
            'Pediatric population?': 'Does this study include pediatric patients?',
            'Oncology study?': 'Is this an oncology study?',

            # Penalties
            'Penalties & Incentives metrics': 'What are the penalties and incentives metrics for this study?',
        }
        return q.get(field_name, f'What is the {field_name.lower()}?')
