"""Flexible multi-pattern field extraction for clinical protocols.

Each extractor tries multiple regex patterns in order (most specific → most generic)
to handle variations in protocol formatting across different studies.
"""
import re
from typing import Optional


def _try_patterns(text: str, patterns: list) -> Optional[str]:
    """Try multiple regex patterns, return first match group."""
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip() if m.lastindex else m.group(0).strip()
    return None


def protocol_number(text: str) -> Optional[str]:
    """Extract protocol number from various formats."""
    return _try_patterns(text, [
        # Standard label formats
        r'Protocol\s+(?:Number|No\.?|#|ID)\s*:\s*([A-Z0-9][A-Z0-9\-\(\)\/\.]+)',
        r'Protocol\s+(?:Number|No\.?|#|ID)\s*:\s*([^\n\r]+)',
        # Clinical protocol header
        r'Clinical\s+Protocol\s+([A-Z0-9]+\-[A-Z0-9]+\-[A-Z0-9]+[a-z]?)',
        r'Protocol\s+([A-Z0-9]{3,6}\-[A-Z0-9]{2}\-[A-Z0-9]{2,6}[a-z]?)',
        # Study number formats (common patterns in pharma)
        r'([A-Z]{3,4}\-[A-Z]{2}\-[A-Z0-9]{4,6})',
        r'([A-Z0-9]{3,6}\-[A-Z0-9]{4,6})',
    ])


def compound(text: str) -> Optional[str]:
    """Extract compound/drug name and identifier."""
    result = _try_patterns(text, [
        r'Compound:\s*(.+)',
        r'Compound:\s*([^;\n]+)',
        r'Investigational\s+(?:Product|Agent|Drug)(?:\(s\))?:\s*([^;\n]+)',
        r'(?:Drug|Agent|Product)(?:\s+under\s+investigation)?:\s*([^;\n]+)',
    ])
    if result:
        # Clean up common artifacts
        result = re.sub(r'\s+', ' ', result).strip()
        # Only return non-empty
        if len(result) > 2:
            return result
    # Fallback: find any LY/compound number
    m = re.search(r'(LY\d[\d]*)', text)
    if m:
        return m.group(1)
    return None


def protocol_title(text: str) -> Optional[str]:
    """Extract the full protocol title."""
    patterns = [
        # After protocol code line
        r'Protocol\s+[A-Z0-9\-]+\s*\n\s*(A\s+.+?)(?:\n\s*(?:Investigational|Sponsor|Protocol\s+Number|IND|EudraCT))',
        r'CLINICAL\s+PROTOCOL\s+[A-Z0-9\-]+\s*\n\s*(.+?)(?:\n\s*(?:Investigational|Confidential))',
        # Any line starting with "A Phase" or "An Open-Label" etc.
        r'((?:A|An)\s+(?:Phase\s+\d|Open[\-\s]Label|Randomized|Multicenter|Single[\-\s]Arm).{20,200}?)(?:\n\s*(?:Investigational|Protocol|Sponsor|IND|EudraCT))',
        # Long capitalized line early in document
        r'\n\s*([A-Z][A-Z\s,\(\)\d\/\-\:]{30,200})\n\s*(?:Investigational|Protocol\s+Number|Sponsor)',
    ]
    for p in patterns:
        m = re.search(p, text, re.S)
        if m:
            t = m.group(1).strip()
            # Clean up Word comments and weird whitespace
            t = re.sub(r'Commented\s*\[[^\]]*\]', '', t)
            t = re.sub(r'\s+', ' ', t).strip()
            if len(t) > 20:
                return t
    return None


def phase(text: str) -> Optional[str]:
    """Extract study phase."""
    result = _try_patterns(text, [
        r'(?:Development\s+)?Phase:\s*(\d+[A-Za-z]?)',
        r'A\s+Phase\s+(\d+[A-Za-z]?)\s*,',
        r'Phase\s+(\d+[A-Za-z]?)\s+(?:Study|Trial|Randomized|Open)',
        r'Phase\s+(\d+[A-Za-z]?)\b',
    ])
    return result


def therapeutic_area(text: str) -> Optional[str]:
    """Extract therapeutic area from either protocol or design doc."""
    result = _try_patterns(text, [
        r'Therapeutic\s+Area\s*:\s*([^\n]+)',
        r'Therapeutic\s+Area\s*[\(\)]*\s*:\s*([^\n]+)',
        r'TA:\s*([^\n]+)',
    ])
    if result:
        result = re.sub(r'\s*\([^)]*\)', '', result).strip().rstrip('.')
        return result if len(result) > 3 else None
    return None


def indication(text: str) -> Optional[str]:
    """Extract disease indication."""
    result = _try_patterns(text, [
        r'Indication:\s*(.+?)(?:\n|$)',
        r'Indication\s*[\(\)]*\s*:\s*(.+?)(?:\n|$)',
        r'(?:In|for)\s+Patients\s+With\s+(.+?)(?:\n\s*(?:Protocol|Investigational|Sponsor))',
    ])
    # Fallback: look after "patients with" in the title
    if not result:
        title = protocol_title(text)
        if title:
            m = re.search(r'in\s+Patients\s+with\s+(.+?)(?:\.|$)', title, re.I)
            if m:
                result = m.group(1).strip()
    if result:
        result = re.sub(r'\s+', ' ', result).strip().rstrip('.')
        return result
    return None


def enrollment(text: str) -> Optional[int]:
    """Extract total enrolled/randomized participants."""
    patterns = [
        r'(?:Approximately|About|A total of|Estimated|Target|Planned)\s+([\d,]+)\s+(?:participants|patients|subjects)\s+(?:will\s+be\s+)?(?:enrolled|randomized)',
        r'(?:sample\s+size|enrollment|number\s+of\s+(?:participants|patients|subjects))\s*(?::|is|will\s+be|=\s*approximately|of)?\s*([\d,]+)',
        r'(?:total\s+)?(?:sample\s+size|enrollment)\s*(?::|is|=|of)\s*(?:approximately|about|of)?\s*([\d,]+)',
        r'total\s+(?:of\s+)?([\d,]+)\s+(?:participants|patients|subjects)\s+(?:will\s+be\s+)?(?:enrolled|randomized)',
        r'([\d,]+)\s+(?:participants|patients|subjects)\s+(?:will\s+be\s+)?(?:enrolled|randomized)',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return int(m.group(1).replace(',', ''))
            except ValueError:
                pass
    return None


def countries(text: str) -> list:
    """Extract list of countries from design elements."""
    patterns = [
        # Start of line or bullet list
        r'(?:^|\n)\s*Countries?\s+(?:in\s+scope|included|participating)\s*:\s*(.+?)(?:\n(?:\n|\w)|$)',
        r'(?:^|\n)\s*(?:Included|Participating)\s+countries?\s*:\s*(.+?)(?:\n(?:\n|\w)|$)',
        r'For\s+this\s+trial[,;]?\s*(.+?)\s+will\s+be\s+in\s+scope',
        # Explicit "Countries:" label at line start
        r'(?:^|\n)\s*Countries?\s*:\s*(.+?)(?:\n(?:\n|\w)|$)',
    ]
    for p in patterns:
        m = re.search(p, text, re.I | re.M)
        if m:
            raw = m.group(1)
            # Split on comma, semicolon, bullet, "and"
            countries_list = [c.strip().lstrip(r'\uf0b7\uf0a7\-*') for c in re.split(r'[,;]|\band\b', raw) if c.strip()]
            # Filter out non-country-like entries (too short, too long, etc.)
            countries_list = [c for c in countries_list if len(c) > 2 and not c.startswith('the') and not c.startswith('will')]
            if countries_list and len(countries_list) <= 30:
                return countries_list
    return []


def min_age(text: str) -> Optional[int]:
    """Extract minimum participant age."""
    patterns = [
        r'(?:must\s+be|are|aged?)\s+(?:at\s+least|≥|>=)\s*(\d{1,2})\s+years?\s+of\s+age',
        r'(?:must\s+be|are|aged?)\s+(?:at\s+least|≥|>=)\s*(\d{1,2})\s+years?',
        r'aged?\s+(\d{1,2})\s*(?:to|through|\-)\s*\d{1,2}\s*years?',
        r'(\d{1,2})\s+years?\s+of\s+age\s+(?:or\s+)?older',
        r'Age\s*(?:at\s+)?(?:screening|enrollment|inclusion)\s*(?:≥|>=|is|:)?\s*(\d{1,2})',
        r'inclusion\s+criterion\s*(?::|is|#)\s*(\d{1,2})\s*years',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def is_oncology(text: str, ta: Optional[str] = None) -> bool:
    """Determine if study is oncology based on keywords."""
    combined = f"{ta or ''} {text}".lower()
    keywords = ['oncolog', 'cancer', 'tumou?r', 'malignan', 'carcinoma',
                'metastatic', 'neoplasm', 'sarcoma', 'lymphoma', 'leukemia',
                'myeloma', 'glioblastoma', 'melanoma']
    return any(re.search(k, combined) for k in keywords)


def has_ici(text: str) -> bool:
    """Detect if study involves immune checkpoint inhibitors."""
    ici_keywords = [
        'immune checkpoint inhibitor', 'checkpoint inhibitor', 'anti-?PD-?L?1',
        'anti-?PD-?1', 'anti-?CTLA-?4', 'pembrolizumab', 'nivolumab',
        'atezolizumab', 'durvalumab', 'ipilimumab', 'avelumab', 'cemiplimab',
        'tremelimumab', 'dostarlimab',
    ]
    return any(re.search(k, text, re.I) for k in ici_keywords)


def immunogenicity(text: str) -> Optional[str]:
    """Extract immunogenicity testing requirement."""
    patterns = [
        r'Is?\s+immunogenicity\s+testing\s+needed\s*\??\s*(Yes|No)',
        r'immunogenicity\s*(?:testing|assessment)?\s*(?::|is|=)\s*(Yes|No)',
        r'immunogenicity\s*(?:testing|assessment)?\s*(?::|will\s+be\s+)?(performed|required|needed)',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            v = m.group(1).strip().capitalize()
            if v in ('Yes', 'No', 'Performed', 'Required', 'Needed'):
                return 'Yes' if v != 'No' else 'No'
    return None


def genetics_pgx(text: str) -> Optional[str]:
    """Extract genetics/PGx sample collection requirement."""
    patterns = [
        r'(collect|will\s+collect)\s+(?:Genetics|PGx|pharmacogenomic)\s*(Yes|No)?',
        r'(?:Genetics|PGx|pharmacogenomic)\s+(?:samples?\s+)?(?:collected|required)?\s*(?::|is|=)\s*(Yes|No)',
        r'Genetics/PGx\s*sample\s*collected\s*(Yes|No)',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            # Get the last group
            v = m.group(m.lastindex).strip().capitalize() if m.lastindex else 'Yes'
            if v in ('Yes', 'No'):
                return v
    # Keyword heuristic
    if re.search(r'genetics|pgx|pharmacogenom', text, re.I):
        # Check if there's a clear negative
        if re.search(r'no\s+(genetics|pgx)', text, re.I):
            return 'No'
        return 'Yes'
    return None


def screen_fail_rate(text: str) -> float:
    """Extract or estimate screen failure rate."""
    m = re.search(r'(\d{1,3})\s*%\s*(?:screen\s+)?fail', text, re.I)
    if m:
        try:
            return int(m.group(1)) / 100
        except ValueError:
            pass
    return 0.30  # default assumption


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
        m = re.search(p, text)
        if m:
            start = m.start()
            # Find next appendix or section
            nxt = re.search(r'\n\s*(?:Appendix\s+[3-9]|\d+\.\d+\s+|References?\s*\n)', text[start+50:])
            block = text[start: start+50+nxt.start()] if nxt else text[start:start+5000]
            # Extract lines
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            # Filter out page furniture
            lines = [l for l in lines if not re.search(
                r'^(CONFIDENTIAL|Approved on|Page\s+\d|Commented\s*\[|Author and Content|\d{1,3}\s*$)', l
            )]
            if lines:
                return lines
    return None
