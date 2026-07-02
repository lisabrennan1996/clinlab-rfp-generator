"""Flexible multi-pattern field extraction for clinical protocols.

Each extractor tries multiple regex patterns in order (most specific -> most generic)
to handle variations in protocol formatting across different studies.

Lilly-optimized: prioritizes Lilly protocol number format (XXXX-XX-XXXXX),
LY compound codes, and phase from title (Arabic + Roman numerals).
"""
import re
from typing import Optional, List


def _normalize_for_extraction(text: str) -> str:
    """Fix PDF extraction artifacts that break code/identifier matching."""
    # Fix: "I 6 T-M C -A M B X" -> "I6T-MC-AMBX" (spaced uppercase/digit codes)
    text = re.sub(r'(?<=[A-Z0-9]) (?=[A-Z0-9])', '', text)
    # Fix: long sequences of single-letter-spaced words from PDF extraction
    text = re.sub(
        r'\b([A-Za-z])(?: ([A-Za-z])){3,}\b',
        lambda m: ''.join(m.group(0).split()), text
    )
    return text


def _try_patterns(text: str, patterns: list) -> Optional[str]:
    """Try multiple regex patterns, return first match group."""
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip() if m.lastindex else m.group(0).strip()
    return None


# Cache normalized text per call (kept small per extraction session)
_NORMALIZED = {}

def _get_text(text: str) -> str:
    """Return normalized text (cached per unique input)."""
    h = hash(text) % 1000000
    if h not in _NORMALIZED:
        _NORMALIZED.clear()
        _NORMALIZED[h] = _normalize_for_extraction(text)
    return _NORMALIZED[h]


# ═══════════════════════════════════════════════════════════════
# PROTOCOL NUMBER
# ═══════════════════════════════════════════════════════════════

def protocol_number(text: str) -> Optional[str]:
    """Extract protocol number.
    
    Lilly-optimized: prioritizes XXXX-XX-XXXXX format (e.g. H8H-MC-LAHD, I6T-MC-AMBX).
    Falls back to general pharma codes and standard labels.
    """
    t = _get_text(text)
    return _try_patterns(t, [
        # -- Lilly format (labeled) --
        r'(?:Protocol\s*(?:Number|No\.?|#|ID)?\s*[:\.]\s*)'
        r'([A-Z0-9]{2,4}-[A-Z]{2}-[A-Z0-9]{3,6}[a-z]?(?:\([a-z]\))?)',
        r'(?:Protocol\s*(?:Number|No\.?|#|ID)?\s*[:\.]\s*)'
        r'([A-Z0-9][A-Z0-9\-\(\)\/\.]{3,25})',
        r'Protocol\s+(?:number|Number)\s+'
        r'([A-Z0-9]{2,4}-[A-Z]{2}-[A-Z0-9]{3,6}[a-z]?(?:\([a-z]\))?)',
        # -- Standalone Lilly code (appears in headers) --
        r'([A-Z0-9]{2,4}-[A-Z]{2}-[A-Z0-9]{3,6}[a-z]?(?:\([a-z]\))?)',
        # -- Trial ID patterns --
        r'(?:Trial\s*(?:ID|No|#|Number)\s*:?\s*)([A-Z0-9][A-Z0-9\-]{3,20})',
        r'(?:Study\s*(?:ID|No|#|Number)\s*:?\s*)([A-Z0-9][A-Z0-9\-]{3,20})',
        # -- Clinical Protocol header --
        r'Clinical\s+Protocol\s+([A-Z0-9]+\-[A-Z0-9]+\-[A-Z0-9]+[a-z]?)',
        r'Protocol\s+([A-Z0-9]{3,6}\-[A-Z0-9]{2}\-[A-Z0-9]{2,6}[a-z]?)',
        # -- General pharma codes (require alphanumeric start/end in each segment) --
        r'([A-Z]{2,4}\-[A-Z]{2}\-[A-Z0-9]{4,6}[a-z]?(?:\([a-z]\))?)',
        r'(?:^|)([A-Z0-9]{2,6}\-[A-Z0-9]{4,8})(?!\d)',
    ])


# ═══════════════════════════════════════════════════════════════
# COMPOUND
# ═══════════════════════════════════════════════════════════════

def compound(text: str) -> Optional[str]:
    """Extract compound/drug name and identifier.
    
    Lilly-optimized: prioritizes LY###### codes, then labeled drug names,
    then capitalized drug names from title context.
    """
    t = _get_text(text)
    
    # Pattern 1: Explicit Compound: label (extract LY code from parens)
    m = re.search(r'Compound\s*:\s*\w+\s*\(\s*(LY\d{6,8})\s*\)', t, re.I)
    if m:
        return m.group(1)
    # Also catch "Compound: LY3074828" directly (no drug name before)
    m = re.search(r'Compound\s*:\s*(LY\d{6,8})\b', t, re.I)
    if m:
        return m.group(1)
    
    m = re.search(r'Compound\s*:\s*([^;\n]{2,60})', t)
    if m:
        result = re.sub(r'\s+', ' ', m.group(1).strip())
        # Clean: remove trailing parenthetical context
        result = re.sub(r'\s*\(.*', '', result).strip()
        if len(result) > 2:
            return result
    
    # Pattern 2: Other drug labels
    result = _try_patterns(t, [
        r'Investigational\s+(?:Product|Agent|Drug)(?:\(s\))?:\s*([^;\n]+)',
        r'(?:Drug|Agent|Product)(?:\s+under\s+investigation)?:\s*([^;\n]+)',
    ])
    if result:
        result = re.sub(r'\s+', ' ', result).strip()
        if len(result) > 2:
            return result
    
    # Pattern 3: LY code anywhere in text (highest confidence match)
    m = re.search(r'LY\d{6,8}', t)
    if m:
        return m.group(0)
    
    # Pattern 4: Capitalized drug name from title context
    title_match = re.search(
        r'(?:Effect|Study|Trial|Comparison|Safety|Efficacy|Bioequivalence)'
        r'(?:\s+of\s+|\s+of\s+the\s+|\s+of\s+a\s+|\s+of\s+an\s+)'
        r'([A-Z][a-z]{4,}(?:\s*[A-Z][a-z]{2,})?)',
        t[:3000]
    )
    if title_match:
        drug = title_match.group(1).strip()
        common = {'Patients', 'Subjects', 'Participants', 'Treatment', 'Therapy',
                  'Healthy', 'Methodology', 'Approach', 'Method', 'New', 'Novel',
                  'Injectable', 'Oral', 'Intravenous', 'Subcutaneous', 'Topical',
                  'Human', 'Clinical', 'Single', 'Multiple', 'Following', 'Different',
                  'Various', 'Several', 'Alternative'}
        if drug not in common and len(drug) > 4:
            return drug
    
    return None


# ═══════════════════════════════════════════════════════════════
# PROTOCOL TITLE
# ═══════════════════════════════════════════════════════════════

def protocol_title(text: str) -> Optional[str]:
    """Extract the full protocol title."""
    t = _get_text(text)
    patterns = [
        r'Protocol\s+[A-Z0-9\-]+\s*\n\s*(A\s+.+?)(?:\n\s*(?:Investigational|Sponsor|Protocol\s+Number|IND|EudraCT))',
        r'CLINICAL\s+PROTOCOL\s+[A-Z0-9\-]+\s*\n\s*(.+?)(?:\n\s*(?:Investigational|Confidential))',
        r'((?:A|An)\s+(?:Phase\s+\d|Open[\-\s]Label|Randomized|Multicenter|Single[\-\s]Arm).{20,200}?)'
        r'(?:\n\s*(?:Investigational|Protocol|Sponsor|IND|EudraCT))',
        r'\n\s*([A-Z][A-Z\s,\(\)\d\/\-\:]{30,200})\n\s*(?:Investigational|Protocol\s+Number|Sponsor)',
        r'Protocol\s+Title\s*:\s*(.+?)(?:\n\s*\n)',
    ]
    for p in patterns:
        m = re.search(p, t, re.S)
        if m:
            v = m.group(1).strip()
            v = re.sub(r'Commented\s*\[[^\]]*\]', '', v)
            v = re.sub(r'\s+', ' ', v).strip()
            if len(v) > 20:
                return v
    return None


# ═══════════════════════════════════════════════════════════════
# PHASE
# ═══════════════════════════════════════════════════════════════

def phase(text: str) -> Optional[str]:
    """Extract study phase.
    
    Handles: Phase 3, Phase III, PHASE2, Study Phase: 1,
    and phase embedded in title: "A Phase 2, Randomized..."
    """
    t = _get_text(text)
    result = _try_patterns(t, [
        # Explicit labels
        r'(?:Development\s+)?Phase:\s*(\d+[A-Za-z]?)',
        r'Study\s+Phase\s*:\s*(\d+[A-Za-z]?)',
        # Phase from title (Arabic numerals)
        r'Phase\s+(\d+[A-Za-z]?)\s*(?:Study|Trial|Randomized|Open|Double|Multi|Single)',
        r'(?:A|An)\s+Phase\s+(\d+[A-Za-z]?\s*,)',
        # Roman numerals in title
        r'Phase\s+([IVXL]+)\s*(?:Study|Trial|Randomized)',
        r'(?:A|An)\s+Phase\s+([IVXL]+)\s*[,]?',
        # Generic phase mention
        r'Phase\s+(\d+[A-Za-z]?)\b',
        r'Phase\s+([IVXL]+)\b',
    ])
    if result:
        result = result.rstrip(',').strip()
        return result
    return None


# ═══════════════════════════════════════════════════════════════
# THERAPEUTIC AREA
# ═══════════════════════════════════════════════════════════════

def therapeutic_area(text: str) -> Optional[str]:
    """Extract therapeutic area."""
    t = _get_text(text)
    result = _try_patterns(t, [
        r'Therapeutic\s+Area\s*:\s*([^\n]+)',
        r'Therapeutic\s+Area\s*[\(\)]*\s*:\s*([^\n]+)',
        r'TA:\s*([^\n]+)',
    ])
    if result:
        result = re.sub(r'\s*\([^)]*\)', '', result).strip().rstrip('.')
        return result if len(result) > 3 else None
    
    # Fallback: check for condition/disease labels
    for p in [
        r'(?:Condition|Disease|Indication|Target\s+Condition)\s*(?:under\s+study)?\s*:\s*([^\n]{3,80})',
        r'(?:Primary\s+)?Diagnosis\s*:\s*([^\n]{3,80})',
    ]:
        m = re.search(p, t, re.I)
        if m:
            v = m.group(1).strip().strip('.').strip()
            if len(v) > 3:
                return v
    return None


# ═══════════════════════════════════════════════════════════════
# INDICATION
# ═══════════════════════════════════════════════════════════════

def indication(text: str) -> Optional[str]:
    """Extract disease indication."""
    t = _get_text(text)
    result = _try_patterns(t, [
        r'Indication:\s*(.+?)(?:\n|$)',
        r'Indication\s*[\(\)]*\s*:\s*(.+?)(?:\n|$)',
        r'(?:In|for)\s+Patients\s+With\s+(.+?)(?:\n\s*(?:Protocol|Investigational|Sponsor))',
    ])
    if not result:
        title = protocol_title(t)
        if title:
            m = re.search(r'in\s+Patients\s+with\s+(.+?)(?:\.|$)', title, re.I)
            if m:
                result = m.group(1).strip()
    if not result:
        m = re.search(r'Protocol\s+Title\s*:\s*(.+?)(?:\n|$)', t[:3000])
        if m:
            m2 = re.search(r'\bin\s+(.+?)\s*$', m.group(1))
            if m2:
                result = m2.group(1).strip().rstrip('.')
    if result:
        result = re.sub(r'\s+', ' ', result).strip().rstrip('.')
        return result
    return None


# ═══════════════════════════════════════════════════════════════
# ENROLLMENT
# ═══════════════════════════════════════════════════════════════

def enrollment(text: str) -> Optional[int]:
    """Extract total enrolled/randomized participants."""
    t = _get_text(text)
    text_window = t[:20000]
    patterns = [
        # "Approximately 240 patients" (with or without trailing verb)
        r'(?:Approximately|About|A total of|Estimated|Target|Planned|Total)\s+'
        r'([\d,]+)\s+(?:participants|patients|subjects)(?:\s+(?:will\s+be\s+)?(?:enrolled|randomized))?',
        # "N = 240" standalone
        r'(?:sample\s+size|enrollment|number\s+of\s+(?:participants|patients|subjects))\s*'
        r'(?::|is|will\s+be|=\s*approximately|of)?\s*([\d,]+)',
        r'(?:total\s+)?(?:sample\s+size|enrollment)\s*(?::|is|=|of)\s*'
        r'(?:approximately|about|of)?\s*([\d,]+)',
        r'\b[Nn]\s*[=:]\s*(\d{2,4})\b',
        r'(?:^|\s)(\d{3,4})\s+(?:patients|subjects|participants)\s+will\s+be\s+(?:randomized|enrolled)',
        r'total\s+of\s+(\d{3,4})\s+(?:patients|subjects|participants)',
    ]
    for p in patterns:
        m = re.search(p, text_window, re.I)
        if m:
            try:
                val = int(m.group(1).replace(',', ''))
                if 2 <= val <= 100000:
                    return val
            except ValueError:
                pass
    return None


# ═══════════════════════════════════════════════════════════════
# COUNTRIES
# ═══════════════════════════════════════════════════════════════

def countries(text: str) -> List[str]:
    """Extract list of participating countries."""
    t = _get_text(text)
    country_keywords = [
        'United States', 'USA', 'Canada', 'Mexico', 'Brazil', 'Argentina',
        'United Kingdom', 'UK', 'France', 'Germany', 'Italy', 'Spain',
        'Portugal', 'Netherlands', 'Belgium', 'Switzerland', 'Austria',
        'Sweden', 'Norway', 'Denmark', 'Finland', 'Ireland', 'Poland',
        'Czech Republic', 'Hungary', 'Romania', 'Greece', 'Turkey',
        'Russia', 'Ukraine', 'Israel', 'South Africa', 'Australia',
        'New Zealand', 'Japan', 'China', 'South Korea', 'Taiwan',
        'India', 'Singapore', 'Thailand', 'Malaysia', 'Philippines',
        'Hong Kong',
    ]
    countries_list = []
    for c in country_keywords:
        if re.search(r'\b' + re.escape(c) + r'\b', t):
            if c not in countries_list:
                countries_list.append(c)
    countries_list = [c for c in countries_list if len(c) > 2
                      and not c.startswith('the') and not c.startswith('will')]
    if countries_list and len(countries_list) <= 30:
        return countries_list
    return []


# ═══════════════════════════════════════════════════════════════
# MIN AGE
# ═══════════════════════════════════════════════════════════════

def min_age(text: str) -> Optional[int]:
    """Extract minimum participant age."""
    t = _get_text(text)
    patterns = [
        r'(?:must\s+be|are|aged?)\s+(?:at\s+least|>=|≥)\s*(\d{1,2})\s+years?\s+of\s+age',
        r'(?:must\s+be|are|aged?)\s+(?:at\s+least|>=|≥)\s*(\d{1,2})\s+years?',
        r'aged?\s+(\d{1,2})\s*(?:to|through|\-)\s*\d{1,2}\s*years?',
        r'(\d{1,2})\s+years?\s+of\s+age\s+(?:or\s+)?older',
        r'Age\s*(?:at\s+)?(?:screening|enrollment|inclusion)\s*(?:>=|is|:)?\s*(\d{1,2})',
        r'inclusion\s+criterion\s*(?::|is|#)\s*(\d{1,2})\s*years',
        r'(?:>=|≥)\s*(\d{1,2})\s+years',
        r'(?:Age|aged?)\s*(?:>=|≥|=)\s*(\d{1,2})',
        r'(?:Inclusion\s+Criteria|Criteria|Eligibility).{0,200}?'
        r'(?:(?:at\s+least|>|=)\s*(\d{1,2})\s*(?:years?|yrs?))',
        # "Age X to Y" format in inclusion criteria
        r'(?:Inclusion|Criteria|Age).{0,50}?[Aa]ge[\s:]+(\d{1,2})\s*(?:to|through|-)\s*\d{1,2}\s*(?:years?|yrs?)?',
    ]
    for p in patterns:
        m = re.search(p, t, re.I)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


# ═══════════════════════════════════════════════════════════════
# ONCOLOGY / IMMUNOGENICITY / GENETICS / ETC
# ═══════════════════════════════════════════════════════════════

def is_oncology(text: str, ta: Optional[str] = None) -> bool:
    """Determine if study is oncology based on keywords."""
    t = _get_text(text)
    combined = f"{ta or ''} {t}".lower()
    keywords = ['oncolog', 'cancer', 'tumou?r', 'malignan', 'carcinoma',
                'metastatic', 'neoplasm', 'sarcoma', 'lymphoma', 'leukemia',
                'myeloma', 'glioblastoma', 'melanoma']
    return any(re.search(k, combined) for k in keywords)


def has_ici(text: str) -> bool:
    """Detect if study involves immune checkpoint inhibitors."""
    t = _get_text(text)
    ici_keywords = [
        'immune checkpoint inhibitor', 'checkpoint inhibitor', 'anti-?PD-?L?1',
        'anti-?PD-?1', 'anti-?CTLA-?4', 'pembrolizumab', 'nivolumab',
        'atezolizumab', 'durvalumab', 'ipilimumab', 'avelumab', 'cemiplimab',
        'tremelimumab', 'dostarlimab',
    ]
    return any(re.search(k, t, re.I) for k in ici_keywords)


def immunogenicity(text: str) -> Optional[str]:
    """Extract immunogenicity testing requirement."""
    t = _get_text(text)
    patterns = [
        r'Is?\s+immunogenicity\s+testing\s+needed\s*\??\s*(Yes|No)',
        r'immunogenicity\s*(?:testing|assessment)?\s*(?::|is|=)\s*(Yes|No)',
        r'immunogenicity\s*(?:testing|assessment)?\s*(?::|will\s+be\s+)?(performed|required|needed)',
    ]
    for p in patterns:
        m = re.search(p, t, re.I)
        if m:
            v = m.group(1).strip().capitalize()
            if v in ('Yes', 'No', 'Performed', 'Required', 'Needed'):
                return 'Yes' if v != 'No' else 'No'
    return None


def genetics_pgx(text: str) -> Optional[str]:
    """Extract genetics/PGx sample collection requirement."""
    t = _get_text(text)
    patterns = [
        r'(collect|will\s+collect)\s+(?:Genetics|PGx|pharmacogenomic)\s*(Yes|No)?',
        r'(?:Genetics|PGx|pharmacogenomic)\s+(?:samples?\s+)?(?:collected|required)?\s*(?::|is|=)\s*(Yes|No)',
        r'Genetics/PGx\s*sample\s*collected\s*(Yes|No)',
    ]
    for p in patterns:
        m = re.search(p, t, re.I)
        if m:
            v = m.group(m.lastindex).strip().capitalize() if m.lastindex else 'Yes'
            if v in ('Yes', 'No'):
                return v
    if re.search(r'genetics|pgx|pharmacogenom', t, re.I):
        if re.search(r'no\s+(genetics|pgx)', t, re.I):
            return 'No'
        return 'Yes'
    return None


def screen_fail_rate(text: str) -> float:
    """Extract or estimate screen failure rate."""
    m = re.search(r'(\d{1,3})\s*%\s*(?:screen\s+)?fail', _get_text(text), re.I)
    if m:
        try:
            return int(m.group(1)) / 100
        except ValueError:
            pass
    return 0.30


def ed_rate() -> float:
    """Early discontinuation rate (default assumption)."""
    return 0.10


def analyze_appendix_2(text: str) -> Optional[list]:
    """Find and extract the clinical laboratory tests appendix."""
    patterns = [
        r'Appendix\s*2\s*:?\s*Clinical\s+Laboratory\s+Tests\s*\n\s*(?:The\s+tests\s+detailed|The\s+following)',
        r'Clinical\s+Laboratory\s+Tests\s*\n\s*(?:The\s+tests\s+detailed|The\s+following)',
        r'Appendix\s*\d+\s*:?\s*Clinical\s+Laboratory',
    ]
    for p in patterns:
        m = re.search(p, _get_text(text))
        if m:
            start = m.start()
            nxt = re.search(
                r'\n\s*(?:Appendix\s+[3-9]|\d+\.\d+\s+|References?\s*\n)',
                _get_text(text)[start+50:]
            )
            block = _get_text(text)[start:start+50+nxt.start()] if nxt else _get_text(text)[start:start+5000]
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            lines = [l for l in lines if not re.search(
                r'^(CONFIDENTIAL|Approved on|Page\s+\d|Commented\s*\[|Author and Content|\d{1,3}\s*$)', l
            )]
            if lines:
                return lines
    return None
