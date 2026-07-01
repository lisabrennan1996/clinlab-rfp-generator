/* ─────────────────────────────────────────────────────────────────────────
   ai-assist.js — Local QA model to fill engine gaps
   Runs only on fields the regex engine marked as "review".
   Uses Transformers.js (distilbert QA) entirely in-browser.
   ───────────────────────────────────────────────────────────────────────── */
import { pipeline } from '@xenova/transformers';

let qaPipe = null;
let modelLoading = false;
let modelReady = false;
const modelId = 'Xenova/distilbert-base-uncased-distilled-squad';

export function isModelReady() {
  return modelReady;
}

export async function loadModel(onProgress) {
  if (modelReady) return;
  if (modelLoading) {
    // Wait for the in-flight load
    while (!modelReady) await new Promise(r => setTimeout(r, 200));
    return;
  }
  modelLoading = true;
  try {
    qaPipe = await pipeline('question-answering', modelId, {
      progress_callback: (p) => {
        if (onProgress && p.status === 'download' && typeof p.total === 'number') {
          onProgress(p.loaded / p.total);
        }
      },
    });
    modelReady = true;
  } finally {
    modelLoading = false;
  }
}

/* ─── Field → question mapping ───
   Each "review" field from the report gets turned into a
   natural-language question for the QA model.                    */
function questionForField(fieldName) {
  const q = {
    'General Information — requestor phone':
      'What is the requestor phone number?',
    'Date RFP submitted':
      'What date was the RFP submitted?',
    'Date budget required':
      'What date is the budget required?',
    'General Information — requestor contact':
      'Who is the requestor contact and what is their email?',
    // Enrollment & countries
    'Planned Enrollment (total sites)':
      'How many total participants will be enrolled?',
    'Planned Enrollment (US sites)':
      'How many participants will be enrolled in the US?',
    'Planned Enrollment (OUS sites)':
      'How many participants will be enrolled outside the US?',
    'Number of Countries':
      'How many countries are participating?',
    'Number of Sites':
      'How many sites are participating?',
    // Timing
    'First Patient First Visit':
      'What is the first patient first visit date?',
    'Last Patient Last Visit':
      'What is the last patient last visit date?',
    // Therapeutic area
    'Therapeutic Area':
      'What is the therapeutic area for this study?',
    'Compound':
      'What is the compound or drug being studied?',
    'Protocol Number':
      'What is the protocol number?',
    'Phase':
      'What phase is this study?',
    'Indication':
      'What is the indication or disease being studied?',
  };
  return q[fieldName] || `What is the ${fieldName.toLowerCase()}?`;
}

/* ─── Run QA on a single field ─── */
export async function answerField(context, fieldName) {
  if (!qaPipe) return null;
  const question = questionForField(fieldName);
  try {
    const result = await qaPipe(question, context);
    if (result && result.answer && result.score > 0.1) {
      return { value: result.answer.trim(), confidence: result.score };
    }
  } catch {
    // Model can fail on edge cases — skip
  }
  return null;
}

/* ─── Parse the fill report to extract review fields ─── */
export function parseReviewFields(reportText) {
  const results = [];
  const lines = reportText.split('\n');
  for (const line of lines) {
    // Report format: | Field | Value | Source | Status |
    const parts = line.split('|').map(s => s.trim());
    if (parts.length >= 5 && parts[4] === 'review') {
      results.push({
        field: parts[1],
        currentValue: parts[2],
        source: parts[3],
      });
    }
  }
  return results;
}

/* ─── Build search context from available markdown ─── */
export function buildContext(protocolMd, designMd, prevMd) {
  const parts = [];
  if (protocolMd)  parts.push(protocolMd.slice(0, 15000));
  if (designMd)    parts.push(designMd.slice(0, 15000));
  if (prevMd)      parts.push(prevMd.slice(0, 10000));
  return parts.join('\n\n').slice(0, 30000);
}
